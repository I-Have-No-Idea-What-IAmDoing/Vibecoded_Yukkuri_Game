"""
Module defining the kinematic movement system.
Implements the Sweep-and-Slide algorithm for robust, deterministic movement.
"""

import math
import pymunk
from pymunk.vec2d import Vec2d as Vector2
from ...engine.ecs import System, World
from ..components import PhysicsBody, MovementController, VisualTransform
from ..skill_service import SkillService
from ..skill_constants import SkillId
from ..systems.physics import PhysicsSystem


class MovementSystem(System):
    """
    Applies AI-driven velocity commands using a deterministic Sweep-and-Slide algorithm.
    This replaces the previous physics-engine-driven movement for characters.
    """

    def __init__(self):
        super().__init__()
        self.skill_service = None
        self.physics_system = None

    def update(self, world: World, dt: float) -> None:
        """
        Updates entities with movement commands using Sweep-and-Slide.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.
        """
        if not self.skill_service:
            self.skill_service = world.services.try_get(SkillService)
        if not self.physics_system:
            self.physics_system = world.services.try_get(PhysicsSystem)

        space = self.physics_system.space if self.physics_system else None
        if not space:
            return

        for entity, (phys, controller, visual, transform) in world.get_components_tuple(
            PhysicsBody, MovementController, VisualTransform, Transform
        ):
            # Only process Kinematic bodies (characters)
            if phys.body.body_type != pymunk.Body.KINEMATIC:
                continue

            # Override default position update to prevent Pymunk from double-integrating our manual movement.
            # We only want Pymunk to handle interactions with dynamic bodies, using the velocity we set.
            # Pymunk's default update is: pos += vel * dt.
            # We manually update pos in move_and_slide.
            if not getattr(phys.body, "_position_func_set", False):
                def no_op_position_update(body, dt):
                    pass
                phys.body.position_func = no_op_position_update
                phys.body._position_func_set = True

            # 1. Virtual Physics Integration
            input_velocity = controller.target_velocity
            current_velocity = input_velocity

            # Calculate move delta
            if dt > 0.1: # Clamp large dt
                dt = 0.1

            move_delta = current_velocity * dt

            # 2. Sweep-and-Slide
            if move_delta.length > 0.001:
                # Calculate new position manually
                final_pos = self.move_and_slide(space, phys.body, phys.shape, move_delta)

                # Calculate actual effective velocity for this frame (displacement / dt)
                # This is important for collisions with other dynamic objects.
                actual_displacement = final_pos - phys.body.position
                if dt > 0:
                    effective_velocity = actual_displacement / dt
                else:
                    effective_velocity = Vector2(0, 0)

                # Update State
                phys.body.position = final_pos
                phys.body.velocity = effective_velocity
                transform.x = final_pos.x
                transform.y = final_pos.y

            else:
                phys.body.velocity = Vector2(0, 0)

            # 3. Visual & Gameplay Logic
            speed = phys.body.velocity.length
            if speed > 0.1:
                controller.visual_bob_timer += dt * controller.bob_speed

                # Award Athletics XP
                if self.skill_service:
                    xp_gain = (speed / 100.0) * dt
                    xp_gain = min(xp_gain, 5.0 * dt)
                    self.skill_service.add_xp(entity, SkillId.ATHLETICS, xp_gain)

            bob_offset = (
                abs(math.sin(controller.visual_bob_timer)) * controller.bob_height
            )
            visual.vertical_offset = bob_offset
            visual.shadow_position = phys.body.position

    def move_and_slide(
        self, space: pymunk.Space, body: pymunk.Body, shape: pymunk.Shape, move_delta: Vector2
    ) -> Vector2:
        """
        Performs the sweep-and-slide algorithm.
        """
        current_pos = body.position
        remaining_move = move_delta
        epsilon = 0.1 # Small buffer distance

        # Max iterations to prevent infinite loops in corners
        for _ in range(3):
            if remaining_move.length < 0.001:
                break

            start = current_pos
            end = start + remaining_move

            # Use segment query with radius = collider radius
            radius = 0.0
            if isinstance(shape, pymunk.Circle):
                radius = shape.radius
            elif isinstance(shape, pymunk.Poly):
                # For polygons, use a radius that approximates the shape's size.
                bb = shape.bb
                radius = max(bb.right - bb.left, bb.top - bb.bottom) / 2.0

            # Segment query
            # filter excludes self and sensors
            query_filter = pymunk.ShapeFilter(
                mask=shape.filter.mask,
                group=shape.filter.group,
                categories=shape.filter.categories
            )

            info = space.segment_query_first(start, end, radius, query_filter)

            if info and info.shape != shape and not info.shape.sensor:
                 # Collision detected!

                # Safe fraction to move
                safe_fraction = max(0.0, info.alpha - (epsilon / remaining_move.length))

                # Move
                travel_vec = remaining_move * safe_fraction
                current_pos = current_pos + travel_vec

                # Remainder is the part we didn't move
                remaining_move = remaining_move - travel_vec

                # Slide: Project remainder onto plane tangent
                normal = info.normal

                # Slide
                dot = remaining_move.dot(normal)

                # Only slide if we are moving INTO the wall
                if dot < 0:
                    remaining_move = remaining_move - normal * dot

            else:
                # No collision, move full distance
                current_pos = current_pos + remaining_move
                break

        return current_pos
