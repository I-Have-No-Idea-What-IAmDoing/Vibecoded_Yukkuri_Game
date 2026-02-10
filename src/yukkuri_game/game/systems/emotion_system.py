"""
Emotion System - Stat Decay and Emotional State Management.

Manages the decay of Yukkuri stats over time and updates emotional states.
Core to the simulation's need-driven AI behavior.

Stat Decay:
-   Physical stats (hunger, energy, cleanliness, social) decay over game time.
-   Decay rates modifiable by traits.
-   Starvation (hunger >= 100) causes health damage.

Emotional Model (2D Stress-Happiness Graph):
-   Happiness: -100 (sad) to +100 (happy), decays toward neutral (0).
-   Stress: 0 (calm) to 100 (stressed), decays over time.

Quadrant-based mood derivation:
-   Happy + Low Stress = Content/Relaxed.
-   Happy + High Stress = Excited/Manic.
-   Unhappy + High Stress = Rage (if brave) or Fear.
-   Unhappy + Low Stress = Depression.

Environmental Effects:
-   Night without light source = stress increase (DARKNESS_STRESS_RATE).
-   Proximity to light negates darkness stress.

Personality Drift:
-   Current personality axis values drift toward base values over time.
-   Simulates "returning to normal" after events that shifted personality.
"""

from ...config import StatDecaySettings
from ...engine import rng
from ...engine.ecs import System, World
from ..components import LightSource, Transform
from ..services import TimeService
from ..skill_service import SkillService
from ..trait_service import TraitService
from ..yukkuri_components import (
    Dead,
    EmotionalState,
    Needs,
    Personality,
    Skills,
    YukkuriStats,
)

SECONDS_PER_DAY = TimeService.GAME_DAY_LENGTH


