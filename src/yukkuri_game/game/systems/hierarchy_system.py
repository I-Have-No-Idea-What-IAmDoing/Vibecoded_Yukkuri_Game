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
            self.recalculate_root_collider(world, root, mounts)
            self.process_entity(world, root, mounts)

        # 4. Process Pending Dismounts
        self.process_pending_dismounts(world, dt)

    def recalculate_root_collider(self, world: World, root_entity: int, mounts: dict):
        """
        Updates the root entity's collider to encompass the entire stack (Totem Pole).
        """
        phys = world.get_component(root_entity, PhysicsBody)
        if not phys or not isinstance(phys.shape, pymunk.Circle):
            return

        mount = mounts.get(root_entity)
        if not mount or not mount.children_ids:
             return

        max_dist_sq = 0.0

        for child_id in mount.children_ids:
            child_mount = mounts.get(child_id)
            if not child_mount:
                continue

            dist_sq = child_mount.mount_point_offset.length_squared
            child_phys = world.get_component(child_id, PhysicsBody)
            child_r = 10.0
            if child_phys and hasattr(child_phys.shape, 'radius'):
                child_r = child_phys.shape.radius

            req_r = math.sqrt(dist_sq) + child_r
            if req_r > max_dist_sq:
                max_dist_sq = req_r

        current_r = phys.shape.radius
        target_r = max(current_r, max_dist_sq)

        if target_r > current_r + 1.0:
            logger.trace(f"Resizing root collider from {current_r} to {target_r}")
            phys.shape.unsafe_set_radius(target_r)
            physics_system = world.services.try_get(PhysicsSystem)
            if physics_system:
                physics_system.space.reindex_shape(phys.shape)

    def process_entity(self, world: World, root_entity: int, mounts: dict):
        """
        Iteratively update children of this entity using a stack.
        """
        # Fetch root current and prev pos
        root_pos = None
        root_rot = 0.0
        root_prev_pos = None

        phys = world.get_component(root_entity, PhysicsBody)
        if phys:
            root_pos = phys.body.position
            root_rot = phys.body.angle
        else:
            trans = world.get_component(root_entity, Transform)
            if trans:
                root_pos = pymunk.Vec2d(trans.x, trans.y)
                root_rot = 0.0

        trans = world.get_component(root_entity, Transform)
        if trans:
            root_prev_pos = pymunk.Vec2d(trans.prev_x, trans.prev_y) if trans.prev_x is not None else root_pos

        if root_pos is None:
            return

        if root_prev_pos is None:
            root_prev_pos = root_pos

        # Stack: (entity_id, parent_pos, parent_rot, parent_prev_pos)
        stack = [(root_entity, root_pos, root_rot, root_prev_pos)]

        while stack:
            current_entity, parent_pos, parent_rot, parent_prev_pos = stack.pop()

            mount = mounts.get(current_entity)
            if not mount:
                continue

            for child_id in mount.children_ids:
                child_mount = mounts.get(child_id)
                if not child_mount:
                    continue

                # Child logic
                offset = child_mount.mount_point_offset
                rotated_offset = offset.rotated(parent_rot)
                child_pos = parent_pos + rotated_offset

                # Interpolation Logic:
                # Calculate what the child's prev position SHOULD have been based on parent's prev position.
                # Use current rotation for simplicity, or ideally parent_prev_rot if we had it.
                # Assuming rotation is slow/instant or we don't interpolate rotation perfectly here:
                # Better approximation: rotated_offset is based on CURRENT rot.
                # If we want smooth interp, we should use parent_prev_rot.
                # But we don't track prev_rot in Transform.
                # So we approximate using current rotation for the offset.
                child_prev_pos = parent_prev_pos + rotated_offset

                # Apply to Child
                child_phys = world.get_component(child_id, PhysicsBody)
                child_rot = parent_rot # Children inherit rotation

                if child_phys:
                    child_phys.body.position = child_pos
                    child_phys.body.angle = child_rot

                    # Ensure children are sensors
                    if not child_phys.shape.sensor:
                        child_phys.shape.sensor = True

                    # Reindex needed? Usually children follow parent.
                    # If parent moved, we reindexed parent. Children are sensors, so maybe less critical for collision blocking,
                    # but critical for hitboxes.
                    # PhysicsSystem.space.reindex_shapes_for_body(child_phys.body) could be called here if we had access.
                    # Or rely on global step() if it happens later.
                    # But hierarchy system usually runs AFTER movement.
                    # So global step has already happened?
                    # If KinematicMovementSystem calls step(), then Hierarchy runs, children positions are updated.
                    # The spatial hash for children is now STALE until next frame's step().
                    # This means raycasts (Visibility) might miss children in this frame.
                    # So we should reindex children here.
                    if child_phys.body.space:
                        child_phys.body.space.reindex_shapes_for_body(child_phys.body)

                child_trans = world.get_component(child_id, Transform)
                if child_trans:
                    child_trans.x = child_pos.x
                    child_trans.y = child_pos.y
                    child_trans.prev_x = child_prev_pos.x
                    child_trans.prev_y = child_prev_pos.y

                stack.append((child_id, child_pos, child_rot, child_prev_pos))

    def process_pending_dismounts(self, world: World, dt: float):
        """
        Handle entities that are trying to find a spot to dismount.
        """
        for entity, (pending, trans, phys) in world.get_components_tuple(PendingDismount, Transform, PhysicsBody):
            # logger.trace(f"Processing pending dismount for entity {entity}")
            pending.time_in_pending += dt

            # Check timeout
            if pending.time_in_pending > 5.0:
                 # Emergency Teleport
                 # Teleport to (0,0) or some safe spot
                 phys.body.position = pymunk.Vec2d(0, 0)
                 trans.x = 0
                 trans.y = 0
                 world.remove_component(entity, PendingDismount)
                 if phys.shape.sensor:
                     phys.shape.sensor = False
                 continue

            # Search for a valid spot
            found_spot = False
            target_pos = phys.body.position
            search_radius = 50.0

            # Concentric/Spiral Search Pattern
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
                # Expand search
                pymunk.Vec2d(search_radius*2, 0),
                pymunk.Vec2d(-search_radius*2, 0),
                pymunk.Vec2d(0, search_radius*2),
                pymunk.Vec2d(0, -search_radius*2),
            ]

            space = phys.body.space
            if not space:
                continue

            collider_radius = 10.0
            if hasattr(phys.shape, 'radius'):
                collider_radius = phys.shape.radius

            for offset in offsets:
                candidate_pos = target_pos + offset

                # Check for overlap with walls
                # point_query checks if point is INSIDE a shape.
                # We need to check if our SHAPE would overlap.
                # shape_query is better.

                # Create a temporary shape or use point_query with radius?
                # point_query_nearest finds distance to nearest shape.

                info = space.point_query_nearest(candidate_pos, collider_radius + 1.0, pymunk.ShapeFilter(mask=CollisionCategories.WALL))

                # info.distance is distance to surface. Negative means inside.
                # We want distance > collider_radius (approximately) to be safe?
                # Wait, point_query_nearest returns info about the nearest point on a shape.
                # If distance < 0, we are inside.

                # Using point_query_nearest(pos, max_dist, filter)
                # If it finds something within max_dist, it returns it.
                # If we want to check if free:
                # If info is None (nothing within max_dist), we are good (assuming max_dist covers our radius).
                # But point_query_nearest checks infinite distance? No, max_distance is 2nd arg.

                # Actually, correct way to check "Can I place here?" is shape_query.
                # But we can't easily move the shape to query without modifying body.
                # Alternative: point_query with (radius + skin).

                # If we use point_query_nearest with max_dist = collider_radius:
                # If it returns a hit with dist < 0, we are overlapping.
                # If dist > 0, we are near but not overlapping?

                # Let's try to trust point_query for now.
                # Check if point is inside any WALL.

                # Use a cleaner check:
                # Check if position is valid.

                # Simple check:
                query = space.point_query_nearest(candidate_pos, 0, pymunk.ShapeFilter(mask=CollisionCategories.WALL))

                if query and query.distance < collider_radius:
                     # Too close or inside
                     continue

                # If safe:
                phys.body.position = candidate_pos
                trans.x = candidate_pos.x
                trans.y = candidate_pos.y

                world.remove_component(entity, PendingDismount)
                if phys.shape.sensor:
                    phys.shape.sensor = False

                if space:
                    space.reindex_shapes_for_body(phys.body)

                found_spot = True
                break
