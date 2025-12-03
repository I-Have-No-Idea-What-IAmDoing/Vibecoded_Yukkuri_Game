"""
Module defining the kinematic movement system.
"""
import math
from ...engine.ecs import System, World
from ..components import PhysicsBody, MovementController, VisualTransform
from ..skill_service import SkillService
from ..skill_constants import SkillId

class MovementSystem(System):
    """
    Applies AI-driven velocity commands and updates visual transforms for effects like hopping.
    """

    def __init__(self):
        super().__init__()
        self.skill_service = None

    def update(self, world: World, dt: float) -> None:
        """
        Updates entities with movement commands.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.
        """
        if not self.skill_service:
            self.skill_service = world.services.try_get(SkillService)

        for entity, (phys, controller, visual) in world.get_components_tuple(
            PhysicsBody, MovementController, VisualTransform
        ):
            # 1. Apply AI-commanded velocity to the physics body
            # The 'controller.target_velocity' is usually set by the behavior system or input system.
            # We directly set the pymunk body velocity, allowing the physics engine to handle integration.
            phys.body.velocity = controller.target_velocity

            # 2. Update the visual bobbing timer based on speed
            # Only animate bobbing if the entity is moving appreciably.
            speed = phys.body.velocity.length
            if speed > 0.1:
                controller.visual_bob_timer += dt * controller.bob_speed

                # 3. Award Athletics XP
                # XP Gain based on speed and time.
                # Threshold for gain: moving at least a little bit.
                # Scale XP by speed to reward faster movement (sprinting/chasing).
                # Base 1.0 XP per second of movement at standard speed?
                if self.skill_service:
                    # Let's say speed 100.0 is standard.
                    # xp = (speed / 100.0) * dt
                    # This might be too fast, let's clamp or scale.
                    # Proposal: "Call SkillService.add_xp(entity, SkillId.ATHLETICS, 1.0)" when moving significant distance.
                    # Let's accumulate. But here we have continuous update.
                    xp_gain = (speed / 100.0) * dt
                    # Cap gain per frame to avoid crazy spikes
                    xp_gain = min(xp_gain, 5.0 * dt)

                    self.skill_service.add_xp(entity, SkillId.ATHLETICS, xp_gain)

            # 4. Calculate the vertical offset for the bobbing effect
            # Simple absolute sine wave creates a hopping/bobbing motion typical of Yukkuri.
            bob_offset = abs(math.sin(controller.visual_bob_timer)) * controller.bob_height
            visual.vertical_offset = bob_offset

            # 5. Ensure the shadow's position is locked to the entity's ground position
            # This is purely visual; the shadow indicates the actual position on the 2D plane.
            visual.shadow_position = phys.body.position