class EmotionSystem(System):
    """
    Decays Yukkuri stats and manages emotional state over time.

    Responsibilities:
    -   Apply decay rates to physical stats (hunger, energy, etc.).
    -   Update happiness/stress based on environment and events.
    -   Apply personality drift toward baseline values.
    -   Trigger daily skill decay.

    Attributes:
        settings (StatDecaySettings): Stat decay configuration.
        trait_service (TraitService | None): Trait service.
        last_day_index (int): Index of the last day for skill decay tracking.
    """

    # Stress gained per second in darkness without light
    DARKNESS_STRESS_RATE: float = 5.0

    # Optimization: Update at 10 Hz (every 100ms)
    UPDATE_INTERVAL: float = 0.1
    MAX_UPDATES_PER_FRAME: int = 20

    def __init__(self, settings: StatDecaySettings):
        """
        Initializes the EmotionSystem.

        Args:
            settings (StatDecaySettings): Stat decay configuration (rates for hunger, energy, etc.).
        """
        self.settings = settings
        self.trait_service: TraitService | None = None
        self.last_day_index = -1

        # Optimization: Accumulator for throttling updates
        self.accumulated_dt = 0.0

    def update(self, world: World, dt: float) -> None:
        """
        Decays stats and emotional state for all entities with YukkuriStats.
        Uses a fixed-step loop to ensure simulation consistency.

        Args:
            world (World): The ECS World.
            dt (float): Delta time (physics time).
        """
        # Throttle updates to improve performance
        self.accumulated_dt += dt

        updates_count = 0
        while self.accumulated_dt >= self.UPDATE_INTERVAL:
            self._run_throttled_update(world, self.UPDATE_INTERVAL)
            self.accumulated_dt -= self.UPDATE_INTERVAL

            # Prevent spiral of death
            updates_count += 1
            if updates_count >= self.MAX_UPDATES_PER_FRAME:
                break

    def _run_throttled_update(self, world: World, dt: float) -> None:
        """
        Internal method containing the core update logic.

        Args:
            world (World): The ECS World.
            dt (float): Fixed delta time step.
        """
        # Lazy initialization
        if self.trait_service is None:
            self.trait_service = world.services.try_get(TraitService)

        time_service = world.services.try_get(TimeService)
        skill_service = world.services.try_get(SkillService)

        # Game time calculations
        game_dt = dt
        is_night = False
        if time_service:
            game_dt = dt * time_service.game_delta_multiplier
            is_night = time_service.is_night

        # Handle skill decay (once per game day)
        if time_service and skill_service:
            self._handle_skill_decay(world, time_service, skill_service)

        # Pre-calculate active light sources for night stress
        light_sources = []
        if is_night:
            light_sources = self._get_active_lights(world)

        # Process entities
        for entity, (stats, needs) in world.get_components_tuple(YukkuriStats, Needs):
            if world.has_component(entity, Dead):
                continue

            self._process_entity_decay(
                world, entity, stats, needs, game_dt, dt, is_night, light_sources
            )

    def _get_active_lights(self, world: World) -> list[tuple[Transform, LightSource]]:
        """
        Returns a list of active light sources.

        Args:
            world (World): The ECS World.

        Returns:
            list[tuple[Transform, LightSource]]: List of active light source components and their transforms.
        """
        lights = []
        for ent, (trans, light) in world.get_components_tuple(Transform, LightSource):
            if light.intensity > 0.0:
                lights.append((trans, light))
        return lights

    def _handle_skill_decay(
        self, world: World, time_service: TimeService, skill_service: SkillService
    ) -> None:
        """
        Checks if a day has passed and triggers skill decay.

        Args:
            world (World): The ECS World.
            time_service (TimeService): The time service.
            skill_service (SkillService): The skill service.
        """
        current_day_index = int(time_service.time_elapsed / SECONDS_PER_DAY)

        if self.last_day_index == -1:
            self.last_day_index = current_day_index
        elif current_day_index > self.last_day_index:
            days_passed = current_day_index - self.last_day_index
            for entity, (skills,) in world.get_components_tuple(Skills):
                for _ in range(days_passed):
                    skill_service.apply_decay(entity)
            self.last_day_index = current_day_index

    def _process_entity_decay(
        self,
        world: World,
        entity: int,
        stats: YukkuriStats,
        needs: Needs,
        game_dt: float,
        dt: float,
        is_night: bool,
        light_sources: list[tuple[Transform, LightSource]],
    ) -> None:
        """
        Applies decay for a single entity.

        Args:
            world (World): The ECS World.
            entity (int): The entity ID.
            stats (YukkuriStats): The stats component.
            needs (Needs): The needs component.
            game_dt (float): The game delta time.
            dt (float): The physics delta time.
            is_night (bool): Whether it is currently night.
            light_sources (list[tuple[Transform, LightSource]]): List of active light sources.
        """
        emotional_state = world.get_component(entity, EmotionalState)
        personality = world.get_component(entity, Personality)
        trans = world.get_component(entity, Transform)

        # 1. Determine multipliers
        multipliers = self._calculate_multipliers(personality)

        # 2. Decay physical stats
        needs.hunger += self.settings.hunger * multipliers["hunger"] * game_dt
        needs.energy -= self.settings.energy * multipliers["energy"] * game_dt
        stats.age += self.settings.age * game_dt
        needs.cleanliness -= (
            self.settings.cleanliness * multipliers["cleanliness"] * game_dt
        )

        if hasattr(self.settings, "social"):
            needs.social -= self.settings.social * multipliers["social"] * game_dt
        else:
            needs.social -= 1.0 * multipliers["social"] * game_dt

        # Starvation
        if needs.hunger >= 100.0:
            needs.health -= self.settings.starvation_damage * game_dt

        # Clamp physical
        needs.hunger = min(100, max(0, needs.hunger))
        needs.energy = min(100, max(0, needs.energy))
        needs.cleanliness = min(100, max(0, needs.cleanliness))
        needs.social = min(100, max(0, needs.social))
        needs.health = min(needs.max_health, max(0, needs.health))

        # Stabilize float drift for deterministic assertions
        needs.hunger = round(needs.hunger, 6)
        needs.energy = round(needs.energy, 6)
        needs.cleanliness = round(needs.cleanliness, 6)
        needs.social = round(needs.social, 6)
        needs.health = round(needs.health, 6)

        # 3. Update Emotional State
        if emotional_state:
            self._update_emotional_state(
                emotional_state,
                trans,
                dt,
                game_dt,
                is_night,
                light_sources,
                multipliers,
            )

        # 4. Personality Drift
        if personality and personality.base_axis:
            self._drift_personality(personality, dt)

    def _calculate_multipliers(
        self, personality: Personality | None
    ) -> dict[str, float]:
        """
        Calculates decay multipliers based on traits.

        Args:
            personality (Personality | None): The personality component.

        Returns:
            dict[str, float]: Multipliers for various stats.
        """
        mults = {
            "hunger": 1.0,
            "energy": 1.0,
            "social": 1.0,
            "cleanliness": 1.0,
            "stress": 1.0,
            "happiness": 1.0,
        }

        if self.trait_service and personality:
            for trait_id in personality.traits:
                trait_data = self.trait_service.get_trait(trait_id)
                if trait_data and trait_data.stat_modifiers:
                    mods = trait_data.stat_modifiers
                    mults["hunger"] *= mods.get("hunger_decay", 1.0)
                    mults["energy"] *= mods.get("energy_decay", 1.0)
                    mults["social"] *= mods.get("social_decay", 1.0)
                    mults["cleanliness"] *= mods.get("cleanliness_decay", 1.0)
                    mults["happiness"] *= mods.get("happiness_decay", 1.0)
                    mults["stress"] *= mods.get("stress_decay", 1.0)
        return mults

    def _update_emotional_state(
        self,
        emotional_state: EmotionalState,
        trans: Transform | None,
        dt: float,
        game_dt: float,
        is_night: bool,
        light_sources: list[tuple[Transform, LightSource]],
        multipliers: dict[str, float],
    ) -> None:
        """
        Updates stress and happiness.

        Args:
            emotional_state (EmotionalState): The emotional state component.
            trans (Transform | None): The transform component.
            dt (float): The physics delta time.
            game_dt (float): The game delta time.
            is_night (bool): Whether it is currently night.
            light_sources (list[tuple[Transform, LightSource]]): List of active light sources.
            multipliers (dict[str, float]): Decay multipliers.
        """
        # Darkness Stress
        if is_night and trans:
            in_light = False
            for l_trans, l_src in light_sources:
                dist_sq = (trans.x - l_trans.x) ** 2 + (trans.y - l_trans.y) ** 2
                if dist_sq < l_src.radius**2:
                    in_light = True
                    break

            if not in_light:
                emotional_state.stress += self.DARKNESS_STRESS_RATE * game_dt

        # Stress Decay
        stress_decay_rate = getattr(self.settings, "stress", 5.0)
        if emotional_state.stress > 0:
            emotional_state.stress -= (
                stress_decay_rate * multipliers["stress"] * game_dt
            )
            emotional_state.stress = max(0.0, emotional_state.stress)

        # Happiness Decay (Return to Neutral)
        happiness_decay_rate = self.settings.happiness
        baseline = 0.0

        if emotional_state.happiness > baseline:
            emotional_state.happiness -= (
                happiness_decay_rate * multipliers["happiness"] * game_dt
            )
            emotional_state.happiness = max(baseline, emotional_state.happiness)
        elif emotional_state.happiness < baseline:
            emotional_state.happiness += (
                happiness_decay_rate * multipliers["happiness"] * game_dt
            )
            emotional_state.happiness = min(baseline, emotional_state.happiness)

        # Clamp
        emotional_state.happiness = max(-100.0, min(100.0, emotional_state.happiness))
        emotional_state.stress = max(0.0, min(100.0, emotional_state.stress))

    def _drift_personality(self, personality: Personality, dt: float) -> None:
        """
        Drifts the current personality axis towards the base axis (resting point).

        Args:
            personality (Personality): The personality component.
            dt (float): Delta time.
        """
        drift_rate = getattr(self.settings, "personality_drift_rate", 0.1)

        # Fractional drift via probability.
        drift_amount_float = drift_rate * dt
        guaranteed_drift = int(drift_amount_float)
        probability_drift = drift_amount_float - guaranteed_drift

        for attr in ["kindness", "energy", "bravery", "greed"]:
            current = getattr(personality.axis, attr)
            base = getattr(personality.base_axis, attr)

            if current == base:
                continue

            diff = base - current
            direction = 1 if diff > 0 else -1

            # Apply guaranteed drift
            change = guaranteed_drift

            # Apply probabilistic drift
            if rng.random_float() < probability_drift:
                change += 1

            if change > 0:
                new_val = current + (change * direction)

                # Don't overshoot
                if direction > 0:
                    new_val = min(new_val, base)
                else:
                    new_val = max(new_val, base)

                setattr(personality.axis, attr, new_val)
