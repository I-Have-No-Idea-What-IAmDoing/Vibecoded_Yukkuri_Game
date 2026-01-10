"""
Time System Module.
"""

from ...engine.ecs import System, World
from ..services import TimeService


class TimeSystem(System):
    """
    System that tracks game time using TimeService.

    Attributes:
        game_speed (float): The user-adjustable speed multiplier (0.5x - 5.0x).
        _time_service (TimeService): Reference to the time service.
    """

    def __init__(self) -> None:
        """Initializes the TimeSystem."""
        self.game_speed = 1.0
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

        # Apply user speed and update time
        physics_dt = dt * self.game_speed
        self._time_service.update(physics_dt)
        # Sync speed for HUD access
        self._time_service.game_speed = self.game_speed


