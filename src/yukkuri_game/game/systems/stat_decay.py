from ...engine.ecs import System, World
from ..yukkuri_components import YukkuriStats
from ...config import StatDecaySettings

class StatDecaySystem(System):
    """
    System responsible for decaying Yukkuri stats over time.

    Attributes:
        settings (StatDecaySettings): The configuration settings for decay rates.
    """

    def __init__(self, settings: StatDecaySettings | None = None):
        """
        Initializes the StatDecaySystem.

        Args:
            settings (StatDecaySettings | None): Stat decay settings configuration.
        """
        self.settings = settings if settings is not None else StatDecaySettings()

    def update(self, world: World, dt: float) -> None:
        """
        Decays stats for all entities with YukkuriStats component.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.
        """
        # Iterate over entities with YukkuriStats
        # Note: unpack the tuple returned by get_components_tuple
        for entity, (stats,) in world.get_components_tuple(YukkuriStats):
            # Decay stats
            stats.hunger += self.settings.hunger * dt
            stats.happiness -= self.settings.happiness * dt
            stats.energy -= self.settings.energy * dt
            stats.age += self.settings.age * dt
            stats.cleanliness -= self.settings.cleanliness * dt

            # Clamp
            stats.hunger = min(100, max(0, stats.hunger))
            stats.happiness = min(100, max(0, stats.happiness))
            stats.energy = min(100, max(0, stats.energy))
            stats.cleanliness = min(100, max(0, stats.cleanliness))
