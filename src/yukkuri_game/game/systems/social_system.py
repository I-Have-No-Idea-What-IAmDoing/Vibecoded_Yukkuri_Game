"""
Module implementing the social system for Yukkuri interaction and relationship management.
"""
import math
import time
from typing import Optional, Dict, List, Any
from loguru import logger
import random
from collections import deque

from ...engine.ecs import System, World
from ...engine.event_bus import EventBus
from ..utils.evaluator import ConditionEvaluator
from ..components import Transform, InteractionRequest
from ..yukkuri_components import YukkuriStats, RelationshipRegistry, RelationshipData, MemoryHeadline, Personality, EmotionalState, Skills
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
        self.trait_service: Optional[TraitService] = None
        self.skill_service: Optional[SkillService] = None
        self.cleanup_index = 0
        self.cleanup_batch_size = 10
        self.event_bus = event_bus

        # Note: We no longer subscribe to SocialInteractionEvent for resolution logic
        # because we trigger logic via InteractionRequest directly.
        # This avoids double-triggering logic when we publish the event ourselves.
        # self.event_bus.subscribe(SocialInteractionEvent, self.on_social_interaction)

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

        time_service = world.services.try_get(TimeService)
        now = time_service.time_elapsed if time_service else time.time()

        # Process Interaction Requests (Talk/Fight/Dance etc)
        # We look for InteractionRequest with specific actions (not "Eat" which is handled by HungerSystem)
        # Note: HungerSystem might have already processed food items, so here we mostly see Social.

        entities_with_requests = list(world.get_components_tuple(InteractionRequest, Transform))
        for entity_id, (request, _) in entities_with_requests:
            # logger.info(f"Processing request for {entity_id}: {request.action}")
            if request.action in ["Talk", "Fight", "Dance"]:
                self.process_interaction_request(world, entity_id, request)
                if world.has_component(entity_id, InteractionRequest):
                    world.remove_component(entity_id, InteractionRequest)

        # Update Relationships (Cleanup & Opinion Update)
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
                to_remove = []
                max_age = 600 # 10 minutes

                for other_id, rel_data in registry.relationships.items():
                    # Recalculate Opinion (Affinity)
                    self._update_opinion(world, eid, other_id, rel_data)

                    other_registry = world.get_component(other_id, RelationshipRegistry)
                    is_special = (other_id == registry.mate_id) or \
                                 (registry.family_group_id is not None and \
                                  other_registry is not None and \
                                  other_registry.family_group_id == registry.family_group_id)

                    age = now - rel_data.last_update
                    if not is_special and age > max_age:
                        to_remove.append(other_id)

                for rid in to_remove:
                    del registry.relationships[rid]

        self.cleanup_index = (self.cleanup_index + self.cleanup_batch_size) % max(1, count)

    def process_interaction_request(self, world: World, initiator_id: int, request: InteractionRequest) -> None:
        """
        Process a direct social interaction request from the behavior tree.
        """
        target_id = request.target_id
        action = request.action

        if not world.entity_exists(target_id):
            return

        # Perform the interaction logic
        self.register_interaction(world, initiator_id, target_id, action)

        # Dispatch event for other listeners (e.g. GossipSystem)
        self.event_bus.publish(SocialInteractionEvent(initiator_id, target_id, action))

    def _update_opinion(self, world: World, subject_id: int, other_id: int, rel_data: RelationshipData, force_compatibility_update: bool = False) -> None:
        """
        Recalculates the opinion (affinity) based on the formula:
        Opinion = Base Compatibility + Sum(CoreMemories) + Sum(TrivialEvents)

        Args:
            world (World): The ECS World.
            subject_id (int): The entity holding the opinion.
            other_id (int): The target of the opinion.
            rel_data (RelationshipData): The relationship data object.
            force_compatibility_update (bool): Whether to force recompute base compatibility.
        """
        if not self.trait_service:
            return

        # 1. Update Base Compatibility (if needed, or just every time for simplicity)
        subject_pers = world.get_component(subject_id, Personality)
        other_pers = world.get_component(other_id, Personality)

        if subject_pers and other_pers:
            base_compatibility = 0.0

            # Calculate from Axis comparison
            if subject_pers.axis and other_pers.axis:
                diff_kind = abs(subject_pers.axis.kindness - other_pers.axis.kindness)
                diff_ener = abs(subject_pers.axis.energy - other_pers.axis.energy)
                diff_brav = abs(subject_pers.axis.bravery - other_pers.axis.bravery)
                diff_gree = abs(subject_pers.axis.greed - other_pers.axis.greed)

                total_diff = diff_kind + diff_ener + diff_brav + diff_gree
                # 800 diff -> -100. 0 diff -> 100.
                base_compatibility += (100.0 - (total_diff / 4.0))

            # Traits compatibility
            for my_trait in subject_pers.traits:
                trait_data = self.trait_service.get_trait(my_trait)
                # trait_data is TraitDefinition (Struct)
                if not trait_data:
                    continue

                # Access social_modifiers.
                # Defensively check if dict or object.
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

            rel_data.base_compatibility = base_compatibility

        # 2. Use Cached Memory Sums (O(1))
        memory_score = rel_data.core_sentiment_sum + rel_data.trivial_sentiment_sum

        # 3. Final Calculation
        rel_data.affinity = rel_data.base_compatibility + memory_score

    def on_social_interaction(self, event: SocialInteractionEvent) -> None:
        """
        Handler for SocialInteractionEvent.

        Args:
            event (SocialInteractionEvent): The event data.
        """
        if not hasattr(self, 'ecs_world'):
            return
        self.register_interaction(self.ecs_world, event.initiator_id, event.target_id, event.interaction_type)

    def _check_condition(self, world: World, entity_id: int, condition: Any) -> bool:
        """
        Checks if a condition is met by the entity.

        Args:
            world (World): The ECS World.
            entity_id (int): The entity to check.
            condition (Any): The condition definition (dict or expression string).

        Returns:
            bool: True if condition is met.
        """
        # Handle string expressions directly
        if isinstance(condition, str):
            evaluator = world.services.try_get(ConditionEvaluator)
            if evaluator:
                ctx = evaluator.build_context(world, entity_id)
                return evaluator.evaluate(condition, ctx)
            return False

        # Handle dict-based conditions
        if isinstance(condition, dict):
            # Support explicit expression key
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
                return False # Skill not found -> Fail

        # Add other condition types here (e.g. stat check)
        return True

    def _get_attr(self, obj: Any, key: str, default: Any = None) -> Any:
        """Helper to get attribute from dict or object."""
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def register_interaction(self, world: World, actor_id: int, target_id: int, interaction_name: str) -> None:
        """
        Registers a social interaction, applying effects to both parties.

        Args:
            world (World): The ECS World.
            actor_id (int): The initiator.
            target_id (int): The target.
            interaction_name (str): The interaction type name.
        """
        if not self.trait_service:
            self.trait_service = world.services.try_get(TraitService)
            if not self.trait_service:
                return

        if not self.skill_service:
            self.skill_service = world.services.try_get(SkillService)

        interaction_data = self.trait_service.get_interaction(interaction_name)
        if not interaction_data:
            logger.warning(f"Unknown interaction: {interaction_name}")
            return

        # Check conditions (e.g. Skill Requirements)
        conditions = self._get_attr(interaction_data, "conditions", [])
        if conditions:
            for cond in conditions:
                if not self._check_condition(world, actor_id, cond):
                    logger.debug(f"Interaction {interaction_name} failed condition: {cond}")
                    return

        time_service = world.services.try_get(TimeService)
        now = time_service.time_elapsed if time_service else time.time()

        self._apply_impact(world, actor_id, target_id, interaction_data, role="actor", now=now)
        self._apply_impact(world, target_id, actor_id, interaction_data, role="target", now=now)
        self._spawn_visual_feedback(world, target_id, interaction_name, interaction_data)

        # --- Specific Gameplay Logic (Hardcoded migration from GameService) ---
        # TODO: Move these into data-driven InteractionDefinition in the future

        # 1. Damage (Fight)
        if interaction_name == "Fight":
            damage = 5.0
            self._apply_damage(world, actor_id, damage)
            self._apply_damage(world, target_id, damage)

            # Additional Stress/Happiness impact for Fight is usually handled by data,
            # but legacy code had specific logic. The data model should handle emotional impact.
            # We assume TOML covers happiness/stress changes.

        # 2. Skill XP
        if self.skill_service:
            if interaction_name == "Fight":
                self.skill_service.add_xp(actor_id, "combat", 10.0)
            elif interaction_name == "Dance":
                self.skill_service.add_xp(actor_id, "athletics", 5.0)
                self.skill_service.add_xp(actor_id, "socialization", 2.0)
            elif interaction_name == "Talk":
                self.skill_service.add_xp(actor_id, "socialization", 5.0)
            else:
                # Default fallback
                xp_amount = 5.0
                self.skill_service.add_xp(actor_id, "socialization", xp_amount)

    def _apply_damage(self, world: World, entity_id: int, amount: float) -> None:
        """Helper to apply damage to an entity."""
        stats = world.get_component(entity_id, YukkuriStats)
        if stats:
            stats.health = max(0.0, stats.health - amount)


    def _spawn_visual_feedback(self, world: World, entity_id: int, interaction_name: str, data: Any) -> None:
        """
        Spawns visual feedback (floating text/icon) for the interaction.

        Args:
            world (World): The ECS World.
            entity_id (int): The entity to show feedback on.
            interaction_name (str): The name of the interaction.
            data (Any): The interaction data definition.
        """
        trans = world.get_component(entity_id, Transform)
        if not trans: return

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

    def _apply_impact(self, world: World, subject_id: int, other_id: int, data: Any, role: str, now: float) -> None:
        """
        Applies the social impact of an interaction to a subject.

        Args:
            world (World): The ECS World.
            subject_id (int): The entity receiving the impact.
            other_id (int): The other entity involved.
            data (Any): Interaction data.
            role (str): "actor" or "target".
            now (float): Current timestamp.
        """
        if role == "actor":
            return

        registry = self._get_or_create_registry(world, subject_id)
        if other_id not in registry.relationships:
            registry.relationships[other_id] = RelationshipData(last_update=now)
        rel = registry.relationships[other_id]
        rel.last_update = now

        social_impact = self._get_attr(data, "social_impact", {})
        base_impact_score = self._get_attr(data, "base_impact", 0.0)
        modifiers = self._get_attr(data, "modifiers", {})
        event_type = self._get_attr(data, "type", "GENERIC")

        # Calculate deltas based on traits and personality
        # Pass other_id (the person interacting with subject) for skill checks
        d_affinity, d_trust, d_fear, d_familiarity = self._calculate_impact_deltas(
            world, subject_id, other_id, social_impact, modifiers, base_impact_score
        )

        # Update Emotional State
        self._update_emotional_state(world, subject_id, base_impact_score)

        # Update non-affinity relationship stats
        rel.trust = max(0, min(100, rel.trust + d_trust))
        rel.fear = max(0, min(100, rel.fear + d_fear))
        rel.familiarity = max(0, min(100, rel.familiarity + d_familiarity))

        # Add Memory and Update Opinion
        self._add_memory_headline(world, rel, base_impact_score, d_affinity, event_type, now)
        self._update_opinion(world, subject_id, other_id, rel)

    def _get_or_create_registry(self, world: World, entity_id: int) -> RelationshipRegistry:
        """
        Helper to get or create RelationshipRegistry component.

        Args:
            world (World): The ECS World.
            entity_id (int): The entity ID.

        Returns:
            RelationshipRegistry: The component.
        """
        registry = world.get_component(entity_id, RelationshipRegistry)
        if not registry:
            registry = RelationshipRegistry()
            world.add_component(entity_id, registry)
        return registry

    def _calculate_impact_deltas(self, world: World, subject_id: int, other_id: int, social_impact: Dict[str, float], modifiers: Dict[str, Dict[str, float]], base_impact_score: float) -> tuple[float, float, float, float]:
        """
        Calculates impact deltas considering personality and traits.

        Args:
            world (World): The ECS World.
            subject_id (int): The subject ID.
            other_id (int): The other entity ID (Actor).
            social_impact (Dict): Base social impact map.
            modifiers (Dict): Trait modifiers map.
            base_impact_score (float): Base impact score.

        Returns:
            tuple[float, float, float, float]: (d_affinity, d_trust, d_fear, d_familiarity).
        """
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

            # Handle Expressions (Check OTHER/ACTOR context)
            evaluator = world.services.try_get(ConditionEvaluator)
            if evaluator:
                actor_context = evaluator.build_context(world, other_id)
                for key, mod in modifiers.items():
                    # Skip trait/mood keys as they are subject-based or legacy
                    if key.startswith("trait:") or key.startswith("mood:"):
                        continue

                    # Evaluate expression against Actor
                    if evaluator.evaluate(key, actor_context):
                        d_affinity += mod.get("affinity", 0.0)
                        d_trust += mod.get("trust", 0.0)
                        d_fear += mod.get("fear", 0.0)


            kindness = 0
            if subject_personality.axis:
                kindness = subject_personality.axis.kindness

            if base_impact_score > 0:
                comp_mult = 1.0 + (kindness / 100.0)
                comp_mult = max(0.1, comp_mult)
                d_affinity *= comp_mult
                d_trust *= comp_mult
            elif base_impact_score < 0:
                # For negative impacts, selfish yukkuris should be vindictive (react strongly),
                # while kind ones might be forgiving (react weakly) or sensitive (react strongly).
                # Current design choice: Selfish = Vindictive (High reaction), Kind = Forgiving (Low reaction).
                comp_mult = 1.0 - (kindness / 100.0)
                comp_mult = max(0.1, comp_mult)

                d_affinity *= comp_mult
                d_trust *= comp_mult
                d_fear *= comp_mult

        return d_affinity, d_trust, d_fear, d_familiarity

    def _update_emotional_state(self, world: World, subject_id: int, base_impact_score: float) -> None:
        """
        Updates emotional state based on interaction impact.

        Args:
            world (World): The ECS World.
            subject_id (int): The subject entity ID.
            base_impact_score (float): The impact score.
        """
        emotional = world.get_component(subject_id, EmotionalState)
        if emotional:
            if base_impact_score < -15:
                emotional.happiness = max(-100.0, emotional.happiness - 20.0)
                emotional.stress = min(100.0, emotional.stress + 20.0)
            elif base_impact_score > 15:
                emotional.happiness = min(100.0, emotional.happiness + 20.0)

    def _add_memory_headline(self, world: World, rel: RelationshipData, base_impact_score: float, d_affinity: float, event_type: str, now: float) -> None:
        """
        Adds a memory headline to the relationship.

        Args:
            world (World): The ECS World.
            rel (RelationshipData): The relationship data.
            base_impact_score (float): The importance score.
            d_affinity (float): The sentiment change.
            event_type (str): The event type string.
            now (float): Current timestamp.
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
                event_type=event_type
            )

            from ...config import GameConfig
            config = world.services.try_get(GameConfig)
            threshold = 50.0
            if config and hasattr(config.rules, 'social'):
                threshold = config.rules.social.memory_importance_threshold

            rel.add_headline(headline, threshold=threshold)
