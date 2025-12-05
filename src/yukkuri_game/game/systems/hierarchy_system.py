"""
Hierarchy System.
Manages parent-child relationships and transforms.
"""

import pymunk
from ...engine.ecs import System, World
from ..components import Mount, Transform, PhysicsBody

class HierarchySystem(System):
    """
    Updates positions of mounted entities based on their parents.
    """

    def update(self, world: World, dt: float) -> None:
        """
        Recursive update of the hierarchy.
        """
        # 1. Build a map of all mounted entities
        mounts = {}
        for ent, mount in world.get_components_tuple(Mount):
            mounts[ent] = mount

        # 2. Identify roots (Entities that have a Mount component but no valid parent in the hierarchy)
        # Note: An entity might not have a Mount component but be a parent?
        # The Proposal says "Mount Component... parent_id... children_ids".
        # So we assume if you are in the hierarchy, you have a Mount component.

        roots = []
        for ent, mount in mounts.items():
            # If parent_id is -1 or parent not in mounts list (e.g. parent destroyed or not a Mount)
            # wait, if parent is not in 'mounts', does it mean it's a root?
            # Or is it a top-level entity that just has children?
            # If 'parent_id' is set to something valid, we are a child.
            # If parent_id is -1, we are a root.

            if mount.parent_id == -1:
                roots.append(ent)
            elif mount.parent_id not in mounts:
                 # Orphaned? Treat as root or handle error?
                 # Treat as root for now to avoid disappearing
                 roots.append(ent)

        # 3. Process roots
        for root in roots:
            self.process_entity(world, root, mounts)

    def process_entity(self, world: World, entity: int, mounts: dict):
        """
        Recursively update children of this entity.
        """
        mount = mounts.get(entity)
        if not mount:
            return

        # Get current transform/physics data of this entity (The Parent)
        parent_pos = None
        parent_rot = 0.0

        phys = world.get_component(entity, PhysicsBody)
        if phys:
            parent_pos = phys.body.position
            parent_rot = phys.body.angle
        else:
            trans = world.get_component(entity, Transform)
            if trans:
                parent_pos = pymunk.Vec2d(trans.x, trans.y)
                # Transform doesn't have rotation currently, assume 0
                parent_rot = 0.0

        if parent_pos is None:
            # Cannot propogate
            return

        # Update Children
        for child_id in mount.children_ids:
            child_mount = mounts.get(child_id)
            if not child_mount:
                continue

            # Calculate Child Position
            offset = child_mount.mount_point_offset
            # Rotate offset by parent rotation
            rotated_offset = offset.rotated(parent_rot)
            child_pos = parent_pos + rotated_offset

            # Apply to Child
            child_phys = world.get_component(child_id, PhysicsBody)
            if child_phys:
                child_phys.body.position = child_pos
                child_phys.body.angle = parent_rot

                # Ensure child shapes are sensors as per proposal
                if not child_phys.shape.sensor:
                    child_phys.shape.sensor = True

            child_trans = world.get_component(child_id, Transform)
            if child_trans:
                child_trans.x = child_pos.x
                child_trans.y = child_pos.y

            # Recurse
            self.process_entity(world, child_id, mounts)
