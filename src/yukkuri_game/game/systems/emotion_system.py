"""
Module implementing the EmotionSystem for handling Yukkuri emotional states and moods.
"""
import math
from typing import Optional
from ...engine.ecs import System, World
from ..yukkuri_components import EmotionalState, Personality, Dead, YukkuriStats
from ..trait_service import TraitService
from ...config import StatDecaySettings

class EmotionSystem(System):
    """
    System responsible for updating EmotionalState (Happiness, Stress) and deriving Moods.

    Design Doc Section 3: Emotional State: The 2D Stress-Happiness Graph
    - Happiness (-100 to 100)
    - Stress (0 to 100)
    - Derived Moods (Quadrants)
    """

    def __init__(self, decay_settings: Optional[StatDecaySettings] = None):
        super().__init__()
        # If no settings provided, use defaults (or injected later)
        self.decay_settings = decay_settings
        self.trait_service: Optional[TraitService] = None

    def update(self, world: World, dt: float) -> None:
        if self.trait_service is None:
            self.trait_service = world.services.try_get(TraitService)

        # Iterate over entities with EmotionalState
        for entity, (emo, pers) in world.get_components_tuple(EmotionalState, Personality):
            if world.has_component(entity, Dead):
                continue

            self._update_emotional_state(emo, pers, dt)
            self._derive_mood(emo, pers)

            # Sync to YukkuriStats (deprecated fields)
            # This ensures other systems using stats.happiness/stress still work
            stats = world.get_component(entity, YukkuriStats)
            if stats:
                stats.happiness = emo.happiness
                stats.stress = emo.stress

    def _update_emotional_state(self, emo: EmotionalState, pers: Personality, dt: float) -> None:
        """
        Decays Happiness and Stress towards baseline (usually 0).
        """
        baseline_happiness = 0.0
        baseline_stress = 0.0

        # Apply Trait-based Baseline Shifts (Center Shift logic for Emotions)
        # While design doc emphasizes Personality Center Shift, traits can also shift emotional baseline.
        if self.trait_service:
            for trait_id in pers.traits:
                # We look for explicit baseline modifiers or infer from existing structure
                # For now, we use a heuristic based on trait names or simple hardcoded logic if data is missing.
                # Ideally, traits.toml would have [traits.ID.emotional_modifiers] baseline_happiness = 20.0

                trait_data = self.trait_service.get_trait(trait_id)
                if trait_data:
                    # Check for custom 'emotional_modifiers' block if we added it (we haven't yet in TOML)
                    # Or reuse 'stat_modifiers' if suitable.
                    # As a fallback/implementation of the "Center Shift" concept:
                    if trait_id == "NICE":
                        baseline_happiness += 10.0 # Nice yukkuris are naturally happier?
                    elif trait_id == "GESU":
                        baseline_happiness -= 10.0 # Gesu are naturally grumpy?

                    # Future: Load from TOML
                    # mods = trait_data.get("emotional_modifiers", {})
                    # baseline_happiness += mods.get("baseline_happiness", 0.0)

        # Decay Rates
        decay_rate_happiness = 2.0
        decay_rate_stress = 5.0

        # Apply Decay Modifiers from Traits
        if self.trait_service:
            for trait_id in pers.traits:
                trait_data = self.trait_service.get_trait(trait_id)
                if trait_data and "stat_modifiers" in trait_data:
                    mods = trait_data["stat_modifiers"]
                    decay_rate_happiness *= mods.get("happiness_decay", 1.0)
                    # decay_rate_stress *= mods.get("stress_decay", 1.0) # If exists

        # Decay Happiness towards baseline
        if emo.happiness > baseline_happiness:
            emo.happiness = max(baseline_happiness, emo.happiness - decay_rate_happiness * dt)
        elif emo.happiness < baseline_happiness:
            emo.happiness = min(baseline_happiness, emo.happiness + decay_rate_happiness * dt)

        # Decay Stress towards baseline
        if emo.stress > baseline_stress:
            emo.stress = max(baseline_stress, emo.stress - decay_rate_stress * dt)

        # Clamp
        emo.happiness = max(-100, min(100, emo.happiness))
        emo.stress = max(0, min(100, emo.stress))

    def _derive_mood(self, emo: EmotionalState, pers: Personality) -> None:
        """
        Derives the current mood based on Happiness/Stress quadrants.
        """

        # Thresholds
        HIGH_HAPPINESS = 20.0
        LOW_HAPPINESS = -20.0
        HIGH_STRESS = 50.0

        mood = "Neutral"

        if emo.happiness > HIGH_HAPPINESS:
            if emo.stress < HIGH_STRESS:
                mood = "Relaxed" # Content/Relaxed
            else:
                mood = "Excited" # Excited/Manic
        elif emo.happiness < LOW_HAPPINESS:
            if emo.stress < HIGH_STRESS:
                mood = "Depressed" # Depressed/Sulking
            else:
                # Terror vs Rage depends on Bravery
                if pers.bravery > 0:
                    mood = "Rage"
                else:
                    mood = "Terror"
        else:
            # Middle Happiness
            if emo.stress > HIGH_STRESS:
                mood = "Stressed"
            else:
                mood = "Neutral"

        emo.current_mood = mood
