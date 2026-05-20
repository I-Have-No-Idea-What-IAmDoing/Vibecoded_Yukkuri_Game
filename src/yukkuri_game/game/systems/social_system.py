"""
Social System - Relationship and Interaction Management.

This system monitors social interactions and manages long-term relationships between entities.
It implements the "Headline System" for memory, where significant events ("headlines") that drive
affinity changes are stored and decay over time.

Relationships track:
-   Affinity: Relative liking (-100 to 100), derived from base compatibility and consolidated memories.
-   Trust: Reliability and safety perception (-100 to 100).
-   Fear: Threat perception (0 to 100).
-   Familiarity: Depth of knowledge about the other entity (0 to 100).

Key Features:
-   Memory Consolidation: Trivial memories decay rapidly; core memories persist based on importance.
-   Compatibility: Base affinity calculated from Personality traits and axes (Kindness, Energy, etc.).
-   Interaction Impacts: Modifies stats (Health, Happiness, Stress) and relationship values.
"""

from typing import TYPE_CHECKING, Any, cast

from loguru import logger

from ...engine import rng
from ...engine.audio import AudioManager
from ...engine.ecs import System, World
from ...engine.event_bus import EventBus
from ..components import InteractionRequest
from yukkuri_game.engine.components import Transform
from ..events import SocialInteractionEvent
from ..prefabs.effects import create_floating_text
from ..skill_service import SkillService
from ..trait_service import TraitService
from ..utils.evaluator import ConditionEvaluator
from ..components import (
    EmotionalState,
    MemoryHeadline,
    Needs,
    Personality,
    RelationshipData,
    RelationshipRegistry,
    Skills,
)

if TYPE_CHECKING:
    from ...engine.data_models import InteractionDefinition


