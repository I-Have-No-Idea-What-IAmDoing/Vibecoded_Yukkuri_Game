"""
Day/Night Cycle System.
"""

from ...engine.ecs import System, World
from ..services import TimeService
from ..systems.render_system import RenderSystem


class DayNightSystem(System):
    """
    Manages the ambient light color based on game time.
    """

    GAME_DAY_LENGTH: float = 600.0

    # Color Ramp (Time of Day -> Ambient Color)
    # Time is 0.0 to 24.0 (hours)
    AMBIENT_COLORS = [
        (0.0, (40, 40, 70)),  # Midnight (Brightened from 20,20,50 to be visible)
        (5.0, (40, 40, 70)),  # Early Morning (Dark)
        (6.0, (100, 100, 120)),  # Dawn
        (8.0, (255, 255, 255)),  # Morning
        (17.0, (255, 255, 255)),  # Late Afternoon
        (19.0, (150, 100, 100)),  # Dusk
        (21.0, (60, 50, 80)),  # Evening
        (24.0, (40, 40, 70)),  # Midnight Loop
    ]

    def __init__(self, world: World, renderer: RenderSystem) -> None:
        super().__init__()
        self.render_system = renderer
        self.time_service = world.services.get(TimeService)

    def _interpolate_color(self, c1: tuple[int, int, int], c2: tuple[int, int, int], t: float) -> tuple[int, int, int, int]:
        return (
            int(c1[0] + (c2[0] - c1[0]) * t),
            int(c1[1] + (c2[1] - c1[1]) * t),
            int(c1[2] + (c2[2] - c1[2]) * t),
            255,
        )

    def _get_ambient_color(self, time_of_day: float) -> tuple[int, int, int, int]:
        """Calculates ambient color based on time."""
        # Wrap time to 24h
        t = time_of_day % 24.0

        for i in range(len(self.AMBIENT_COLORS) - 1):
            t1, c1 = self.AMBIENT_COLORS[i]
            t2, c2 = self.AMBIENT_COLORS[i + 1]

            if t1 <= t <= t2:
                # Interpolate
                factor = (t - t1) / (t2 - t1)
                return self._interpolate_color(c1, c2, factor)

        return (*self.AMBIENT_COLORS[0][1], 255)  # Fallback

    def update(self, world: World, dt: float) -> None:
        time_of_day = self.time_service.time_of_day
        color = self._get_ambient_color(time_of_day)

        if hasattr(self.render_system, "set_ambient_light"):
            self.render_system.set_ambient_light(color)
