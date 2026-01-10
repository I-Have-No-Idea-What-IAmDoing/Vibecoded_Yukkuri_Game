"""
Time System Module.
"""

from ...engine.ecs import System, World
from ..services import TimeService


class TimeSystem(System):
    """
    System that tracks game time using TimeService.

    Delegates actual time tracking and speed control to the TimeService.
    This system is responsible for calling TimeService.update() each frame.

    Attributes:
        _time_service (TimeService): Reference to the time service.
    """

    def __init__(self) -> None:
        """Initializes the TimeSystem."""
        self._time_service: TimeService | None = None

    def update(self, world: World, dt: float) -> None:
        """
        Updates game time.

        Args:
            world (World): The ECS World.
            dt (float): Physics delta time.
        """
        # Lazy init
        if self._time_service is None:
            self._time_service = world.services.try_get(TimeService)

        if self._time_service is None:
            return

        # TimeService now handles speed multiplication internally
        self._time_service.update(dt)


