"""
Module implementing the social system for Yukkuri interaction and relationship management.
"""
import math
import time
from typing import Optional, Dict, List, Any
from loguru import logger
import random

from ...engine.ecs import System, World
from ...engine.event_bus import EventBus
from ..components import Transform
from ..yukkuri_components import YukkuriStats, RelationshipRegistry, RelationshipData, MemoryRecord, Personality
from ..trait_service import TraitService
from ..entity_factory import EntityFactory
from ..events import SocialInteractionEvent

class SocialSystem(System):
    """
    System responsible for managing social relationships, memory decay, and applying interaction effects.

    Attributes:
        trait_service (Optional[TraitService]): The service for accessing trait/interaction data.
        cleanup_index (int): Index for distributed cleanup.
        cleanup_batch_size (int): Batch size for distributed cleanup.
        event_bus (EventBus): The event bus.
    """

    def __init__(self, event_bus: EventBus):
        """
        Initializes the SocialSystem.

        Args:
            event_bus (EventBus): The global event bus.
        """
        super().__init__()
        self.trait_service: Optional[TraitService] = None
        # Distributed cleanup state
        self.cleanup_index = 0
        self.cleanup_batch_size = 10
        self.event_bus = event_bus

        self.event_bus.subscribe(SocialInteractionEvent, self.on_social_interaction)

    def update(self, world: World, dt: float) -> None:
        """
        Updates social states.
        Handles distributed cleanup of old relationships and Mood decay.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.

        Returns:
            None
        """
        if not self.trait_service:
            self.trait_service = world.services.try_get(TraitService)

        # 1. Mood Decay (for all entities, but this is lighter than relationship map iteration)
        # Ideally, this should also be distributed or event-driven, but for now we iterate stats
        # to decay mood score.
        entities_with_personality = world.get_entities_with(Personality)
        for entity in entities_with_personality:
            pers = world.get_component(entity, Personality)
            if pers and pers.mood_score > 0:
                pers.mood_score -= dt * 5.0 # Decay rate
                if pers.mood_score <= 0:
                    pers.mood_score = 0
                    pers.mood = "NEUTRAL"

        # 2. Distributed Relationship Cleanup
        # Only check N entities per frame to remove very old/irrelevant relationships
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
                now = time.time()
                # Retention policy: inactive relationships are removed
                # cutoff: relationships older than this DURATION are removed
                max_age = 600 # 10 minutes

                for other_id, rel_data in registry.relationships.items():
                    # If not permanent (family/mate) and old
                    # (Mate/Family logic usually kept elsewhere or flagged, assuming ID check is enough)
                    is_special = (other_id == registry.mate_id) or \
                                 (registry.family_group_id is not None and \
                                  world.has_component(other_id, RelationshipRegistry) and \
                                  world.get_component(other_id, RelationshipRegistry).family_group_id == registry.family_group_id)

                    age = now - rel_data.last_update
                    if not is_special and age > max_age:
                        to_remove.append(other_id)

                for rid in to_remove:
                    del registry.relationships[rid]

        self.cleanup_index = (self.cleanup_index + self.cleanup_batch_size) % max(1, count)

    def on_social_interaction(self, event: SocialInteractionEvent) -> None:
        """
        Event handler for social interactions.

        Args:
            event (SocialInteractionEvent): The social interaction event.

        Returns:
            None
        """
        # We need access to the world. System has self.ecs_world injected by World.add_system
        if not hasattr(self, 'ecs_world'):
            # Should be set by World when system added
            return

        self.register_interaction(self.ecs_world, event.initiator_id, event.target_id, event.interaction_type)

    def _update_relationship_decay(self, rel_data: RelationshipData) -> None:
        """
        Lazily updates relationship values based on time elapsed since last update.

        Args:
            rel_data (RelationshipData): The relationship data to update.

        Returns:
            None
        """
        now = time.time()
        if rel_data.last_update == 0.0:
            rel_data.last_update = now
            return

        elapsed = now - rel_data.last_update
        # Decay rates per second
        decay_affinity = 0.01 * elapsed # 0.1 per 10s
        decay_fear = 0.05 * elapsed
        decay_trust = 0.005 * elapsed

        # Apply decay
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
        """
        Registers a social interaction between two Yukkuris and applies its effects.

        Args:
            world (World): The ECS world.
            actor_id (int): The ID of the doer.
            target_id (int): The ID of the receiver.
            interaction_name (str): The key in interactions.toml (e.g. "Hit", "Greet").

        Returns:
            None
        """
        if not self.trait_service:
            self.trait_service = world.services.try_get(TraitService)
            if not self.trait_service:
                return

        interaction_data = self.trait_service.get_interaction(interaction_name)
        if not interaction_data:
            logger.warning(f"Unknown interaction: {interaction_name}")
            return

        # Apply impacts
        self._apply_impact(world, actor_id, target_id, interaction_data, role="actor")
        self._apply_impact(world, target_id, actor_id, interaction_data, role="target")

        # Visual Feedback
        self._spawn_visual_feedback(world, target_id, interaction_name, interaction_data)

    def _spawn_visual_feedback(self, world: World, entity_id: int, interaction_name: str, data: Dict[str, Any]) -> None:
        """
        Spawns floating text or icons based on interaction result.

        Args:
            world (World): The ECS World.
            entity_id (int): The entity ID.
            interaction_name (str): The interaction name.
            data (Dict[str, Any]): The interaction data.

        Returns:
            None
        """
        factory = world.services.try_get(EntityFactory)
        if not factory:
            return

        trans = world.get_component(entity_id, Transform)
        if not trans:
            return

        # Determine symbol based on impact or name
        text = "!"
        color = (255, 255, 255)

        base_impact = data.get("base_impact", 0.0)

        if interaction_name in ["Talk", "Greet"]:
            text = "♪" # Note
            color = (100, 255, 100)
        elif interaction_name in ["Fight", "Hit"]:
            text = "💢" # Anger
            color = (255, 50, 50)
        elif interaction_name == "Dance":
            text = "♥" # Heart
            color = (255, 105, 180)
        elif interaction_name == "Feed":
            text = "Mogu"
            color = (255, 200, 50)

        # Override if impact is negative
        if base_impact < -10:
             text = "T_T"
             color = (100, 100, 255)

        # Offset slightly
        fx = trans.x + random.uniform(-10, 10)
        fy = trans.y - 30

        factory.create_floating_text(fx, fy, text, color, size=24, lifetime=1.5)

    def _apply_impact(self, world: World, subject_id: int, other_id: int, data: Dict[str, Any], role: str) -> None:
        """
        Applies the social impact to the subject regarding the other.

        Args:
            world (World): The ECS World.
            subject_id (int): The subject entity ID.
            other_id (int): The other entity ID.
            data (Dict[str, Any]): The interaction data.
            role (str): The role of the subject ("actor" or "target").

        Returns:
            None
        """
        if role == "actor":
            # Optional: Actor might feel satisfaction or guilt.
            return

        registry = world.get_component(subject_id, RelationshipRegistry)
        if not registry:
            registry = RelationshipRegistry()
            world.add_component(subject_id, registry)

        if other_id not in registry.relationships:
            registry.relationships[other_id] = RelationshipData(last_update=time.time())

        rel = registry.relationships[other_id]

        # LAZY DECAY: Update decay before applying new impact
        self._update_relationship_decay(rel)

        # Base Impact
        social_impact = data.get("social_impact", {})

        d_affinity = social_impact.get("affinity", 0.0)
        d_trust = social_impact.get("trust", 0.0)
        d_fear = social_impact.get("fear", 0.0)
        d_familiarity = social_impact.get("familiarity", 0.0)
        base_impact_score = data.get("base_impact", 0.0)

        # Apply Modifiers
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

            # Check Mood
            mood_key = f"mood:{subject_personality.mood}"
            if mood_key in modifiers:
                mod = modifiers[mood_key]
                d_affinity += mod.get("affinity", 0.0)

            # UPDATE MOOD based on impact
            if base_impact_score < -15:
                # Strong negative event
                subject_personality.mood = "FURIOUS" if random.random() < 0.5 else "SCARED"
                subject_personality.mood_score = 100.0
            elif base_impact_score > 15:
                subject_personality.mood = "HAPPY"
                subject_personality.mood_score = 100.0

        # Update values clamped
        rel.affinity = max(-100, min(100, rel.affinity + d_affinity))
        rel.trust = max(0, min(100, rel.trust + d_trust))
        rel.fear = max(0, min(100, rel.fear + d_fear))
        rel.familiarity = max(0, min(100, rel.familiarity + d_familiarity))

        # Add Memory
        if abs(base_impact_score) > 0:
            memory = MemoryRecord(
                timestamp=time.time(),
                actor_id=other_id,
                action_type=data.get("type", "unknown"),
                impact=base_impact_score,
                permanent=False
            )
            rel.memories.append(memory)
            # Trim memories
            if len(rel.memories) > 20:
                rel.memories.pop(0)

        logger.debug(f"Interaction {role}: Entity {subject_id} view of {other_id} -> Aff:{rel.affinity:.1f}, Trust:{rel.trust:.1f}")
