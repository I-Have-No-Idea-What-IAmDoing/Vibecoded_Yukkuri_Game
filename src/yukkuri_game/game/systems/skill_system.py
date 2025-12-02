"""
Module defining the SkillSystem, responsible for managing skill decay and other periodic updates.
"""
from typing import Optional
from ...engine.ecs import System, World
from ..skill_service import SkillService
from ..services import TimeService

class SkillSystem(System):
    """
    System responsible for managing skill updates, specifically decay.
    """

    def __init__(self) -> None:
        super().__init__()
        self.skill_service: Optional[SkillService] = None
        self.time_service: Optional[TimeService] = None

    def update(self, world: World, dt: float) -> None:
        if not self.skill_service:
            self.skill_service = world.services.try_get(SkillService)

        if not self.time_service:
            self.time_service = world.services.try_get(TimeService)

        if self.skill_service and self.time_service:
            # We don't need to pass world because skill_service has it
            # But the existing service structure might need update
            self.skill_service.update_skills(self.time_service.time_elapsed)
