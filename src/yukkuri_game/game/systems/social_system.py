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
from ..components import Transform
from ..yukkuri_components import YukkuriStats, RelationshipRegistry, RelationshipData, Headline, Personality, EmotionalState
from ..trait_service import TraitService
from ..services import TimeService
from ..entity_factory import EntityFactory
from ..events import SocialInteractionEvent

class SocialSystem(System):
    """
    System responsible for managing social relationships, memory decay, and applying interaction effects.
    """

    def __init__(self, event_bus: EventBus):
        super().__init__()
        self.trait_service: Optional[TraitService] = None
        self.cleanup_index = 0
        self.cleanup_batch_size = 10
        self.event_bus = event_bus

        self.event_bus.subscribe(SocialInteractionEvent, self.on_social_interaction)

        self.headline_counter = 0

    def update(self, world: World, dt: float) -> None:
        if not self.trait_service:
            self.trait_service = world.services.try_get(TraitService)

        time_service = world.services.try_get(TimeService)
        now = time_service.time_elapsed if time_service else time.time()

        # Update Relationships (Cleanup & Compatibility Drift)
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
                    self._process_compatibility_drift(world, eid, other_id, rel_data, dt)

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

    def _process_compatibility_drift(self, world: World, subject_id: int, other_id: int, rel_data: RelationshipData, dt: float) -> None:
        if not self.trait_service:
            return

        subject_pers = world.get_component(subject_id, Personality)
        other_pers = world.get_component(other_id, Personality)

        if not subject_pers or not other_pers:
            return

        base_compatibility = 0.0

        # Calculate from Axis comparison
        if subject_pers.axis and other_pers.axis:
            diff_kind = abs(subject_pers.axis.kindness - other_pers.axis.kindness)
            diff_ener = abs(subject_pers.axis.energy - other_pers.axis.energy)
            diff_brav = abs(subject_pers.axis.bravery - other_pers.axis.bravery)
            diff_gree = abs(subject_pers.axis.greed - other_pers.axis.greed)

            total_diff = diff_kind + diff_ener + diff_brav + diff_gree
            # 800 diff -> -100. 0 diff -> 100.
            # val = 100 - (diff / 4)
            base_compatibility += (100.0 - (total_diff / 4.0))

        # Traits compatibility
        for my_trait in subject_pers.traits:
            trait_data = self.trait_service.get_trait(my_trait)
            if not trait_data or "social_modifiers" not in trait_data:
                continue

            social_mods = trait_data["social_modifiers"]
            if "compatibility" not in social_mods:
                continue

            comp_map = social_mods["compatibility"]
            for other_trait in other_pers.traits:
                if other_trait in comp_map:
                    base_compatibility += comp_map[other_trait]

        # Drift
        drift_speed = 1.0 / 60.0
        diff = base_compatibility - rel_data.affinity
        if abs(diff) > 1.0:
            change = math.copysign(drift_speed * dt, diff)
            if abs(change) > abs(diff):
                rel_data.affinity = base_compatibility
            else:
                rel_data.affinity += change

    def on_social_interaction(self, event: SocialInteractionEvent) -> None:
        if not hasattr(self, 'ecs_world'):
            return
        self.register_interaction(self.ecs_world, event.initiator_id, event.target_id, event.interaction_type)

    def _update_relationship_decay(self, rel_data: RelationshipData, now: float) -> None:
        if rel_data.last_update == 0.0:
            rel_data.last_update = now
            return

        elapsed = now - rel_data.last_update
        decay_affinity = 0.01 * elapsed
        decay_fear = 0.05 * elapsed
        decay_trust = 0.005 * elapsed

        if rel_data.affinity > 0.1:
            rel_data.affinity = max(0, rel_data.affinity - decay_affinity)
        elif rel_data.affinity < -0.1:
            rel_data.affinity = min(0, rel_data.affinity + decay_affinity)

        if rel_data.fear > 0.1:
            rel_data.fear = max(0, rel_data.fear - decay_fear)

        if rel_data.trust > 50.0:
            rel_data.trust = max(50.0, rel_data.trust - decay_trust)

        rel_data.last_update = now

    def register_interaction(self, world: World, actor_id: int, target_id: int, interaction_name: str) -> None:
        if not self.trait_service:
            self.trait_service = world.services.try_get(TraitService)
            if not self.trait_service:
                return

        interaction_data = self.trait_service.get_interaction(interaction_name)
        if not interaction_data:
            logger.warning(f"Unknown interaction: {interaction_name}")
            return

        time_service = world.services.try_get(TimeService)
        now = time_service.time_elapsed if time_service else time.time()

        self._apply_impact(world, actor_id, target_id, interaction_data, role="actor", now=now)
        self._apply_impact(world, target_id, actor_id, interaction_data, role="target", now=now)
        self._spawn_visual_feedback(world, target_id, interaction_name, interaction_data)

    def _spawn_visual_feedback(self, world: World, entity_id: int, interaction_name: str, data: Dict[str, Any]) -> None:
        factory = world.services.try_get(EntityFactory)
        if not factory: return
        trans = world.get_component(entity_id, Transform)
        if not trans: return

        text = "!"
        color = (255, 255, 255)
        base_impact = data.get("base_impact", 0.0)

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
        factory.create_floating_text(fx, fy, text, color, size=24, lifetime=1.5)

    def _apply_impact(self, world: World, subject_id: int, other_id: int, data: Dict[str, Any], role: str, now: float) -> None:
        if role == "actor":
            # Optional: Actor feeling
            return

        registry = world.get_component(subject_id, RelationshipRegistry)
        if not registry:
            registry = RelationshipRegistry()
            world.add_component(subject_id, registry)

        if other_id not in registry.relationships:
            registry.relationships[other_id] = RelationshipData(last_update=now)

        rel = registry.relationships[other_id]
        self._update_relationship_decay(rel, now)

        social_impact = data.get("social_impact", {})
        d_affinity = social_impact.get("affinity", 0.0)
        d_trust = social_impact.get("trust", 0.0)
        d_fear = social_impact.get("fear", 0.0)
        d_familiarity = social_impact.get("familiarity", 0.0)
        base_impact_score = data.get("base_impact", 0.0)

        subject_personality = world.get_component(subject_id, Personality)
        modifiers = data.get("modifiers", {})

        if subject_personality:
            for trait in subject_personality.traits:
                key = f"trait:{trait}"
                if key in modifiers:
                    mod = modifiers[key]
                    d_affinity += mod.get("affinity", 0.0)
                    d_trust += mod.get("trust", 0.0)
                    d_fear += mod.get("fear", 0.0)

            kindness = 0
            if subject_personality.axis:
                kindness = subject_personality.axis.kindness

            comp_mult = 1.0 + (kindness / 100.0)
            if comp_mult < 0: comp_mult = 0.0

            if base_impact_score > 0:
                d_affinity *= comp_mult
                d_trust *= comp_mult
            elif base_impact_score < 0:
                d_affinity *= comp_mult
                d_trust *= comp_mult
                d_fear *= comp_mult

            # UPDATE EMOTIONAL STATE
            emotional = world.get_component(subject_id, EmotionalState)
            if emotional:
                if base_impact_score < -15:
                    emotional.happiness = max(-100.0, emotional.happiness - 20.0)
                    emotional.stress = min(100.0, emotional.stress + 20.0)
                elif base_impact_score > 15:
                    emotional.happiness = min(100.0, emotional.happiness + 20.0)

        rel.affinity = max(-100, min(100, rel.affinity + d_affinity))
        rel.trust = max(0, min(100, rel.trust + d_trust))
        rel.fear = max(0, min(100, rel.fear + d_fear))
        rel.familiarity = max(0, min(100, rel.familiarity + d_familiarity))

        # Add Headline
        if abs(base_impact_score) > 0:
            self.headline_counter += 1
            headline = Headline(
                id=self.headline_counter,
                timestamp=now,
                importance=abs(base_impact_score),
                is_locked=False,
                text=data.get("type", "unknown"),
                event_type=data.get("type", "GENERIC")
            )

            if headline.importance > 50.0:
                rel.core_buffer.add(headline)
            else:
                rel.trivial_buffer.add(headline)
