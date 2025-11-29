"""
Module defining the StatDecaySystem logic.
"""
from typing import Optional
from ...engine.ecs import System, World
from ..yukkuri_components import YukkuriStats, Dead, Personality
from ..trait_service import TraitService
from ...config import StatDecaySettings

class StatDecaySystem(System):
    """
    System responsible for decaying Yukkuri physical stats over time.
    Emotional stats are handled by EmotionSystem.

    Attributes:
        settings (StatDecaySettings): The configuration settings for decay rates.
        trait_service (Optional[TraitService]): Service to access trait modifiers.
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
        if self.trait_service is None:
            self.trait_service = world.services.try_get(TraitService)

        # Iterate over entities with YukkuriStats
        for entity, (stats,) in world.get_components_tuple(YukkuriStats):
            if world.has_component(entity, Dead):
                continue

            # Default multipliers
            mult_hunger = 1.0
            mult_energy = 1.0
            mult_social = 1.0
            mult_cleanliness = 1.0

            # Apply Trait Modifiers
            if self.trait_service:
                personality = world.get_component(entity, Personality)
                if personality:
                    for trait_id in personality.traits:
                        trait_data = self.trait_service.get_trait(trait_id)
                        if trait_data and "stat_modifiers" in trait_data:
                            mods = trait_data["stat_modifiers"]
                            mult_hunger *= mods.get("hunger_decay", 1.0)
                            mult_energy *= mods.get("energy_decay", 1.0)
                            mult_social *= mods.get("social_decay", 1.0)
                            mult_cleanliness *= mods.get("cleanliness_decay", 1.0)

            # Decay stats
            stats.hunger += self.settings.hunger * mult_hunger * dt
            stats.energy -= self.settings.energy * mult_energy * dt
            stats.age += self.settings.age * dt
            stats.cleanliness -= self.settings.cleanliness * mult_cleanliness * dt

            if hasattr(self.settings, 'social'):
                 stats.social -= self.settings.social * mult_social * dt
            else:
                 stats.social -= 1.0 * mult_social * dt

            # Health decay due to starvation
            if stats.hunger >= 100.0:
                stats.health -= self.settings.starvation_damage * dt

            # Clamp
            stats.hunger = min(100, max(0, stats.hunger))
            stats.energy = min(100, max(0, stats.energy))
            stats.cleanliness = min(100, max(0, stats.cleanliness))
            stats.social = min(100, max(0, stats.social))
            stats.health = min(stats.max_health, max(0, stats.health))
