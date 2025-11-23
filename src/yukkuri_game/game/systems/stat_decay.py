from typing import Optional
from ...engine.ecs import System, World
from ..yukkuri_components import YukkuriStats, Dead, Personality
from ...config import StatDecaySettings
from ..trait_service import TraitService

class StatDecaySystem(System):
    """
    System responsible for decaying Yukkuri stats over time.

    Attributes:
        settings (StatDecaySettings): The configuration settings for decay rates.
        trait_service (Optional[TraitService]): Service to access trait data.
    """

    def __init__(self, settings: StatDecaySettings):
        """
        Initializes the StatDecaySystem.

        Args:
            settings (StatDecaySettings): Stat decay settings configuration.
        """
        self.settings = settings
        self.trait_service: Optional[TraitService] = None

    def update(self, world: World, dt: float) -> None:
        """
        Decays stats for all entities with YukkuriStats component.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.

        Returns:
            None
        """
        if not self.trait_service:
            self.trait_service = world.services.try_get(TraitService)

        # Iterate over entities with YukkuriStats
        # Note: unpack the tuple returned by get_components_tuple
        for entity, (stats,) in world.get_components_tuple(YukkuriStats):
            if world.has_component(entity, Dead):
                continue

            # Base modifiers
            hunger_mod = 1.0
            happiness_mod = 1.0
            energy_mod = 1.0
            social_mod = 1.0

            # Check personality for modifiers
            if self.trait_service and world.has_component(entity, Personality):
                personality = world.get_component(entity, Personality)
                for trait_id in personality.traits:
                    trait_data = self.trait_service.get_trait(trait_id)
                    if trait_data and "stat_modifiers" in trait_data:
                        mods = trait_data["stat_modifiers"]
                        hunger_mod *= mods.get("hunger_decay", 1.0)
                        happiness_mod *= mods.get("happiness_decay", 1.0)
                        energy_mod *= mods.get("energy_decay", 1.0)
                        social_mod *= mods.get("social_decay", 1.0)

            # Decay stats
            stats.hunger += self.settings.hunger * hunger_mod * dt
            stats.happiness -= self.settings.happiness * happiness_mod * dt
            stats.energy -= self.settings.energy * energy_mod * dt
            stats.age += self.settings.age * dt
            stats.cleanliness -= self.settings.cleanliness * dt

            # Social decay (if implemented in stats)
            # stats.social -= self.settings.social * social_mod * dt # if social decay exists in settings

            # Health decay due to starvation
            if stats.hunger >= 100.0:
                stats.health -= self.settings.starvation_damage * dt

            # Clamp
            stats.hunger = min(100, max(0, stats.hunger))
            stats.happiness = min(100, max(0, stats.happiness))
            stats.energy = min(100, max(0, stats.energy))
            stats.cleanliness = min(100, max(0, stats.cleanliness))
