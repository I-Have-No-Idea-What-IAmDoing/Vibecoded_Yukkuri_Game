import math
import random
from typing import Tuple

class Steering:
    """
    Provides steering behaviors for smooth movement.
    """

    @staticmethod
    def _limit_magnitude(vector: Tuple[float, float], max_val: float) -> Tuple[float, float]:
        """Limits the magnitude of a vector."""
        mag = math.hypot(vector[0], vector[1])
        if mag > max_val and mag > 0:
             factor = max_val / mag
             return (vector[0] * factor, vector[1] * factor)
        return vector

    @staticmethod
    def seek(position: Tuple[float, float], target: Tuple[float, float], max_speed: float, velocity: Tuple[float, float] = (0.0, 0.0), max_force: float = 10.0) -> Tuple[float, float]:
        """
        Calculates the steering force to seek a target.

        Args:
            position: Current position (x, y).
            target: Target position (x, y).
            max_speed: Maximum movement speed.
            velocity: Current velocity (x, y).
            max_force: Maximum steering force (turn rate).

        Returns:
            Tuple[float, float]: The calculated new velocity.
        """
        # Desired velocity
        dx = target[0] - position[0]
        dy = target[1] - position[1]
        dist = math.hypot(dx, dy)

        if dist > 0:
            # Normalize and scale to max speed
            desired_vx = (dx / dist) * max_speed
            desired_vy = (dy / dist) * max_speed
        else:
            return (0.0, 0.0)

        # Steering force = desired - velocity
        steer_x = desired_vx - velocity[0]
        steer_y = desired_vy - velocity[1]

        # Limit steering force
        steer = Steering._limit_magnitude((steer_x, steer_y), max_force)

        # Apply steering to velocity
        new_vx = velocity[0] + steer[0]
        new_vy = velocity[1] + steer[1]

        # Limit final velocity
        return Steering._limit_magnitude((new_vx, new_vy), max_speed)

    @staticmethod
    def arrive(position: Tuple[float, float], target: Tuple[float, float], max_speed: float, slowing_radius: float = 100.0) -> Tuple[float, float]:
        """
        Calculates the velocity to arrive at a target, slowing down as it approaches.
        This is a simplified version that returns desired velocity directly, as 'arrive' implies slowing down which is velocity control.

        Args:
            position: Current position (x, y).
            target: Target position (x, y).
            max_speed: Maximum movement speed.
            slowing_radius: Distance at which to start slowing down.

        Returns:
             Tuple[float, float]: The desired velocity.
        """
        dx = target[0] - position[0]
        dy = target[1] - position[1]
        dist = math.hypot(dx, dy)

        if dist < 0.1:
            return (0.0, 0.0)

        # Calculate desired speed
        if dist < slowing_radius:
            speed = max_speed * (dist / slowing_radius)
        else:
            speed = max_speed

        # Desired velocity
        vx = (dx / dist) * speed
        vy = (dy / dist) * speed

        return (vx, vy)

    @staticmethod
    def wander(velocity: Tuple[float, float], max_speed: float, wander_radius: float = 50.0, wander_distance: float = 100.0, wander_jitter: float = 10.0) -> Tuple[float, float]:
        """
        Calculates a wander steering force.
        Note: This stateless implementation requires the caller to persist wander target or just use random jitter.
        Here we implement a simple random jitter based wander.

        Args:
            velocity: Current velocity.
            max_speed: Max speed.
            wander_radius: Radius of the wander circle.
            wander_distance: Distance the wander circle is offset.
            wander_jitter: Amount of random displacement.

        Returns:
             Tuple[float, float]: The new velocity.
        """
        # Get current heading
        current_speed = math.hypot(velocity[0], velocity[1])
        if current_speed < 0.1:
            # If stationary, pick random direction
            angle = random.uniform(0, math.pi * 2)
            return (math.cos(angle) * max_speed, math.sin(angle) * max_speed)

        heading_x = velocity[0] / current_speed
        heading_y = velocity[1] / current_speed

        # Center of wander circle
        circle_center_x = heading_x * wander_distance
        circle_center_y = heading_y * wander_distance

        # Random point on circle (jitter)
        # Since we don't store state, we just pick a random angle relative to heading
        # A true Reynolds wander stores the target angle.
        # Simplified: Add random vector to current velocity vector

        jitter_x = random.uniform(-1, 1) * wander_jitter
        jitter_y = random.uniform(-1, 1) * wander_jitter

        target_x = circle_center_x + jitter_x
        target_y = circle_center_y + jitter_y

        # Normalize to radius? Or just use as steering target?
        # Let's just return this as the new desired velocity direction

        mag = math.hypot(target_x, target_y)
        if mag > 0:
            return (target_x / mag * max_speed, target_y / mag * max_speed)

        return velocity
