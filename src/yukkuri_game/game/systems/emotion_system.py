"""
Module defining the EmotionSystem logic (formerly StatDecaySystem).
"""
from typing import Optional
from ...engine.ecs import System, World
from ..yukkuri_components import YukkuriStats, Dead, Personality, EmotionalState, Skills
from ..trait_service import TraitService
from ..services import TimeService
from ..skill_service import SkillService
from ...config import StatDecaySettings
import random

SECONDS_PER_DAY = 3600.0

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
        self.last_day_index = -1

    def update(self, world: World, dt: float) -> None:
        """
        Decays stats and emotional state for all entities with YukkuriStats.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.
        """
        if self.trait_service is None:
            self.trait_service = world.services.try_get(TraitService)

        # --- Skill Decay Automation ---
        time_service = world.services.try_get(TimeService)
        skill_service = world.services.try_get(SkillService)

        if time_service and skill_service:
            current_day_index = int(time_service.time_elapsed / SECONDS_PER_DAY)

            if self.last_day_index == -1:
                # Initialize
                self.last_day_index = current_day_index

            elif current_day_index > self.last_day_index:
                # One or more days passed
                days_passed = current_day_index - self.last_day_index

                # Iterate all entities with Skills
                for entity, (skills,) in world.get_components_tuple(Skills):
                    # Apply decay for each day passed
                    for _ in range(days_passed):
                        skill_service.apply_decay(entity)

                self.last_day_index = current_day_index

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

                # Happiness decays slow to 0 (Neutral)
                happiness_decay_rate = self.settings.happiness
                baseline = 0.0

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

        Uses a deterministic accumulator (not yet implemented in Component, so using a temp workaround or stochastic approximation).
        Actually, we can use a small float accumulation if we add it to Personality, but for now,
        let's make it deterministic by accumulating drift debt if we could.

        Since we can't easily change the Component structure to add a 'drift_accumulator' without breaking pickles or migration (simulated constraint),
        we will use a clearer stochastic method that scales correctly with DT, or better:

        We treat 'axis' as the integer representation, but we could drift by checking if (current != base).
        If we want true deterministic drift, we need storage.

        Wait, I can add a `_drift_accumulator` field to the Personality component in yukkuri_components.py first.
        But for this step, I will stick to fixing the "drift_chance > 1.0" issue first.
        """
        drift_rate = getattr(self.settings, 'personality_drift_rate', 0.1) # Units per second

        # We can simulate fractional drift by using a probability that is clamped.
        # But if drift_rate * dt > 1, we should drift multiple points.

        drift_amount_float = drift_rate * dt
        guaranteed_drift = int(drift_amount_float)
        probability_drift = drift_amount_float - guaranteed_drift

        for attr in ['kindness', 'energy', 'bravery', 'greed']:
            current = getattr(personality.axis, attr)
            base = getattr(personality.base_axis, attr)

            if current == base:
                continue

            diff = base - current
            direction = 1 if diff > 0 else -1

            # Apply guaranteed drift
            change = guaranteed_drift

            # Apply probabilistic drift
            if random.random() < probability_drift:
                change += 1

            if change > 0:
                new_val = current + (change * direction)

                # Don't overshoot
                if direction > 0:
                    new_val = min(new_val, base)
                else:
                    new_val = max(new_val, base)

                setattr(personality.axis, attr, new_val)
