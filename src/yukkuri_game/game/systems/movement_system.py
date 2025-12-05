"""
Module defining the kinematic movement system.
Implements the Sweep-and-Slide algorithm for robust, deterministic movement.
"""

import math
import pymunk
from pymunk.vec2d import Vec2d as Vector2
from ...engine.ecs import System, World
from ..components import PhysicsBody, MovementController, VisualTransform, Transform
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
            # Apply Acceleration / Friction
            target_vel = controller.target_velocity
            current_vel = phys.body.velocity

            if dt > 0.1: # Clamp large dt
                dt = 0.1

            # If we have input (target_vel > 0), accelerate towards it
            if target_vel.length > 0.001:
                # Accelerate
                # Calculate direction to target
                diff = target_vel - current_vel

                # Max change allowed this frame
                change_limit = controller.acceleration * dt

                if diff.length <= change_limit:
                    current_vel = target_vel
                else:
                    current_vel += diff.normalized() * change_limit
            else:
                # Friction (Decelerate)
                speed = current_vel.length
                if speed > 0:
                    drop = controller.friction * dt
                    if speed <= drop:
                        current_vel = Vector2(0, 0)
                    else:
                        current_vel -= current_vel.normalized() * drop

            # Clamp to max speed if needed (though acceleration logic should handle it if target is clamped)
            if current_vel.length > controller.max_speed:
                current_vel = current_vel.normalized() * controller.max_speed

            move_delta = current_vel * dt

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

                # We should NOT update velocity based on displacement if we want to preserve slide momentum?
                # Actually, if we slide, the velocity SHOULD change to reflect the slide.
                # move_and_slide logic updates position.
                # If we hit a wall, we stopped or slid.

                phys.body.velocity = effective_velocity
                transform.x = final_pos.x
                transform.y = final_pos.y

            else:
                phys.body.velocity = current_vel # Even if we don't move, we keep velocity? No, move_delta is derived from current_vel.
                # If move_delta is small, it means current_vel is small.
                pass

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
        Performs the discrete collision resolution algorithm (Move -> Depenetrate -> Slide).
        Subdivides movement to prevent tunneling.
        """
        start_pos = body.position

        # 1. Determine Step Size to prevent tunneling
        # Use radius as a safe step size.
        radius = 10.0
        if isinstance(shape, pymunk.Circle):
            radius = shape.radius
        elif isinstance(shape, pymunk.Poly):
            bb = shape.bb
            radius = min(bb.right - bb.left, bb.top - bb.bottom) / 2.0

        # Ensure minimum step to avoid infinite loops
        step_size = max(radius * 0.9, 1.0)
        total_dist = move_delta.length

        if total_dist < 0.001:
            return start_pos

        num_steps = math.ceil(total_dist / step_size)
        step_move = move_delta / num_steps

        current_pos = start_pos

        # Track velocity modification for subsequent steps
        # If we slide, we change direction.
        current_velocity = step_move * num_steps

        # We process step by step
        for _ in range(num_steps):
            if current_velocity.length < 0.001:
                break

            step_vec = current_velocity.normalized() * min(step_size, current_velocity.length)

            # Attempt to move full step
            target_pos = current_pos + step_vec

            # Move body to target
            body.position = target_pos
            space.reindex_shape(shape)

            # Resolve Collisions iteratively
            for _ in range(3): # Max resolution iterations
                overlaps = space.shape_query(shape)

                collision_found = False
                max_pen = 0.0
                best_normal = Vector2(0, 0)

                for info in overlaps:
                    if info.shape != shape and not info.shape.sensor:
                        cps = info.contact_point_set

                        # Find deepest penetration in this contact set
                        min_dist_in_set = 0.0
                        for p in cps.points:
                            if p.distance < min_dist_in_set:
                                min_dist_in_set = p.distance

                        if min_dist_in_set < -0.001: # Tolerance
                            collision_found = True
                            penetration = -min_dist_in_set

                            if penetration > max_pen:
                                max_pen = penetration
                                best_normal = cps.normal

                if collision_found and max_pen > 0:
                    # Depenetrate
                    # Normal usually points OUT of the hit shape (towards us).
                    # So we move +Normal * Penetration.
                    push_vector = best_normal * (max_pen + 0.01) # Small epsilon buffer
                    body.position = body.position + push_vector
                    space.reindex_shape(shape)

                    # Slide velocity
                    # Remove velocity component against normal
                    dot = current_velocity.dot(best_normal)
                    if dot < 0:
                        current_velocity = current_velocity - best_normal * dot

                else:
                    break

            current_pos = body.position

            # Decrease remaining velocity magnitude by what we just moved?
            # Or just rely on re-calculating step_vec from current_velocity?
            # The loop is fixed count, but velocity might change direction/magnitude.
            # If we slide, velocity changes.
            # We consumed 'step_size' of magnitude (roughly).

            # Better logic:
            # We have 'time' remaining.
            # velocity is speed * direction.
            # We step for dt/N time.
            # If velocity changes, subsequent steps use new velocity.

            # Actually, let's just subtract the step vector we USED from total?
            # But sliding changes direction.

            # Simplified: Just update position. Velocity update is implicit if we want to preserve momentum?
            # No, 'current_velocity' variable holds the REMAINING movement vector essentially?
            # No, it holds the current velocity vector (displacement for full frame).

            # Let's effectively reduce the "magnitude to travel" by step_size.
            if current_velocity.length > step_size:
                current_velocity = current_velocity.normalized() * (current_velocity.length - step_size)
            else:
                current_velocity = Vector2(0, 0)

        return current_pos
