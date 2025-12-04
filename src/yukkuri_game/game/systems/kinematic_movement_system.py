"""
Kinematic Movement System (Controller Pattern).
"""

import math
import pymunk
from pymunk import Vec2d
from ...engine.ecs import System, World
from ..components import PhysicsBody, MovementController, VisualTransform, Mount
from ..systems.physics import PhysicsSystem
from ..skill_service import SkillService
from ..skill_constants import SkillId

class KinematicMovementSystem(System):
    """
    Implements Deterministic Kinematic Movement.
    Treats physics engine as a geometry database.
    """

    def __init__(self):
        super().__init__()
        self.physics_system = None
        self.space = None
        self.skill_service = None

    def update(self, world: World, dt: float) -> None:
        if not self.physics_system:
            self.physics_system = world.services.try_get(PhysicsSystem)
            if self.physics_system:
                self.space = self.physics_system.space

        if not self.skill_service:
            self.skill_service = world.services.try_get(SkillService)

        if not self.space:
            return

        for entity, (phys, controller, visual) in world.get_components_tuple(
            PhysicsBody, MovementController, VisualTransform
        ):
            # Only process Kinematic bodies
            if phys.body.body_type != pymunk.Body.KINEMATIC:
                continue

            # Skip mounted entities (children)
            mount = world.get_component(entity, Mount)
            if mount and mount.parent_id != -1:
                continue

            self.process_movement(entity, phys, controller, visual, dt)

    def process_movement(self, entity, phys, controller, visual, dt):
        # 1. Virtual Physics (Acceleration/Friction)
        ACCELERATION = 2000.0
        FRICTION = 10.0

        target_v = controller.target_velocity
        current_v = phys.body.velocity

        if target_v.length_squared == 0:
            # Apply friction
            if current_v.length > 0:
                # Friction reduces speed
                speed = current_v.length
                new_speed = max(0, speed - FRICTION * dt * 100) # Scaling friction
                if speed > 0:
                     current_v = current_v * (new_speed / speed)
        else:
            # Move towards target
            diff = target_v - current_v
            dist = diff.length
            max_change = ACCELERATION * dt
            if dist > max_change:
                diff = diff.normalized() * max_change
            current_v += diff

        phys.body.velocity = current_v

        # 2. Calculate Desired Vector
        move_delta = current_v * dt

        if move_delta.length_squared < 0.0001:
            # Still update visuals if needed (e.g. idle animation)
            visual.shadow_position = phys.body.position
            return

        # 3. The Sweep
        radius = 10.0
        if isinstance(phys.shape, pymunk.Circle):
            radius = phys.shape.radius

        start_pos = phys.body.position

        # 4. Resolve Collision
        final_pos = self.move_and_slide(start_pos, move_delta, radius, phys.shape)

        # 5. Commit
        phys.body.position = final_pos

        # Update Visuals
        speed = current_v.length
        if speed > 0.1:
            controller.visual_bob_timer += dt * controller.bob_speed

            # Award XP
            if self.skill_service:
                xp_gain = (speed / 100.0) * dt
                xp_gain = min(xp_gain, 5.0 * dt)
                self.skill_service.add_xp(entity, SkillId.ATHLETICS, xp_gain)

        bob_offset = (
            abs(math.sin(controller.visual_bob_timer)) * controller.bob_height
        )
        visual.vertical_offset = bob_offset
        visual.shadow_position = phys.body.position

        self.space.reindex_shapes_for_body(phys.body)

    def move_and_slide(self, start_pos, move_delta, radius, own_shape):
        remaining_move = move_delta
        current_pos = start_pos

        for _ in range(3):
            if remaining_move.length_squared < 0.0001:
                break

            target_pos = current_pos + remaining_move

            info = self.space.segment_query_first(
                current_pos,
                target_pos,
                radius,
                own_shape.filter
            )

            if info and info.shape != own_shape and not info.shape.sensor:
                # Hit
                alpha = info.alpha

                # Move to hit point (minus epsilon)
                safe_fraction = max(0.0, alpha - 0.01) # Epsilon

                current_pos = current_pos + remaining_move * safe_fraction

                # Slide
                remainder = remaining_move * (1.0 - safe_fraction)

                normal = info.normal

                # Project remainder
                dot = remainder.dot(normal)
                slide_vec = remainder - normal * dot

                remaining_move = slide_vec

            else:
                current_pos += remaining_move
                break

        return current_pos
