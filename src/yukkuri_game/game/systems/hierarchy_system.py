"""
Hierarchy System.
Manages parent-child relationships and transforms.
"""

import pymunk
import math
from loguru import logger
from ...engine.ecs import System, World
from ..components import Mount, Transform, PhysicsBody, PendingDismount, MovementController
from ..collision_constants import CollisionCategories
from .physics import PhysicsSystem

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
            mount = mounts.get(root)
            if mount and mount.structure_dirty:
                self.recalculate_root_collider(world, root, mounts)
                mount.structure_dirty = False
            self.process_entity(world, root, mounts)

        # 4. Process Pending Dismounts
        self.process_pending_dismounts(world, dt)

    def collect_descendants(self, entity_id: int, mounts: dict, accumulated_offset: pymunk.Vec2d, results: list):
        """
        Recursively collects all descendants and their absolute offsets relative to the root.
        """
        mount = mounts.get(entity_id)
        if not mount:
            return

        for child_id in mount.children_ids:
            child_mount = mounts.get(child_id)
            if not child_mount:
                continue

            # Note: This ignores rotation for radius calculation (assuming worst case circular expansion)
            # A precise AABB would require checking rotations, but for a Circle collider, max distance is enough.
            child_abs_offset = accumulated_offset + child_mount.mount_point_offset
            results.append((child_id, child_abs_offset))

            self.collect_descendants(child_id, mounts, child_abs_offset, results)

    def recalculate_root_collider(self, world: World, root_entity: int, mounts: dict):
        """
        Updates the root entity's collider to encompass the entire stack (Totem Pole).
        """
        phys = world.get_component(root_entity, PhysicsBody)
        if not phys or not isinstance(phys.shape, pymunk.Circle):
            return

        # Capture base radius if not set
        if phys.base_radius is None:
            phys.base_radius = phys.shape.radius

        mount = mounts.get(root_entity)
        # Even if mount is empty, we might need to shrink back to base_radius

        # Recursive collection
        descendants = []
        if mount:
            self.collect_descendants(root_entity, mounts, pymunk.Vec2d(0, 0), descendants)

        # Start with base radius
        max_req_radius = phys.base_radius

        for child_id, offset in descendants:
            # Add child radius. Safe get, if missing default to 0.
            child_phys = world.get_component(child_id, PhysicsBody)
            child_r = 0.0
            if child_phys and isinstance(child_phys.shape, pymunk.Circle):
                child_r = child_phys.shape.radius

            # Use offset length + child radius to determine extent
            req_r = offset.length + child_r
            if req_r > max_req_radius:
                max_req_radius = req_r

        # Update radius if significantly different
        current_r = phys.shape.radius

        if abs(max_req_radius - current_r) > 1.0:
            logger.trace(f"Resizing root collider from {current_r} to {max_req_radius}")
            phys.shape.unsafe_set_radius(max_req_radius)
            physics_system = world.services.try_get(PhysicsSystem)
            if physics_system:
                physics_system.space.reindex_shape(phys.shape)

    def process_entity(self, world: World, root_entity: int, mounts: dict):
        """
        Iteratively update children of this entity using a stack.
        """
        # Stack contains (entity_id, parent_pos, parent_rot)
        # For the root, we need to fetch its current pos/rot first.

        # Initial fetch for root
        root_pos = None
        root_rot = 0.0
        root_prev_pos = None
        root_prev_rot = 0.0

        phys = world.get_component(root_entity, PhysicsBody)
        if phys:
            root_pos = phys.body.position
            root_rot = phys.body.angle
        else:
            trans = world.get_component(root_entity, Transform)
            if trans:
                root_pos = pymunk.Vec2d(trans.x, trans.y)
                root_rot = trans.rotation

        # Fetch root prev pos for interpolation syncing
        trans = world.get_component(root_entity, Transform)
        if trans:
            root_prev_pos = pymunk.Vec2d(trans.prev_x, trans.prev_y) if trans.prev_x is not None else root_pos
            root_prev_rot = trans.prev_rotation if trans.prev_rotation is not None else root_rot

        if root_pos is None:
            return

        if root_prev_pos is None:
            root_prev_pos = root_pos

        stack = [(root_entity, root_pos, root_rot, root_prev_pos, root_prev_rot)]

        while stack:
            current_entity, parent_pos, parent_rot, parent_prev_pos, parent_prev_rot = stack.pop()

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

                # Calculate Child Prev Position
                # Use parent_prev_rot to correctly interpolate the offset
                prev_rotated_offset = offset.rotated(parent_prev_rot)
                child_prev_pos = parent_prev_pos + prev_rotated_offset

                # Apply to Child
                child_phys = world.get_component(child_id, PhysicsBody)
                child_rot = parent_rot # Children inherit rotation
                child_prev_rot = parent_prev_rot

                if child_phys:
                    # Sync physics body directly
                    child_phys.body.position = child_pos
                    child_phys.body.angle = child_rot

                    if not child_phys.shape.sensor:
                        child_phys.shape.sensor = True

                child_trans = world.get_component(child_id, Transform)
                if child_trans:
                    child_trans.x = child_pos.x
                    child_trans.y = child_pos.y
                    child_trans.rotation = child_rot

                    # Update prev to match parent's relative motion for interpolation
                    child_trans.prev_x = child_prev_pos.x
                    child_trans.prev_y = child_prev_pos.y
                    child_trans.prev_rotation = child_prev_rot

                # Push child to stack to process ITS children
                stack.append((child_id, child_pos, child_rot, child_prev_pos, child_prev_rot))

    def process_pending_dismounts(self, world: World, dt: float):
        """
        Handle entities that are trying to find a spot to dismount.
        """
        for entity, (pending, trans, phys) in world.get_components_tuple(PendingDismount, Transform, PhysicsBody):
            logger.trace(f"Processing pending dismount for entity {entity}")
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
