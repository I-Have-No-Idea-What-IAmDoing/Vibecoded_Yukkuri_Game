"""
Time System Module.
"""

from ..ecs import System, World
from ..services.time_service import TimeService
from yukkuri_game.game.systems.command_processor_system import CommandProcessorSystem


class TimeSystem(System):
    run_after = [CommandProcessorSystem]

    """
    System that tracks game time using TimeService.
    """

    def __init__(self) -> None:
        self._time_service: TimeService | None = None

    def update(self, world: World, dt: float) -> None:
        if self._time_service is None:
            self._time_service = world.services.try_get(TimeService)

        if self._time_service is None:
            return

        self._time_service.update(dt)
