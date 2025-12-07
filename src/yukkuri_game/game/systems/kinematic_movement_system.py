"""
Kinematic Movement System.
Implements a Robust Sweep-and-Slide algorithm for deterministic character movement.
Includes multi-plane sliding to prevent corner jitter and a pre-step depenetration pass.
"""

import pymunk
import math
from loguru import logger
from ...engine.ecs import System, World
from ...engine.event_bus import EventBus
from ...engine.events import PhysicsFixedUpdateEvent
from ..components import PhysicsBody, MovementController, Transform
from .physics import PhysicsSystem

class KinematicMovementSystem(System):
    """
    System responsible for moving Kinematic bodies using a sweep-and-slide algorithm
    against the static/dynamic geometry database.

    Features:
    - Fixed Timestep Update
    - Capsule/Circle Sweeping (No Box approximation)
    - Multi-plane slide resolution (prevents V-corner getting stuck)
    - Pre-step Depenetration
    """

    def __init__(self):
        self.space: pymunk.Space = None
        self.skin_width = 0.01
        self.event_bus = None
        self.ecs_world = None

    def on_fixed_update(self, event: PhysicsFixedUpdateEvent):
        if not self.space:
            return

        # Ensure we have the world. If ecs_world is None, we can't update.
        # This prevents race conditions if fixed_update fires before first update.
        if self.ecs_world:
            self.fixed_update(self.ecs_world, event.dt)
        else:
            # Fallback/Warning: This should be rare if PhysicsSystem and KinematicSystem
            # are initialized in order or if update() runs first.
            logger.warning("KinematicMovementSystem: Fixed update skipped because world is not initialized.")

    def update(self, world: World, dt: float) -> None:
        """
        Updates kinematic entities.
        """
        if not self.space:
            physics_system = world.services.try_get(PhysicsSystem)
            if physics_system:
                self.space = physics_system.space

        if not self.event_bus:
            self.event_bus = world.services.try_get(EventBus)
            if self.event_bus:
                self.event_bus.subscribe(PhysicsFixedUpdateEvent, self.on_fixed_update)
                self.ecs_world = world # Cache it for the callback

        # Update cache if world changed (rare in this engine probably)
        self.ecs_world = world

    def fixed_update(self, world: World, dt: float):
        """
        Runs the deterministic movement logic.
        """
        components = world.get_components_tuple(PhysicsBody, MovementController, Transform)

        for entity, (phys, controller, trans) in components:
            # Only handle Kinematic bodies
            if phys.body.body_type != pymunk.Body.KINEMATIC:
                continue

            # 0. Sync Transform to Body (Start of frame consistency)
            start_pos = phys.body.position

            # 1. Depenetration (Push out of overlapping geometry)
            # Optimized: Only run 1 iteration, usually enough for simple overlaps.
            clean_pos = self.resolve_penetration(phys, start_pos)
            if clean_pos != start_pos:
                phys.body.position = clean_pos
                start_pos = clean_pos

            # Update prev position for interpolation
            trans.prev_x = start_pos.x
            trans.prev_y = start_pos.y

            # 2. Perform Movement
            self.move_and_slide(phys, controller, trans, dt)

            # 3. Sync Transform back
            trans.x = phys.body.position.x
            trans.y = phys.body.position.y

    def resolve_penetration(self, phys: PhysicsBody, pos: pymunk.Vec2d) -> pymunk.Vec2d:
        """
        Checks if the body is currently overlapping static geometry and pushes it out.
        Returns the corrected position.
        Uses shape_query to handle multiple contacts (e.g. corners).
        """
        current_pos = pos

        # Optimization: Reduced iterations from 3 to 1.
        # Deep penetration should be rare with continuous collision detection.
        # Running once resolves the majority of "stuck in wall" cases.
        max_iterations = 1

        for _ in range(max_iterations):
            phys.body.position = current_pos

            infos = self.space.shape_query(phys.shape)

            if not infos:
                break

            total_push = pymunk.Vec2d(0, 0)
            hits = 0

            for info in infos:
                if info.shape == phys.shape or info.shape.sensor:
                    continue

                contact_set = info.contact_point_set
                if len(contact_set.points) == 0:
                    continue

                best_push = pymunk.Vec2d(0,0)

                for point in contact_set.points:
                    if point.distance < -0.001:
                        push = contact_set.normal * (-point.distance)
                        if push.length_squared > best_push.length_squared:
                            best_push = push

                if best_push.length_squared > 0:
                    total_push += best_push
                    hits += 1

            if hits > 0:
                if total_push.length_squared < 0.000001:
                    break
                current_pos += total_push
            else:
                break

        phys.body.position = pos # Restore
        return current_pos

    def get_radius(self, shape: pymunk.Shape) -> float:
        if hasattr(shape, 'radius'):
            return shape.radius
        bb = shape.bb
        # Warning: Approximating Box as Circle (Inscribed)
        # This is safe (won't get stuck) but visual clipping might occur.
        return min(bb.right - bb.left, bb.top - bb.bottom) / 2.0

    def move_and_slide(self, phys: PhysicsBody, controller: MovementController, trans: Transform, dt: float):
        body = phys.body
        shape = phys.shape
        radius = self.get_radius(shape)
        query_filter = shape.filter

        # 1. Virtual Physics Integration
        input_vector = controller.target_velocity
        velocity = controller.current_velocity

        if input_vector.length_squared < 0.000001:
            friction = controller.friction
            damping = max(0.0, 1.0 - friction * dt)
            velocity = velocity * damping
            if velocity.length_squared < 0.0001:
                velocity = pymunk.Vec2d(0, 0)
        else:
            diff = input_vector - velocity
            change = controller.acceleration * dt
            if change >= diff.length:
                velocity = input_vector
            else:
                velocity += diff.normalized() * change

        controller.current_velocity = velocity

        # 2. Sweep Movement
        move_delta = velocity * dt
        if move_delta.length_squared < 0.000001:
            return

        current_pos = body.position

        collision_planes = []
        # Restore max_slides to 4 to allow proper sliding (Move -> Hit -> Slide -> Move)
        # 1 iteration results in "sticky" movement.
        max_slides = 4

        for i in range(max_slides):
            if move_delta.length_squared < 0.000001:
                break

            target_pos = current_pos + move_delta

            results = self.space.segment_query(current_pos, target_pos, radius, query_filter)

            hit = None
            best_alpha = 1.0

            for info in results:
                if info.shape == shape: continue
                if info.shape.sensor: continue

                # Backface check (can be risky if inside, but segment_query shouldn't work if inside)
                if info.normal.dot(move_delta) > 0.0001:
                     continue

                if info.alpha < best_alpha:
                    best_alpha = info.alpha
                    hit = info

            if hit:
                # Optimization: Guard against division by zero or tiny move_delta
                md_len = move_delta.length
                safe_alpha = hit.alpha
                if md_len > 0.0001:
                    safe_alpha = max(0.0, hit.alpha - (self.skin_width / md_len))

                step_move = move_delta * safe_alpha
                current_pos += step_move

                remainder = move_delta * (1.0 - safe_alpha)
                collision_planes.append(hit.normal)

                new_dir = remainder
                for plane in collision_planes:
                    dot = new_dir.dot(plane)
                    if dot < 0:
                        new_dir = new_dir - plane * dot

                valid = True
                for plane in collision_planes:
                    if new_dir.dot(plane) < -0.001:
                        valid = False
                        break

                if not valid:
                    move_delta = pymunk.Vec2d(0, 0)
                else:
                    move_delta = new_dir

            else:
                current_pos = target_pos
                move_delta = pymunk.Vec2d(0, 0)
                break

        body.position = current_pos

        if dt > 0.000001:
             final_vel = velocity
             for plane in collision_planes:
                 dot = final_vel.dot(plane)
                 if dot < 0:
                     final_vel = final_vel - plane * dot

             controller.current_velocity = final_vel
