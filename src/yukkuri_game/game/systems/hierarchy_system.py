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
            # We NO LONGER resize the root collider ("The Totem Pole" fix).
            # The root's movement collider is fixed.
            self.process_entity(world, root, mounts)

        # 4. Process Pending Dismounts (Now immediate or short-lived)
        self.process_dismounts(world)

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

    def process_dismounts(self, world: World):
        """
        Handle entities that need to be placed back into the world.
        Uses a Spiral Search to find a spot IMMEDIATELY.
        """
        # We process all PendingDismounts this frame.
        # If we can't find a spot, we might have to force it or fail.

        components = world.get_components_tuple(PendingDismount, Transform, PhysicsBody)

        # Collect to remove component later (modifying during iteration safety)
        to_remove = []

        for entity, (pending, trans, phys) in components:
            space = phys.body.space
            if not space:
                continue

            start_pos = phys.body.position
            collider_radius = _DISMOUNT_DEFAULT_RADIUS
            if hasattr(phys.shape, 'radius'):
                collider_radius = phys.shape.radius

            # Spiral Search
            # Theta step: depends on radius. Arc length ~ radius/2?
            # r = a + b*theta

            found_pos = None
            max_radius = _DISMOUNT_MAX_SEARCH_RADIUS # How far are we willing to look?
            current_r = 0.0
            theta = 0.0
            step_size = collider_radius * 2.0 # Check every diameter roughly

            # Safety limit
            max_checks = _DISMOUNT_MAX_SEARCH_CHECKS
            checks = 0

            # Check origin first
            # Note: point_query_nearest finds the closest shape. If it returns something,
            # it means a shape is within 'max_distance'. So returning 'info' is bad here.
            # We assume max_distance=collider_radius means we are checking if anything overlaps our radius.
            # If info is returned, we have a collision.
            info = space.point_query_nearest(start_pos, collider_radius, pymunk.ShapeFilter(mask=CollisionCategories.WALL))
            if info is None: # Nothing within radius -> Valid
                 found_pos = start_pos

            if not found_pos:
                while current_r < max_radius and checks < max_checks:
                    checks += 1

                    # Generate candidate
                    offset = pymunk.Vec2d(current_r * math.cos(theta), current_r * math.sin(theta))
                    candidate = start_pos + offset

                    # Check
                    info = space.point_query_nearest(candidate, collider_radius, pymunk.ShapeFilter(mask=CollisionCategories.WALL))

                    if info is None:
                        found_pos = candidate
                        break

                    # Advance spiral
                    # approximate arc length
                    arc = collider_radius
                    d_theta = arc / (current_r if current_r > 0.1 else 1.0)
                    theta += d_theta
                    current_r = (step_size / (2*math.pi)) * theta # Archimedean spiral r = b*theta

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
                # If we fail, we FORCE them at the parents position but kept as Sensor?
                # Or we just accept the overlap (tunneling) and let depenetration handle it next frame?

                # Let's try forcing overlap but resetting velocity so they don't explode.
                phys.body.position = start_pos
                if phys.shape.sensor:
                    phys.shape.sensor = False # Be physical

                # They will be inside the wall. The KinematicMovementSystem depenetration will push them out next frame.
                to_remove.append(entity)

        for ent in to_remove:
            world.remove_component(ent, PendingDismount)
