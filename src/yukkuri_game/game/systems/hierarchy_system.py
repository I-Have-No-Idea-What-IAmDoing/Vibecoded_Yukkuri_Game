"""
Module defining the hierarchy system for handling entity attachments.
"""

import math
import random
from collections import deque
import pymunk
from pymunk.vec2d import Vec2d as Vector2
from ...engine.ecs import System, World
from ..components import Transform, Mount, PhysicsBody, PendingDismount
from ..systems.physics import PhysicsSystem

class HierarchySystem(System):
    """
    Manages parent-child relationships, updating transforms and physics bodies.
    Also handles dismount logic (safe spot finding).
    """

    def __init__(self):
        super().__init__()
        self.physics_system = None

    def update(self, world: World, dt: float) -> None:
        """
        Updates the transforms of attached entities based on their parents.
        And processes PendingDismount entities.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.
        """
        if not self.physics_system:
            self.physics_system = world.services.try_get(PhysicsSystem)

        self._process_hierarchy(world)
        self._process_dismounts(world, dt)

    def _process_hierarchy(self, world: World) -> None:
        mounts = {}
        # Unpack the list wrapper esper returns
        for entity, (mount,) in world.get_components_tuple(Mount):
            mounts[entity] = mount

        # Find roots (those where parent_id is -1 or parent not in mounts)
        roots = [e for e, m in mounts.items() if m.parent_id == -1 or m.parent_id not in mounts]

        # Traverse
        queue = deque(roots)
        processed = set()

        while queue:
            parent_entity = queue.popleft()
            if parent_entity in processed:
                continue
            processed.add(parent_entity)

            parent_mount = mounts.get(parent_entity)
            if not parent_mount:
                continue

            # Get Parent Transform
            parent_transform = world.get_component(parent_entity, Transform)
            if not parent_transform:
                continue

            # Get Parent Rotation and Velocity from PhysicsBody if available
            parent_phys = world.get_component(parent_entity, PhysicsBody)
            parent_angle = 0.0
            parent_velocity = Vector2(0, 0)
            parent_angular_velocity = 0.0

            if parent_phys:
                parent_angle = parent_phys.body.angle
                parent_velocity = parent_phys.body.velocity
                parent_angular_velocity = parent_phys.body.angular_velocity

                # Ensure Root is NOT a sensor (unless intended, but assuming characters here)
                if parent_phys.shape.sensor:
                    parent_phys.shape.sensor = False

            # Process Children
            for child_id in parent_mount.children_ids:
                if child_id not in mounts:
                    continue

                child_mount = mounts[child_id]
                child_transform = world.get_component(child_id, Transform)

                if child_transform:
                    # Calculate new position with rotation
                    # Offset is relative to parent, rotated by parent's angle
                    offset = child_mount.mount_point_offset
                    rotated_offset = offset.rotated(parent_angle)

                    target_x = parent_transform.x + rotated_offset.x
                    target_y = parent_transform.y + rotated_offset.y

                    # Update Child Physics Body if it exists
                    child_phys = world.get_component(child_id, PhysicsBody)

                    # Phase 2.3: Rotation Constraints / Blockage Check
                    # Check if the new position for the child is blocked by geometry.
                    blocked = False
                    if child_phys and self.physics_system:
                        space = self.physics_system.space

                        # Ensure Child IS a sensor
                        if not child_phys.shape.sensor:
                            child_phys.shape.sensor = True
                            # Force reindex to update physics state immediately?
                            space.reindex_shape(child_phys.shape)

                        # We use a point query or shape query at the target position.
                        # Since we haven't moved yet, we can check `(target_x, target_y)`.
                        # We should verify if this position overlaps with WALLs.
                        # Use child's mask
                        mask = child_phys.shape.filter.mask
                        radius = 10.0 # Fallback
                        if isinstance(child_phys.shape, pymunk.Circle):
                             radius = child_phys.shape.radius
                        elif isinstance(child_phys.shape, pymunk.Poly):
                             # For polygons, use a radius that approximates the shape's size.
                             bb = child_phys.shape.bb
                             radius = max(bb.right - bb.left, bb.top - bb.bottom) / 2.0

                        # Use point query for simplicity and speed, or check if center is blocked.
                        # Ideally shape query is better.
                        # We can use `space.point_query` for the center.
                        collisions = space.point_query((target_x, target_y), radius, pymunk.ShapeFilter(mask=mask))

                        for info in collisions:
                            if info.shape != child_phys.shape and not info.shape.sensor:
                                # Hit a wall!
                                blocked = True
                                break

                    if not blocked:
                        child_transform.x = target_x
                        child_transform.y = target_y

                        if child_phys:
                            child_phys.body.position = (target_x, target_y)
                            child_phys.body.angle = parent_angle # Lock rotation to parent

                            # Calculate Child Velocity
                            # V_child = V_parent + Omega x R
                            # R is the rotated offset vector
                            # Omega is angular velocity (scalar for 2D)

                            # Omega x R in 2D: (-omega * ry, omega * rx)
                            tangential_vel = Vector2(-parent_angular_velocity * rotated_offset.y, parent_angular_velocity * rotated_offset.x)

                            child_velocity = parent_velocity + tangential_vel
                            child_phys.body.velocity = child_velocity
                    else:
                         # Blocked: Do not update transform or physics position.
                         # This creates a "stuck" effect.
                         pass

                queue.append(child_id)

    def _process_dismounts(self, world: World, dt: float) -> None:
        """
        Processes entities attempting to dismount.
        """
        if not self.physics_system:
            return

        space = self.physics_system.space

        entities_to_remove = []

        for entity, (dismount, transform, phys) in world.get_components_tuple(PendingDismount, Transform, PhysicsBody):
            dismount.time_in_pending += dt
            dismount.retry_timer += dt

            if dismount.retry_timer < dismount.retry_interval:
                continue

            dismount.retry_timer = 0.0

            # Search for a safe spot
            # Concentric search or Spiral search
            # We want to find a spot near current location that is free of collisions.

            if self._find_and_move_to_safe_spot(space, entity, transform, phys):
                # Success! Remove PendingDismount and Mount (if any left over)
                entities_to_remove.append(entity)
                continue

            # Timeout check
            if dismount.time_in_pending > dismount.timeout:
                # Emergency teleport to safe zone
                # If no safe spot found, we force it to a fallback position (e.g. (0,0) or current position)
                # Removing PendingDismount effectively "drops" it wherever it is, even if invalid.
                entities_to_remove.append(entity)

                # Force position to (0, 0) as a fallback safe zone as per spec suggestion
                transform.x = 0.0
                transform.y = 0.0
                if phys:
                    phys.body.position = (0.0, 0.0)
                    phys.body.velocity = (0, 0)

        # Apply removals
        for entity in entities_to_remove:
            world.remove_component(entity, PendingDismount)
            if world.has_component(entity, Mount):
                mount = world.get_component(entity, Mount)
                mount.parent_id = -1

    def _find_and_move_to_safe_spot(self, space: pymunk.Space, entity: int, transform: Transform, phys: PhysicsBody) -> bool:
        """
        Tries to find a safe spot for the entity.
        Returns True if found and moved.
        """
        # Radius of the entity
        radius = 10.0
        if isinstance(phys.shape, pymunk.Circle):
            radius = phys.shape.radius

        # Current position (which might be the parent's position or last known)
        start_x, start_y = transform.x, transform.y
        original_pos = phys.body.position

        # Search pattern: standard offsets then spiral
        offsets = [
            (0, 0), # Try current spot
            (radius * 2, 0), (-radius * 2, 0), (0, radius * 2), (0, -radius * 2), # Cardinal
            (radius * 2, radius * 2), (radius * 2, -radius * 2), # Diagonals
            (-radius * 2, radius * 2), (-radius * 2, -radius * 2)
        ]

        # Spiral expansion could go here

        for dx, dy in offsets:
            cx = start_x + dx
            cy = start_y + dy

            # Check if spot is free using shape_query for maximum accuracy

            # Move the body to the candidate position
            phys.body.position = (cx, cy)
            space.reindex_shape(phys.shape)

            # Query for overlaps
            # shape_query returns all shapes that overlap with the given shape
            collisions = space.shape_query(phys.shape)

            valid_spot = True
            for info in collisions:
                # Ignore self and sensors
                if info.shape != phys.shape and not info.shape.sensor:
                    # Ignore if the other shape matches our mask?
                    # info.shape is what we hit. We should respect collision masks.
                    # Physics logic: (A.cat & B.mask) != 0 and (B.cat & A.mask) != 0

                    cat_a = phys.shape.filter.categories
                    mask_a = phys.shape.filter.mask
                    cat_b = info.shape.filter.categories
                    mask_b = info.shape.filter.mask

                    if (cat_a & mask_b) != 0 and (cat_b & mask_a) != 0:
                        valid_spot = False
                        break

            if valid_spot:
                # Move there permanently
                transform.x = cx
                transform.y = cy
                # phys.body.position is already set

                # Make sure we are solid again
                phys.shape.sensor = False

                return True

        # If failed, revert position
        phys.body.position = original_pos
        space.reindex_shape(phys.shape)

        return False
