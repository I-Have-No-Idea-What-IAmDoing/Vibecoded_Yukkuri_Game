"""
Day/Night Cycle System.
"""

from ..engine.system import System
from ..engine.ecs import World
from ..game.services import TimeService
from ..game.renderer import WorldRenderer, Light2DRenderBackend


class DayNightSystem(System):
    """
    Manages the ambient light color based on game time.
    """

    GAME_DAY_LENGTH: float = 600.0

    # Color Ramp (Time of Day -> Ambient Color)
    # Time is 0.0 to 24.0 (hours)
    AMBIENT_COLORS = [
        (0.0, (20, 20, 50)),  # Midnight
https://github.com/I-Have-No-Idea-What-IAmDoing/Vibecoded_Yukkuri_Game/pull/360/conflict?name=src%252Fyukkuri_game%252Fgame%252Fsystems%252Fsector_system.py&base_oid=fa1bff4a26529d47f7598553f44ea75798a158c0&head_oid=0082b8baa5b65e6e702ecc7ca40b88c75f1eda66        (5.0, (20, 20, 50)),  # Early Morning (Dark)
        (6.0, (100, 100, 120)),  # Dawn
        (8.0, (255, 255, 255)),  # Morning
        (17.0, (255, 255, 255)),  # Late Afternoon
        (19.0, (150, 100, 100)),  # Dusk
        (21.0, (50, 40, 60)),  # Evening
        (24.0, (20, 20, 50)),  # Midnight Loop
    ]

    def __init__(self, world: World, renderer: WorldRenderer) -> None:
        super().__init__(world)
        self.renderer = renderer
        self.time_service = world.services.get(TimeService)

    def _interpolate_color(self, c1, c2, t) -> tuple:
        return (
            int(c1[0] + (c2[0] - c1[0]) * t),
            int(c1[1] + (c2[1] - c1[1]) * t),
            int(c1[2] + (c2[2] - c1[2]) * t),
            255,
        )

    def _get_ambient_color(self, time_of_day: float) -> tuple:
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

        return self.AMBIENT_COLORS[0][1]  # Fallback

    def update(self, dt: float) -> None:
        # Assuming TimeService tracks elapsed time in seconds.
        # We need to map elapsed time to "Time of Day".
        # Let's assume 1 real second = 1 game minute? Or use configured ratio.
        # TimeService usually just accumulates time.
        # If time_scale is 1.0.

        # Simple mapping: TimeService.time_elapsed is total seconds.

        elapsed = self.time_service.time_elapsed
        day_progress = (elapsed % self.GAME_DAY_LENGTH) / self.GAME_DAY_LENGTH
        time_of_day = day_progress * 24.0

        color = self._get_ambient_color(time_of_day)

        # Update renderer
        if isinstance(self.renderer.backend, Light2DRenderBackend):
            self.renderer.backend.set_ambient_light(color)
