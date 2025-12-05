"""
Hierarchy System.
Manages parent-child relationships and transforms.
"""

import pymunk
import math
from ...engine.ecs import System, World
from ..components import Mount, Transform, PhysicsBody, PendingDismount, MovementController
from ..collision_constants import CollisionCategories

class HierarchySystem(System):
    """
    Updates positions of mounted entities based on their parents.
    Also handles PendingDismount (Ghost Mode) logic.
    """

    def update(self, world: World, dt: float) -> None:
        """
        Recursive update of the hierarchy.
        """
        # 1. Build a map of all mounted entities
        # Use get_components (singular) to get a Dict {id: component}
        mounts = world.get_components(Mount)

        # 2. Identify roots
        roots = []
        for ent, mount in mounts.items():
            if mount.parent_id == -1:
                roots.append(ent)
            elif mount.parent_id not in mounts:
                 # Orphaned? Treat as root.
                 roots.append(ent)

        # 3. Process roots
        for root in roots:
            self.process_entity(world, root, mounts)

        # 4. Process Pending Dismounts
        self.process_pending_dismounts(world, dt)

    def process_entity(self, world: World, root_entity: int, mounts: dict):
        """
        Iteratively update children of this entity using a stack.
        """
        # Stack contains (entity_id, parent_pos, parent_rot)
        # For the root, we need to fetch its current pos/rot first.

        # Initial fetch for root
        root_pos = None
        root_rot = 0.0

        phys = world.get_component(root_entity, PhysicsBody)
        if phys:
            root_pos = phys.body.position
            root_rot = phys.body.angle
        else:
            trans = world.get_component(root_entity, Transform)
            if trans:
                root_pos = pymunk.Vec2d(trans.x, trans.y)
                root_rot = 0.0

        if root_pos is None:
            return

        stack = [(root_entity, root_pos, root_rot)]

        while stack:
            current_entity, parent_pos, parent_rot = stack.pop()

            mount = mounts.get(current_entity)
            if not mount:
                continue

            # Iterate over children
            # Note: We reverse the list to process them in order if stack behavior matters (LIFO)
            # But order probably doesn't matter for independent children.
            for child_id in mount.children_ids:
                child_mount = mounts.get(child_id)
                if not child_mount:
                    continue

                # Calculate Child Position
                offset = child_mount.mount_point_offset
                rotated_offset = offset.rotated(parent_rot)
                child_pos = parent_pos + rotated_offset

                # Apply to Child
                child_phys = world.get_component(child_id, PhysicsBody)
                child_rot = parent_rot # Children inherit rotation

                if child_phys:
                    child_phys.body.position = child_pos
                    child_phys.body.angle = child_rot

                    if not child_phys.shape.sensor:
                        child_phys.shape.sensor = True

                child_trans = world.get_component(child_id, Transform)
                if child_trans:
                    child_trans.x = child_pos.x
                    child_trans.y = child_pos.y

                # Push child to stack to process ITS children
                stack.append((child_id, child_pos, child_rot))

    def process_pending_dismounts(self, world: World, dt: float):
        """
        Handle entities that are trying to find a spot to dismount.
        """
        for entity, (pending, trans, phys) in world.get_components_tuple(PendingDismount, Transform, PhysicsBody):
            pending.time_in_pending += dt

            # Throttle search: every 0.2s?
            # For simplicity, search every frame but limit iterations.

            # Search for a valid spot
            # Concentric search

            found_spot = False
            target_pos = phys.body.position

            # Define search pattern
            search_radius = 50.0
            offsets = [
                pymunk.Vec2d(0, 0),
                pymunk.Vec2d(search_radius, 0),
                pymunk.Vec2d(-search_radius, 0),
                pymunk.Vec2d(0, search_radius),
                pymunk.Vec2d(0, -search_radius),
                pymunk.Vec2d(search_radius, search_radius),
                pymunk.Vec2d(-search_radius, search_radius),
                pymunk.Vec2d(search_radius, -search_radius),
                pymunk.Vec2d(-search_radius, -search_radius),
            ]

            space = phys.body.space
            if not space:
                continue

            collider_radius = 10.0
            if hasattr(phys.shape, 'radius'):
                collider_radius = phys.shape.radius

            for offset in offsets:
                candidate_pos = target_pos + offset

                info = space.point_query_nearest(candidate_pos, collider_radius, pymunk.ShapeFilter(mask=CollisionCategories.WALL))

                if info is None or info.distance > 0:
                    if info and info.distance < 0:
                        continue

                    phys.body.position = candidate_pos
                    trans.x = candidate_pos.x
                    trans.y = candidate_pos.y

                    world.remove_component(entity, PendingDismount)

                    if phys.shape.sensor:
                        phys.shape.sensor = False

                    found_spot = True
                    break

            if not found_spot:
                if pending.time_in_pending > 5.0:
                    phys.body.position = pymunk.Vec2d(0, 0)
                    world.remove_component(entity, PendingDismount)
                    if phys.shape.sensor:
                        phys.shape.sensor = False
