"""
Time System Module.
"""
from ...engine.ecs import System, World

class TimeSystem(System):
    """
    System that tracks the total elapsed game time.

    Attributes:
        total_time (float): The total accumulated time.
        game_speed (float): The speed multiplier for time.
    """

    def __init__(self) -> None:
        """Initializes the TimeSystem."""
        self.total_time = 0.0
        self.game_speed = 1.0

    def update(self, world: World, dt: float) -> None:
        """
        Updates the total time.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.

        Returns:
            None
        """
        self.total_time += dt * self.game_speed
