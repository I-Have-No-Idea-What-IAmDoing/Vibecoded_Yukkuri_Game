from ...engine.ecs import System, World
from ..yukkuri_components import YukkuriStats

class StatDecaySystem(System):
    """
    System responsible for decaying Yukkuri stats over time.
    """

    def update(self, world: World, dt: float) -> None:
        """
        Decays stats for all entities with YukkuriStats component.

        Args:
            world: The ECS World.
            dt: Delta time.
        """
        # Iterate over entities with YukkuriStats
        # Note: unpack the tuple returned by get_components_tuple
        for entity, (stats,) in world.get_components_tuple(YukkuriStats):
            # Decay stats
            stats.hunger += 2.0 * dt
            stats.happiness -= 0.5 * dt
            stats.energy -= 0.5 * dt
            stats.age += dt
            stats.cleanliness -= 0.2 * dt

            # Clamp
            stats.hunger = min(100, max(0, stats.hunger))
            stats.happiness = min(100, max(0, stats.happiness))
            stats.energy = min(100, max(0, stats.energy))
