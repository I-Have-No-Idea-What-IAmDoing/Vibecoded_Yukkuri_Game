"""
Module defining the kinematic movement system.
"""
import math
from ...engine.ecs import System, World
from ..components import PhysicsBody, MovementController, VisualTransform

class MovementSystem(System):
    """
    Applies AI-driven velocity commands and updates visual transforms for effects like hopping.
    """

    def update(self, world: World, dt: float) -> None:
        """
        Updates entities with movement commands.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.
        """
        for entity, (phys, controller, visual) in world.get_components_tuple(
            PhysicsBody, MovementController, VisualTransform
        ):
            # 1. Apply AI-commanded velocity to the physics body
            # The 'controller.target_velocity' is usually set by the behavior system or input system.
            # We directly set the pymunk body velocity, allowing the physics engine to handle integration.
            phys.body.velocity = controller.target_velocity

            # 2. Update the visual bobbing timer based on speed
            # Only animate bobbing if the entity is moving appreciably.
            if phys.body.velocity.length > 0.1:
                controller.visual_bob_timer += dt * controller.bob_speed

            # 3. Calculate the vertical offset for the bobbing effect
            # Simple absolute sine wave creates a hopping/bobbing motion typical of Yukkuri.
            bob_offset = abs(math.sin(controller.visual_bob_timer)) * controller.bob_height
            visual.vertical_offset = bob_offset

            # 4. Ensure the shadow's position is locked to the entity's ground position
            # This is purely visual; the shadow indicates the actual position on the 2D plane.
            visual.shadow_position = phys.body.position
