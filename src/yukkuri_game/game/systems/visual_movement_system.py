"""
Module defining the visual movement system.
"""

import math
import pymunk
from ...engine.ecs import System, World
from ..components import PhysicsBody, MovementController, VisualTransform
from ..skill_service import SkillService
from ..skill_constants import SkillId


class VisualMovementSystem(System):
    XP_SPEED_SCALAR = 100.0
    MAX_XP_GAIN_PER_SECOND = 5.0
    """
    Updates visual transforms for effects like hopping and handles side effects of movement (like XP).
    Does NOT update physics bodies directly (that is handled by KinematicMovementSystem).
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
            # NOTE: We do NOT set velocity here. KinematicMovementSystem does that.

            # 1. Update the visual bobbing timer based on speed
            # Use current_velocity which is set by KinematicMovementSystem
            if phys.body.body_type == pymunk.Body.KINEMATIC:
                # Use the controller's current_velocity (calculated from virtual physics)
                speed = controller.current_velocity.length
            else:
                # Fallback for dynamic bodies if any (though Proposal 4 says all are Kinematic)
                speed = phys.body.velocity.length

            if speed > 0.1:
                controller.visual_bob_timer += dt * controller.bob_speed

                # 2. Award Athletics XP
                if self.skill_service:
                    # Scale XP by speed
                    xp_gain = (speed / XP_SPEED_SCALAR) * dt
                    # Cap gain per frame
                    xp_gain = min(xp_gain, MAX_XP_GAIN_PER_SECOND * dt)

                    self.skill_service.add_xp(entity, SkillId.ATHLETICS, xp_gain)

            # 3. Calculate the vertical offset for the bobbing effect
            # Simple absolute sine wave creates a hopping/bobbing motion typical of Yukkuri.
            bob_offset = (
                abs(math.sin(controller.visual_bob_timer)) * controller.bob_height
            )
            visual.vertical_offset = bob_offset

            # 4. Ensure the shadow's position is locked to the entity's ground position
            # This is purely visual; the shadow indicates the actual position on the 2D plane.
            visual.shadow_position = phys.body.position
