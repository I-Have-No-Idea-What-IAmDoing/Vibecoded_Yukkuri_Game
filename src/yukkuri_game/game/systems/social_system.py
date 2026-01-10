"""
Module implementing the social system for Yukkuri interaction and relationship management.
"""

import time
from typing import Any
from loguru import logger
import random

from ...engine.ecs import System, World
from ...engine.event_bus import EventBus
from ...engine.audio import AudioManager
from ..utils.evaluator import ConditionEvaluator
from ..components import Transform, InteractionRequest
from ..yukkuri_components import (
    YukkuriStats,
    Needs,
    RelationshipRegistry,
    RelationshipData,
    MemoryHeadline,
    Personality,
    EmotionalState,
    Skills,
)
from ..trait_service import TraitService
from ..skill_service import SkillService
from ..services import TimeService
from ..events import SocialInteractionEvent
from ..prefabs.effects import create_floating_text


class SocialSystem(System):
    """
    System responsible for managing social relationships, memory decay, and applying interaction effects.
    Implements "Headline System" for memory and Opinion Calculation.

    Attributes:
        trait_service (Optional[TraitService]): The trait service.
        skill_service (Optional[SkillService]): The skill service.
        cleanup_index (int): Index for partial update loop.
        cleanup_batch_size (int): Number of entities to process per frame.
        event_bus (EventBus): The event bus.
        headline_counter (int): Counter for unique memory IDs.
    """

    def __init__(self, event_bus: EventBus):
        """
        Initializes the SocialSystem.

        Args:
            event_bus (EventBus): The event bus instance.
        """
        super().__init__()
        self.trait_service: TraitService | None = None
        self.skill_service: SkillService | None = None
        self.audio: AudioManager | None = None
        self.cleanup_index = 0
        self.cleanup_batch_size = 10
        self.event_bus = event_bus
        self.headline_counter = 0

    def update(self, world: World, dt: float) -> None:
        """
        Updates the social system (memory decay, relationship cleanup).

        Args:
            world (World): The ECS World.
            dt (float): Delta time.
        """
        if not self.trait_service:
            self.trait_service = world.services.try_get(TraitService)
        if not self.skill_service:
            self.skill_service = world.services.try_get(SkillService)
        if not self.audio:
            self.audio = world.services.try_get(AudioManager)

        time_service = world.services.try_get(TimeService)
        now = time_service.time_elapsed if time_service else time.time()

        self._process_relationships(world, now)

    def _process_relationships(self, world: World, now: float) -> None:
        """
        Processes relationship updates and cleanup in batches.
        """
        all_entities = world.get_entities_with(RelationshipRegistry)
        if not all_entities:
            return

        count = len(all_entities)
        start = self.cleanup_index % count
        end = min(start + self.cleanup_batch_size, count)

        for i in range(start, end):
            eid = all_entities[i]
            registry = world.get_component(eid, RelationshipRegistry)
            if registry:
                self._cleanup_registry(world, eid, registry, now)

        # Update the index for the next frame.
        # This ensures we cycle through all entities over time without stalling the frame.
        self.cleanup_index = (self.cleanup_index + self.cleanup_batch_size) % max(
            1, count
        )

    def _cleanup_registry(
        self, world: World, eid: int, registry: RelationshipRegistry, now: float
    ) -> None:
        """
        Cleans up old relationships and updates opinions.
        """
        to_remove = []
        max_age = 600  # 10 minutes

        for other_id, rel_data in registry.relationships.items():
            self._update_opinion(world, eid, other_id, rel_data)

            other_registry = world.get_component(other_id, RelationshipRegistry)
            is_special = (other_id == registry.mate_id) or (
                registry.family_group_id is not None
                and other_registry is not None
                and other_registry.family_group_id == registry.family_group_id
            )

            age = now - rel_data.last_update
            if not is_special and age > max_age:
                to_remove.append(other_id)

        for rid in to_remove:
            del registry.relationships[rid]

    def process_interaction_request(
        self, world: World, initiator_id: int, request: InteractionRequest
    ) -> None:
        """
        Process a direct social interaction request from the behavior tree.
        """
        target_id = request.target_id
        action = request.action

        if not world.entity_exists(target_id):
            return

        self.register_interaction(world, initiator_id, target_id, action)
        self.event_bus.publish(SocialInteractionEvent(initiator_id, target_id, action))

    def _update_opinion(
        self,
        world: World,
        subject_id: int,
        other_id: int,
        rel_data: RelationshipData,
        force_compatibility_update: bool = False,
    ) -> None:
        """
        Recalculates the opinion (affinity).
        """
        if not self.trait_service:
            return

        subject_pers = world.get_component(subject_id, Personality)
        other_pers = world.get_component(other_id, Personality)

        if subject_pers and other_pers:
            rel_data.base_compatibility = self._calculate_base_compatibility(
                subject_pers, other_pers
            )

        memory_score = rel_data.core_sentiment_sum + rel_data.trivial_sentiment_sum
        rel_data.affinity = rel_data.base_compatibility + memory_score

    def _calculate_base_compatibility(
        self, subject_pers: Personality, other_pers: Personality
    ) -> float:
        """
        Calculates base compatibility between two personalities.
        """
        base_compatibility = 0.0

        if subject_pers.axis and other_pers.axis:
            diff_kind = abs(subject_pers.axis.kindness - other_pers.axis.kindness)
            diff_ener = abs(subject_pers.axis.energy - other_pers.axis.energy)
            diff_brav = abs(subject_pers.axis.bravery - other_pers.axis.bravery)
            diff_gree = abs(subject_pers.axis.greed - other_pers.axis.greed)

            total_diff = diff_kind + diff_ener + diff_brav + diff_gree
            total_diff = diff_kind + diff_ener + diff_brav + diff_gree
            # Base compatibility starts at 100 and subtracts the average difference on 4 axes.
            # If personalities are identical, compatibility is 100.
            # If completely opposite, it drops significantly.
            base_compatibility += 100.0 - (total_diff / 4.0)

        if self.trait_service:
            for my_trait in subject_pers.traits:
                trait_data = self.trait_service.get_trait(my_trait)
                if not trait_data:
                    continue

                if isinstance(trait_data, dict):
                    social_mods = trait_data.get("social_modifiers", {})
                else:
                    social_mods = getattr(trait_data, "social_modifiers", {})

                if "compatibility" not in social_mods:
                    continue

                comp_map = social_mods["compatibility"]
                for other_trait in other_pers.traits:
                    if other_trait in comp_map:
                        base_compatibility += comp_map[other_trait]

        return base_compatibility

    def on_social_interaction(self, event: SocialInteractionEvent) -> None:
        """Handler for SocialInteractionEvent."""
        if not hasattr(self, "ecs_world"):
            return
        self.register_interaction(
            self.ecs_world, event.initiator_id, event.target_id, event.interaction_type
        )

    def _check_condition(self, world: World, entity_id: int, condition: Any) -> bool:
        """Checks if a condition is met by the entity."""
        if isinstance(condition, str):
            evaluator = world.services.try_get(ConditionEvaluator)
            if evaluator:
                ctx = evaluator.build_context(world, entity_id)
                return evaluator.evaluate(condition, ctx)
            return False

        if isinstance(condition, dict):
            if "expression" in condition:
                evaluator = world.services.try_get(ConditionEvaluator)
                if evaluator:
                    ctx = evaluator.build_context(world, entity_id)
                    return evaluator.evaluate(condition["expression"], ctx)
                return False

            cond_type = condition.get("type")
            if cond_type == "skill_check":
                skill_id = condition.get("skill")
                min_level = condition.get("min_level", 0)
                skills = world.get_component(entity_id, Skills)
                if skills and skill_id in skills.states:
                    return skills.states[skill_id].level >= min_level
                return False

        return True

    def _get_attr(self, obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def register_interaction(
        self, world: World, actor_id: int, target_id: int, interaction_name: str
    ) -> None:
        """Registers a social interaction."""
        if not self.trait_service:
            self.trait_service = world.services.try_get(TraitService)
            if not self.trait_service:
                return

        if not self.skill_service:
            self.skill_service = world.services.try_get(SkillService)

        if not self.audio:
            self.audio = world.services.try_get(AudioManager)

        interaction_data = self.trait_service.get_interaction(interaction_name)
        if not interaction_data:
            logger.warning(f"Unknown interaction: {interaction_name}")
            return

        conditions = self._get_attr(interaction_data, "conditions", [])
        if conditions:
            for cond in conditions:
                if not self._check_condition(world, actor_id, cond):
                    return

        time_service = world.services.try_get(TimeService)
        now = time_service.time_elapsed if time_service else time.time()

        self._apply_impact(
            world, actor_id, target_id, interaction_data, role="actor", now=now
        )
        self._apply_impact(
            world, target_id, actor_id, interaction_data, role="target", now=now
        )
        self._spawn_visual_feedback(
            world, target_id, interaction_name, interaction_data
        )
        self._play_audio(interaction_name)

        self._apply_additional_effects(world, actor_id, target_id, interaction_data)

    def _apply_additional_effects(
        self, world: World, actor_id: int, target_id: int, interaction_data: Any
    ) -> None:
        """Applies physical impacts and skill rewards."""
        physical_impact = self._get_attr(interaction_data, "physical_impact", {})
        if physical_impact:
            self._apply_physical_impact(world, actor_id, physical_impact)
            self._apply_physical_impact(world, target_id, physical_impact)

        target_physical_impact = self._get_attr(
            interaction_data, "target_physical_impact", {}
        )
        if target_physical_impact:
            self._apply_physical_impact(world, target_id, target_physical_impact)

        actor_physical_impact = self._get_attr(
            interaction_data, "actor_physical_impact", {}
        )
        if actor_physical_impact:
            self._apply_physical_impact(world, actor_id, actor_physical_impact)

        skill_rewards = self._get_attr(interaction_data, "skill_rewards", {})
        if skill_rewards and self.skill_service:
            for skill_id, xp_amount in skill_rewards.items():
                self.skill_service.add_xp(actor_id, skill_id, xp_amount)

    def _apply_physical_impact(
        self, world: World, entity_id: int, impact: dict[str, float]
    ) -> None:
        """Helper to apply physical stat changes to an entity."""
        world.get_component(entity_id, YukkuriStats)
        needs = world.get_component(entity_id, Needs)
        emotional = world.get_component(entity_id, EmotionalState)

        if needs:
            if "health" in impact:
                needs.health = max(
                    0.0, min(needs.max_health, needs.health + impact["health"])
                )
            if "energy" in impact:
                needs.energy = max(0.0, min(100.0, needs.energy + impact["energy"]))
            if "hunger" in impact:
                needs.hunger = max(0.0, min(100.0, needs.hunger + impact["hunger"]))
            if "cleanliness" in impact:
                needs.cleanliness = max(
                    0.0, min(100.0, needs.cleanliness + impact["cleanliness"])
                )

        if emotional:
            if "happiness" in impact:
                emotional.happiness = max(
                    -100.0, min(100.0, emotional.happiness + impact["happiness"])
                )
            if "stress" in impact:
                emotional.stress = max(
                    0.0, min(100.0, emotional.stress + impact["stress"])
                )

    def _play_audio(self, interaction_name: str) -> None:
        """Plays audio for the interaction."""
        if not self.audio:
            return

        sound_name = ""
        if interaction_name in ["Talk", "Greet"]:
            sound_name = "talk"
        elif interaction_name in ["Fight", "Hit"]:
            sound_name = "hit"
        elif interaction_name == "Dance":
            sound_name = "jump"

        if sound_name:
            self.audio.play_sound(sound_name)

    def _spawn_visual_feedback(
        self, world: World, entity_id: int, interaction_name: str, data: Any
    ) -> None:
        """Spawns visual feedback (floating text/icon)."""
        trans = world.get_component(entity_id, Transform)
        if not trans:
            return

        text = "!"
        color = (255, 255, 255)
        base_impact = self._get_attr(data, "base_impact", 0.0)

        if interaction_name in ["Talk", "Greet"]:
            text = "♪"
            color = (100, 255, 100)
        elif interaction_name in ["Fight", "Hit"]:
            text = "💢"
            color = (255, 50, 50)
        elif interaction_name == "Dance":
            text = "♥"
            color = (255, 105, 180)
        elif interaction_name == "Feed":
            text = "Mogu"
            color = (255, 200, 50)

        if base_impact < -10:
            text = "T_T"
            color = (100, 100, 255)

        fx = trans.x + random.uniform(-10, 10)
        fy = trans.y - 30
        create_floating_text(world, fx, fy, text, color, size=24, lifetime=1.5)

    def _apply_impact(
        self,
        world: World,
        subject_id: int,
        other_id: int,
        data: Any,
        role: str,
        now: float,
    ) -> None:
        """Applies the social impact of an interaction to a subject."""
        registry = self._get_or_create_registry(world, subject_id)
        if other_id not in registry.relationships:
            registry.relationships[other_id] = RelationshipData(last_update=now)
        rel = registry.relationships[other_id]
        rel.last_update = now

        social_impact = self._get_attr(data, "social_impact", {})
        base_impact_score = self._get_attr(data, "base_impact", 0.0)
        modifiers = self._get_attr(data, "modifiers", {})
        event_type = self._get_attr(data, "type", "GENERIC")

        d_affinity, d_trust, d_fear, d_familiarity = self._calculate_impact_deltas(
            world, subject_id, other_id, social_impact, modifiers, base_impact_score
        )

        self._update_emotional_state(world, subject_id, base_impact_score)

        rel.trust = max(0, min(100, rel.trust + d_trust))
        rel.fear = max(0, min(100, rel.fear + d_fear))
        rel.familiarity = max(0, min(100, rel.familiarity + d_familiarity))

        self._add_memory_headline(
            world, rel, base_impact_score, d_affinity, event_type, now
        )
        self._update_opinion(world, subject_id, other_id, rel)

    def _get_or_create_registry(
        self, world: World, entity_id: int
    ) -> RelationshipRegistry:
        """Helper to get or create RelationshipRegistry component."""
        registry = world.get_component(entity_id, RelationshipRegistry)
        if not registry:
            registry = RelationshipRegistry()
            world.add_component(entity_id, registry)
        return registry

    def _calculate_impact_deltas(
        self,
        world: World,
        subject_id: int,
        other_id: int,
        social_impact: dict[str, float],
        modifiers: dict[str, dict[str, float]],
        base_impact_score: float,
    ) -> tuple[float, float, float, float]:
        """Calculates impact deltas considering personality and traits."""
        d_affinity = social_impact.get("affinity", 0.0)
        d_trust = social_impact.get("trust", 0.0)
        d_fear = social_impact.get("fear", 0.0)
        d_familiarity = social_impact.get("familiarity", 0.0)

        subject_personality = world.get_component(subject_id, Personality)
        if subject_personality:
            for trait in subject_personality.traits:
                key = f"trait:{trait}"
                if key in modifiers:
                    mod = modifiers[key]
                    d_affinity += mod.get("affinity", 0.0)
                    d_trust += mod.get("trust", 0.0)
                    d_fear += mod.get("fear", 0.0)

            evaluator = world.services.try_get(ConditionEvaluator)
            if evaluator:
                actor_context = evaluator.build_context(world, other_id)
                for key, mod in modifiers.items():
                    if key.startswith("trait:") or key.startswith("mood:"):
                        continue

                    if evaluator.evaluate(key, actor_context):
                        d_affinity += mod.get("affinity", 0.0)
                        d_trust += mod.get("trust", 0.0)
                        d_fear += mod.get("fear", 0.0)

            kindness = 0
            if subject_personality.axis:
                kindness = subject_personality.axis.kindness

            if base_impact_score > 0:
                comp_mult = max(0.1, 1.0 + (kindness / 100.0))
                d_affinity *= comp_mult
                d_trust *= comp_mult
            elif base_impact_score < 0:
                comp_mult = max(0.1, 1.0 - (kindness / 100.0))
                d_affinity *= comp_mult
                d_trust *= comp_mult
                d_fear *= comp_mult

        return d_affinity, d_trust, d_fear, d_familiarity

    def _update_emotional_state(
        self, world: World, subject_id: int, base_impact_score: float
    ) -> None:
        """Updates emotional state based on interaction impact."""
        emotional = world.get_component(subject_id, EmotionalState)
        if emotional:
            if base_impact_score < -15:
                emotional.happiness = max(-100.0, emotional.happiness - 20.0)
                emotional.stress = min(100.0, emotional.stress + 20.0)
            elif base_impact_score > 15:
                emotional.happiness = min(100.0, emotional.happiness + 20.0)

    def _add_memory_headline(
        self,
        world: World,
        rel: RelationshipData,
        base_impact_score: float,
        d_affinity: float,
        event_type: str,
        now: float,
    ) -> None:
        """Adds a memory headline to the relationship."""
        if abs(base_impact_score) > 0:
            self.headline_counter += 1
            headline = MemoryHeadline(
                id=self.headline_counter,
                timestamp=now,
                importance=abs(base_impact_score),
                sentiment=d_affinity,
                is_locked=False,
                text=event_type,
                event_type=event_type,
            )

            from ...config import GameConfig

            config = world.services.try_get(GameConfig)
            threshold = 50.0
            if config and hasattr(config.rules, "social"):
                threshold = config.rules.social.memory_importance_threshold

            rel.add_headline(headline, threshold=threshold)
