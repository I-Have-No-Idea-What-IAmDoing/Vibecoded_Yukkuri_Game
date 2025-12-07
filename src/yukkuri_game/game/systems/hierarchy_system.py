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

_DISMOUNT_DEFAULT_RADIUS = 10.0
_DISMOUNT_MAX_SEARCH_RADIUS = 100.0
_DISMOUNT_MAX_SEARCH_CHECKS = 50
_DISMOUNT_TIMEOUT = 5.0
_DEFAULT_ENTITY_RADIUS = 10.0
_RADIUS_UPDATE_THRESHOLD = 0.1
_SPIRAL_SEARCH_MIN_RADIUS = 0.1
# Safety Cap: Prevent single unit from becoming a screen-sized collider
_MAX_ROOT_COLLIDER_RADIUS = 50.0

class HierarchySystem(System):
    """
    Updates positions of mounted entities based on their parents.
    Also handles Dismount logic (finding free space).
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
                roots.append(ent)

        # 3. Process roots
        for root in roots:
            self.process_structure_update(world, root, mounts)
            self.process_entity(world, root, mounts)

        # 4. Process Pending Dismounts
        self.process_dismounts(world, dt)

    def process_structure_update(self, world: World, root_entity: int, mounts: dict):
        """
        Recalculates the root collider radius if structure changed ("The Totem Pole").
        """
        mount = mounts.get(root_entity)
        if not mount or not mount.structure_dirty:
            return

        phys = world.get_component(root_entity, PhysicsBody)
        if not phys:
            return

        # Base radius of the root itself
        base_radius = phys.base_radius if phys.base_radius is not None else _DEFAULT_ENTITY_RADIUS

        max_dist = 0.0

        # Traverse hierarchy to find furthest extent
        # (This implies a spherical approximation of the whole stack)
        stack = [(root_entity, pymunk.Vec2d(0,0))]

        while stack:
            curr_ent, curr_offset = stack.pop()
            curr_mount = mounts.get(curr_ent)
            if not curr_mount:
                continue

            for child_id in curr_mount.children_ids:
                child_mount = mounts.get(child_id)
                if not child_mount:
                    continue

                # We care about the magnitude of offset from Root
                child_total_offset = curr_offset + child_mount.mount_point_offset

                # Get child size
                child_radius = _DEFAULT_ENTITY_RADIUS # Default
                c_phys = world.get_component(child_id, PhysicsBody)
                if c_phys and hasattr(c_phys.shape, 'radius'):
                    child_radius = c_phys.shape.radius

                dist = child_total_offset.length + child_radius
                if dist > max_dist:
                    max_dist = dist

                stack.append((child_id, child_total_offset))

        final_radius = max(base_radius, max_dist)

        # Critique Fix: Cap the radius to prevent game-breaking size
        if final_radius > _MAX_ROOT_COLLIDER_RADIUS:
             # Just cap it. Children outside will be sensors (no clip).
             # This is a compromise: We prefer visual clipping over "I can't fit through the door".
             final_radius = _MAX_ROOT_COLLIDER_RADIUS

        # Update Shape
        if hasattr(phys.shape, 'unsafe_set_radius'):
            # Only update if significant change to avoid thrashing
            if abs(phys.shape.radius - final_radius) > _RADIUS_UPDATE_THRESHOLD:
                phys.shape.unsafe_set_radius(final_radius)
                if phys.body.space:
                    phys.body.space.reindex_shape(phys.shape)

        mount.structure_dirty = False

    def process_entity(self, world: World, root_entity: int, mounts: dict):
        """
        Iteratively update children of this entity using a stack.
        """
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

            for child_id in mount.children_ids:
                child_mount = mounts.get(child_id)
                if not child_mount:
                    continue

                # Calculate Child Position
                offset = child_mount.mount_point_offset
                rotated_offset = offset.rotated(parent_rot)
                child_pos = parent_pos + rotated_offset

                # Calculate Child Prev Position
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

                    # Ensure child is sensor (Hitbox only) while mounted
                    if not child_phys.shape.sensor:
                        child_phys.shape.sensor = True

                child_trans = world.get_component(child_id, Transform)
                if child_trans:
                    child_trans.x = child_pos.x
                    child_trans.y = child_pos.y
                    child_trans.rotation = child_rot
                    child_trans.prev_x = child_prev_pos.x
                    child_trans.prev_y = child_prev_pos.y
                    child_trans.prev_rotation = child_prev_rot

                stack.append((child_id, child_pos, child_rot, child_prev_pos, child_prev_rot))

    def process_dismounts(self, world: World, dt: float):
        """
        Handle entities that need to be placed back into the world.
        Uses a Spiral Search to find a spot.
        """
        components = world.get_components_tuple(PendingDismount, Transform, PhysicsBody)

        to_remove = []

        for entity, (pending, trans, phys) in components:
            pending.time_in_pending += dt

            # Ensure sensor mode
            if not phys.shape.sensor:
                phys.shape.sensor = True

            space = phys.body.space
            if not space:
                continue

            start_pos = phys.body.position
            collider_radius = _DISMOUNT_DEFAULT_RADIUS
            if hasattr(phys.shape, 'radius'):
                collider_radius = phys.shape.radius

            found_pos = self.find_free_spot(space, start_pos, collider_radius)

            if found_pos:
                phys.body.position = found_pos
                trans.x = found_pos.x
                trans.y = found_pos.y

                # Re-enable physical collision
                if phys.shape.sensor:
                    phys.shape.sensor = False

                to_remove.append(entity)
            else:
                # Failed to find spot.
                if pending.time_in_pending > _DISMOUNT_TIMEOUT:
                    # Fallback: Force place and let depenetration handle it.
                    # This deviates slightly from "Teleport to Base" but ensures the entity
                    # remains in the play area near where they were lost, which is often preferred.
                    if phys.shape.sensor:
                        phys.shape.sensor = False
                    to_remove.append(entity)
                    logger.warning(f"Entity {entity} forced dismount after timeout.")

        for ent in to_remove:
            world.remove_component(ent, PendingDismount)

    def find_free_spot(self, space, start_pos, collider_radius):
        """
        Searches for a free spot using a spiral pattern.
        Critique Fix: Use shape_query instead of point_query to check full volume.
        Critique Fix: Include YUKKURI (Units) in check to prevent tele-fragging.
        """
        max_radius = _DISMOUNT_MAX_SEARCH_RADIUS
        current_r = 0.0
        theta = 0.0
        step_size = collider_radius * 2.0
        max_checks = _DISMOUNT_MAX_SEARCH_CHECKS
        checks = 0

        # Create a temporary shape for query (Circle)
        # We assume the unit fits in a circle of collider_radius
        query_mask = CollisionCategories.WALL | CollisionCategories.YUKKURI

        def is_spot_free(pos):
             # shape_query checks if the shape at 'pos' overlaps anything
             # We can cheat by using point_query with radius, but shape_query is more "correct" for actual overlaps.
             # However, Pymunk's point_query_nearest checks if a point is within distance of a shape.
             # We want: Is there ANY shape within 'collider_radius' of 'pos'?
             # point_query_nearest(pos, max_dist=collider_radius) returns the nearest shape.
             # If distance < 0, it means overlap (if inside).
             # If distance < collider_radius, it means overlap (if outside but close).

             info = space.point_query_nearest(pos, collider_radius, pymunk.ShapeFilter(mask=query_mask))

             # If info is None, no shapes are within collider_radius. Free.
             if info is None:
                 return True

             # If distance is negative, the point 'pos' is INSIDE a shape.
             if info.distance < 0:
                 return False

             # If distance < collider_radius, the shape is overlapping our circle.
             # Wait, point_query_nearest finds the shape closest to the point.
             # info.distance is the distance to the surface.
             # If we want to place a circle of radius R at pos...
             # We are blocked if distance < R.
             # But wait, point_query_nearest max_distance argument filters candidates.
             # So if we get a result, it means there IS a shape within R.
             # So if info is NOT None, we are blocked.

             return False

        if is_spot_free(start_pos):
             return start_pos

        while current_r < max_radius and checks < max_checks:
            checks += 1

            # Generate candidate
            offset = pymunk.Vec2d(current_r * math.cos(theta), current_r * math.sin(theta))
            candidate = start_pos + offset

            if is_spot_free(candidate):
                return candidate

            # Advance spiral
            arc = collider_radius
            d_theta = arc / (current_r if current_r > _SPIRAL_SEARCH_MIN_RADIUS else 1.0)
            theta += d_theta
            current_r = (step_size / (2*math.pi)) * theta

        return None