class SocialSystem(System):
    """
    Manages social relationships, memory formation, and interaction effects.

    This system handles the lifecycle of social interactions, from processing requests
    to applying their effects on entity states and relationships. It periodically cleans up
    stale relationships to manage memory usage.

    Attributes:
        trait_service (Optional[TraitService]): Service for accessing trait data.
        skill_service (Optional[SkillService]): Service for managing skills and XP.
        audio (Optional[AudioManager]): Manager for playing sound effects.
        cleanup_index (int): Index cursor for incremental relationship cleanup.
        event_bus (EventBus): Event bus for publishing/subscribing to social events.
        headline_counter (int): Monotonic ref counter for memory IDs.
    """

    # Batch processing size for relationship cleanup to distribute load.
    CLEANUP_BATCH_SIZE = 10

    # Relationships older than this (in game seconds) are purged (excluding family/mates).
    RELATIONSHIP_MAX_AGE = 600.0  # 10 minutes

    # Base compatibility score for entities with identical personalities.
    BASE_COMPATIBILITY_SCORE = 100.0

    # Divisor for personality axis differences (higher value = less sensitivity to differences).
    COMPATIBILITY_DIVISOR = 4.0

    # Visual feedback settings.
    FLOATING_TEXT_SIZE = 24
    FLOATING_TEXT_LIFETIME = 1.5

    # Interaction feedback colors.
    COLOR_DEFAULT = (255, 255, 255)
    COLOR_FRIENDLY = (100, 255, 100)
    COLOR_HOSTILE = (255, 50, 50)
    COLOR_ROMANTIC = (255, 105, 180)
    COLOR_FEED = (255, 200, 50)
    COLOR_SAD = (100, 100, 255)

    # Memories with importance above this threshold are promoted to the core buffer.
    MEMORY_IMPORTANCE_THRESHOLD = 50.0

    def __init__(self) -> None:
        """
        Initializes the SocialSystem.
        """
        super().__init__()
        self.trait_service: TraitService | None = None
        self.skill_service: SkillService | None = None
        self.audio: AudioManager | None = None
        self.cleanup_index = 0
        self.headline_counter = 0
        # Cached config value — GameConfig is immutable at runtime.
        self._memory_importance_threshold: float = self.MEMORY_IMPORTANCE_THRESHOLD

    def initialize(self) -> None:
        """Called when the system is added to the world."""
        from ...config import GameConfig

        self.event_bus = self.ecs_world.services.get(EventBus)

        # Cache the memory importance threshold from config once at startup.
        config = self.ecs_world.services.try_get(GameConfig)
        if config and hasattr(config.rules, "social"):
            self._memory_importance_threshold = (
                config.rules.social.memory_importance_threshold
            )

    def update(self, world: World, dt: float) -> None:
        """
        Updates the social system.

        Performs incremental cleanup of stale relationships and resolves service dependencies.

        Args:
            world (World): The ECS World instance.
            dt (float): Delta time since the last frame.
        """
        if not self.trait_service:
            self.trait_service = world.services.try_get(TraitService)
        if not self.skill_service:
            self.skill_service = world.services.try_get(SkillService)
        if not self.audio:
            self.audio = world.services.try_get(AudioManager)

        # Inject world for event handlers if not already present
        if not hasattr(self, "ecs_world"):
            self.ecs_world = world

        now = world.time
        self._process_relationships(world, now)

    def _process_relationships(self, world: World, now: float) -> None:
        """
        Processes relationship updates and cleanup in small batches.

        Args:
            world (World): The ECS World.
            now (float): Current game time.
        """
        all_entities = world.get_components_tuple(RelationshipRegistry)
        if not all_entities:
            return

        count = len(all_entities)
        start = self.cleanup_index % count
        end = min(start + self.CLEANUP_BATCH_SIZE, count)

        for i in range(start, end):
            eid, (registry,) = all_entities[i]
            self._cleanup_registry(world, eid, registry, now)

        self.cleanup_index = (self.cleanup_index + self.CLEANUP_BATCH_SIZE) % max(
            1, count
        )

    def _cleanup_registry(
        self, world: World, eid: int, registry: RelationshipRegistry, now: float
    ) -> None:
        """
        Purges old relationships and updates opinion scores.

        Args:
            world (World): The ECS World.
            eid (int): The entity ID owning the registry.
            registry (RelationshipRegistry): The relationship component.
            now (float): Current game time.
        """
        to_remove = []

        for other_id, rel_data in registry.relationships.items():
            self._update_opinion(world, eid, other_id, rel_data)

            # Check if relationship is exempt from decay (mates or family)
            other_registry = world.try_get_component(other_id, RelationshipRegistry)
            is_special = (other_id == registry.mate_id) or (
                registry.family_group_id is not None
                and other_registry is not None
                and other_registry.family_group_id == registry.family_group_id
            )

            age = now - rel_data.last_update
            if not is_special and age > self.RELATIONSHIP_MAX_AGE:
                to_remove.append(other_id)

        for rid in to_remove:
            del registry.relationships[rid]

    def process_interaction_request(
        self, world: World, initiator_id: int, request: InteractionRequest
    ) -> None:
        """
        Processes a direct social interaction request from the behavior tree.

        Args:
            world (World): The ECS World.
            initiator_id (int): Entity ID initiating the interaction.
            request (InteractionRequest): The request component containing details.
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
        Recalculates the total affinity (opinion) based on compatibility and memories.

        Args:
            world (World): The ECS World.
            subject_id (int): The entity "feeling" the opinion.
            other_id (int): The entity the opinion is about.
            rel_data (RelationshipData): The relationship data to update.
            force_compatibility_update (bool): Whether to force recalculation of base compatibility.
        """
        if force_compatibility_update or rel_data.base_compatibility == 0.0:
            if not self.trait_service:
                return

            subject_pers = world.try_get_component(subject_id, Personality)
            other_pers = world.try_get_component(other_id, Personality)

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

        Args:
            subject_pers (Personality): Personality of the subject.
            other_pers (Personality): Personality of the target.

        Returns:
            float: A compatibility score (typically centered around 0 to 100).
        """
        from ..social.opinion_calculator import OpinionCalculator

        return OpinionCalculator.calculate_base_compatibility(
            subject_pers, other_pers, self.trait_service
        )

    def on_social_interaction(self, event: SocialInteractionEvent) -> None:
        """
        Event handler for SocialInteractionEvent.

        Args:
            event (SocialInteractionEvent): The event payload.
        """
        if not hasattr(self, "ecs_world"):
            return
        self.register_interaction(
            self.ecs_world, event.initiator_id, event.target_id, event.interaction_type
        )

    def _check_condition(
        self, world: World, entity_id: int, condition: str | dict[str, Any]
    ) -> bool:
        """
        Checks if a specific condition is met by the entity.

        Args:
            world (World): The ECS World.
            entity_id (int): The entity to check.
            condition (str | dict[str, Any]): string expression, dict with 'expression', or dict with 'type'.

        Returns:
            bool: True if the condition is met, False otherwise.
        """
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
                skills = world.try_get_component(entity_id, Skills)
                if skills and skill_id in skills.states:
                    return bool(skills.states[skill_id].level >= min_level)
                return False

        return True

    def _get_attr(self, obj: Any, key: str, default: Any = None) -> Any:
        """Safe attribute/key accessor for mixed objects/dicts."""
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def register_interaction(
        self, world: World, actor_id: int, target_id: int, interaction_name: str
    ) -> None:
        """
        Registers and executes the effects of a social interaction.

        Args:
            world (World): The ECS World.
            actor_id (int): Initiator ID.
            target_id (int): Target ID.
            interaction_name (str): Name of the interaction (e.g., "Greet", "Attack").
        """
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

        now = world.time

        # Apply bidirectional impacts
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
        self,
        world: World,
        actor_id: int,
        target_id: int,
        interaction_data: "InteractionDefinition | dict[str, Any]",
    ) -> None:
        """
        Applies physical impacts (stats) and skill rewards.

        Args:
            world (World): The ECS World.
            actor_id (int): Initiator ID.
            target_id (int): Target ID.
            interaction_data (InteractionDefinition | dict[str, Any]): Configuration data for the interaction.
        """
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
        """
        Helper to apply physical stat changes (Health, Energy, etc.) to an entity.

        Args:
            world (World): The ECS World.
            entity_id (int): Target entity ID.
            impact (dict[str, float]): Dictionary of stat changes.
        """
        needs = world.try_get_component(entity_id, Needs)
        emotional = world.try_get_component(entity_id, EmotionalState)

        if needs:
            if "health" in impact:
                needs.adjust_health(impact["health"])
            if "energy" in impact:
                needs.adjust_energy(impact["energy"])
            if "hunger" in impact:
                needs.adjust_hunger(impact["hunger"])
            if "cleanliness" in impact:
                needs.adjust_cleanliness(impact["cleanliness"])

        if emotional:
            if "happiness" in impact:
                emotional.adjust_happiness(impact["happiness"])
            if "stress" in impact:
                emotional.adjust_stress(impact["stress"])

    SOCIAL_AUDIO_MAP = {
        "Talk": "talk",
        "Greet": "talk",
        "Fight": "hit",
        "Hit": "hit",
        "Dance": "jump",
    }

    def _play_audio(self, interaction_name: str) -> None:
        """
        Plays audio cue for the interaction using a mapped sound name.

        Args:
            interaction_name (str): Name of the interaction to map to sound.
        """
        if not self.audio:
            return

        sound_name = self.SOCIAL_AUDIO_MAP.get(interaction_name, "")
        if sound_name:
            self.audio.play_sound(sound_name)

    def _spawn_visual_feedback(
        self,
        world: World,
        entity_id: int,
        interaction_name: str,
        data: "InteractionDefinition | dict[str, Any]",
    ) -> None:
        """
        Spawns visual feedback (floating text/icon) over the target entity.

        Args:
            world (World): The ECS World.
            entity_id (int): Target entity ID.
            interaction_name (str): Name of the interaction.
            data (InteractionDefinition | dict[str, Any]): Interaction data.
        """
        trans = world.try_get_component(entity_id, Transform)
        if not trans:
            return

        text = "!"
        color = self.COLOR_DEFAULT
        base_impact = self._get_attr(data, "base_impact", 0.0)

        # Basic feedback mapping
        if interaction_name in ["Talk", "Greet"]:
            text = "♪"
            color = self.COLOR_FRIENDLY
        elif interaction_name in ["Fight", "Hit"]:
            text = "💢"
            color = self.COLOR_HOSTILE
        elif interaction_name == "Dance":
            text = "♥"
            color = self.COLOR_ROMANTIC
        elif interaction_name == "Feed":
            text = "Mogu"
            color = self.COLOR_FEED

        if base_impact < -10:
            text = "T_T"
            color = self.COLOR_SAD

        fx = trans.x + rng.uniform(-10, 10)
        fy = trans.y - 30
        create_floating_text(
            world,
            fx,
            fy,
            text,
            color,
            size=self.FLOATING_TEXT_SIZE,
            lifetime=self.FLOATING_TEXT_LIFETIME,
        )

    def _apply_impact(
        self,
        world: World,
        subject_id: int,
        other_id: int,
        data: "InteractionDefinition | dict[str, Any]",
        role: str,
        now: float,
    ) -> None:
        """
        Applies the social impact of an interaction to a subject's relationship and emotions.

        Args:
            world (World): The ECS World.
            subject_id (int): The entity being affected.
            other_id (int): The other party in the interaction.
            data (InteractionDefinition | dict[str, Any]): Interaction configuration data.
            role (str): "actor" or "target".
            now (float): Current game time.
        """
        registry = self._get_or_create_registry(world, subject_id)
        oid = int(other_id)  # Ensure int for RelationshipRegistry key typing.

        if oid not in registry.relationships:
            registry.relationships[cast(Any, oid)] = RelationshipData(last_update=now)

        rel = registry.relationships[cast(Any, oid)]
        rel.last_update = now

        social_impact = self._get_attr(data, "social_impact", {})
        base_impact_score = self._get_attr(data, "base_impact", 0.0)
        modifiers = self._get_attr(data, "modifiers", {})
        event_type = self._get_attr(data, "type", "GENERIC")

        # Use OpinionCalculator for impact logic
        from ..social.opinion_calculator import OpinionCalculator

        d_affinity, d_trust, d_fear, d_familiarity = (
            OpinionCalculator.calculate_impact_deltas(
                world, subject_id, other_id, social_impact, modifiers, base_impact_score
            )
        )

        emotional = world.try_get_component(subject_id, EmotionalState)
        if emotional:
            OpinionCalculator.update_emotional_state(emotional, base_impact_score)

        rel.adjust_trust(d_trust)
        rel.adjust_fear(d_fear)
        rel.familiarity = max(0, min(100, rel.familiarity + d_familiarity))

        self._add_memory_headline(
            world, rel, base_impact_score, d_affinity, event_type, now
        )
        self._update_opinion(world, subject_id, other_id, rel)

    def _get_or_create_registry(
        self, world: World, entity_id: int
    ) -> RelationshipRegistry:
        """Helper to get or create RelationshipRegistry component."""
        registry = world.try_get_component(entity_id, RelationshipRegistry)
        if not registry:
            registry = RelationshipRegistry()
            world.commands.add_component(entity_id, registry)
        return registry

    def _add_memory_headline(
        self,
        world: World,
        rel: RelationshipData,
        base_impact_score: float,
        d_affinity: float,
        event_type: str,
        now: float,
    ) -> None:
        """
        Constructs and adds a memory headline to the relationship.

        Args:
            world (World): The ECS World.
            rel (RelationshipData): Relationship to update.
            base_impact_score (float): Raw importance.
            d_affinity (float): Sentiment change.
            event_type (str): Type of event.
            now (float): Timestamp.
        """
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

            rel.add_headline(headline, threshold=self._memory_importance_threshold)

