"""
Module defining the EmotionSystem logic (formerly StatDecaySystem).
"""
from typing import Optional
from ...engine.ecs import System, World
from ..yukkuri_components import YukkuriStats, Dead, Personality, EmotionalState
from ..trait_service import TraitService
from ...config import StatDecaySettings
import random

class EmotionSystem(System):
    """
    System responsible for decaying Yukkuri stats and updating Emotional State over time.

    Attributes:
        settings (StatDecaySettings): The configuration settings for decay rates.
        trait_service (Optional[TraitService]): Service to access trait modifiers.
    """

    def __init__(self, settings: StatDecaySettings):
        """
        Initializes the EmotionSystem.

        Args:
            settings (StatDecaySettings): Stat decay settings configuration.
        """
        self.settings = settings
        self.trait_service: Optional[TraitService] = None

    def update(self, world: World, dt: float) -> None:
        """
        Decays stats and emotional state for all entities with YukkuriStats.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.
        """
        if self.trait_service is None:
            self.trait_service = world.services.try_get(TraitService)

        # Iterate over entities with YukkuriStats
        for entity, (stats,) in world.get_components_tuple(YukkuriStats):
            if world.has_component(entity, Dead):
                continue

            # Get EmotionalState if present
            emotional_state = world.get_component(entity, EmotionalState)
            personality = world.get_component(entity, Personality)

            # Default multipliers
            mult_hunger = 1.0
            mult_energy = 1.0
            mult_social = 1.0
            mult_cleanliness = 1.0

            # Emotional decay multipliers
            mult_stress = 1.0
            mult_happiness = 1.0

            # Apply Trait Modifiers
            if self.trait_service and personality:
                for trait_id in personality.traits:
                    trait_data = self.trait_service.get_trait(trait_id)
                    if trait_data and "stat_modifiers" in trait_data:
                        mods = trait_data["stat_modifiers"]
                        mult_hunger *= mods.get("hunger_decay", 1.0)
                        mult_energy *= mods.get("energy_decay", 1.0)
                        mult_social *= mods.get("social_decay", 1.0)
                        mult_cleanliness *= mods.get("cleanliness_decay", 1.0)

                        # Assuming traits.toml will be updated to use "stress_decay" etc.
                        mult_happiness *= mods.get("happiness_decay", 1.0)
                        mult_stress *= mods.get("stress_decay", 1.0)

            # Decay physical stats
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

            # Clamp physical stats
            stats.hunger = min(100, max(0, stats.hunger))
            stats.energy = min(100, max(0, stats.energy))
            stats.cleanliness = min(100, max(0, stats.cleanliness))
            stats.social = min(100, max(0, stats.social))
            stats.health = min(stats.max_health, max(0, stats.health))

            # Update Emotional State
            if emotional_state:
                # Stress decays fast to 0
                stress_decay_rate = getattr(self.settings, 'stress', 5.0)
                if emotional_state.stress > 0:
                    emotional_state.stress -= stress_decay_rate * mult_stress * dt
                    emotional_state.stress = max(0.0, emotional_state.stress)

                # Happiness decays slow to 50
                happiness_decay_rate = self.settings.happiness
                baseline = 50.0

                if emotional_state.happiness > baseline:
                    emotional_state.happiness -= happiness_decay_rate * mult_happiness * dt
                    emotional_state.happiness = max(baseline, emotional_state.happiness)
                elif emotional_state.happiness < baseline:
                    emotional_state.happiness += happiness_decay_rate * mult_happiness * dt
                    emotional_state.happiness = min(baseline, emotional_state.happiness)

                # Clamp
                emotional_state.happiness = max(-100.0, min(100.0, emotional_state.happiness))
                emotional_state.stress = max(0.0, min(100.0, emotional_state.stress))

            # Personality Drift
            if personality and personality.base_axis:
                self._drift_personality(personality, dt)

    def _drift_personality(self, personality: Personality, dt: float) -> None:
        """
        Drifts the current personality axis towards the base axis (resting point).
        Rate: Configured in rules file.
        """
        # Points per second probability
        drift_rate = getattr(self.settings, 'personality_drift_rate', 0.1)
        drift_chance = drift_rate * dt

        # Iterate over attributes
        for attr in ['kindness', 'energy', 'bravery', 'greed']:
            current = getattr(personality.axis, attr)
            base = getattr(personality.base_axis, attr)

            if current == base:
                continue

            if random.random() < drift_chance:
                if current < base:
                    setattr(personality.axis, attr, current + 1)
                else:
                    setattr(personality.axis, attr, current - 1)
