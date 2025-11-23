import math
import time
from typing import Optional, Dict, List
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
    """

    def __init__(self, event_bus: EventBus):
        super().__init__()
        self.trait_service: Optional[TraitService] = None
        self.last_decay_time = time.time()
        self.decay_interval = 5.0 # Run decay logic every 5 seconds (simulated)
        self.event_bus = event_bus

        self.event_bus.subscribe(SocialInteractionEvent, self.on_social_interaction)

    def update(self, world: World, dt: float) -> None:
        """
        Updates social states. This includes decaying temporary emotions/relationship values.
        """
        if not self.trait_service:
            self.trait_service = world.services.try_get(TraitService)

        # Periodic Decay
        current_time = time.time()
        if current_time - self.last_decay_time > self.decay_interval:
            self.last_decay_time = current_time
            self._process_decay(world)

    def on_social_interaction(self, event: SocialInteractionEvent) -> None:
        """
        Event handler for social interactions.
        """
        # We need access to the world. System has self.ecs_world injected by World.add_system
        if not hasattr(self, 'ecs_world'):
            # Should be set by World when system added
            return

        self.register_interaction(self.ecs_world, event.initiator_id, event.target_id, event.interaction_type)

    def _process_decay(self, world: World):
        """
        Decays social values towards neutral/base states.
        """
        # We iterate over entities with RelationshipRegistry
        # Note: In a large world, this should be distributed over frames.
        entities = world.get_entities_with(RelationshipRegistry)

        for entity in entities:
            registry = world.get_component(entity, RelationshipRegistry)
            if not registry:
                continue

            for target_id, rel_data in registry.relationships.items():
                # Decay Affinity towards 0
                if rel_data.affinity > 0.1:
                    rel_data.affinity -= 0.5
                elif rel_data.affinity < -0.1:
                    rel_data.affinity += 0.5

                # Decay Fear slowly
                if rel_data.fear > 0.1:
                    rel_data.fear -= 0.2

                # Trust decays very slowly if positive, or stays?
                # Let's say trust is harder to lose naturally, but decays if very high
                if rel_data.trust > 50.0:
                    rel_data.trust -= 0.1

                # Memory clean up (remove old memories)
                # Assuming timestamp is simple time.time()
                # 300 seconds (5 mins) retention for non-permanent
                cutoff = time.time() - 300
                rel_data.memories = [m for m in rel_data.memories if m.permanent or m.timestamp > cutoff]

    def register_interaction(self, world: World, actor_id: int, target_id: int, interaction_name: str):
        """
        Registers a social interaction between two Yukkuris and applies its effects.

        Args:
            world: The ECS world.
            actor_id: The ID of the doer.
            target_id: The ID of the receiver.
            interaction_name: The key in interactions.toml (e.g. "Hit", "Greet").
        """
        if not self.trait_service:
            self.trait_service = world.services.try_get(TraitService)
            if not self.trait_service:
                return

        interaction_data = self.trait_service.get_interaction(interaction_name)
        if not interaction_data:
            # Try to find a fallback or just log
            # Map "Fight" -> "Hit" if not found? No, we added Fight to TOML.
            logger.warning(f"Unknown interaction: {interaction_name}")
            return

        # Apply impacts
        self._apply_impact(world, actor_id, target_id, interaction_data, role="actor")
        self._apply_impact(world, target_id, actor_id, interaction_data, role="target")

        # Visual Feedback
        self._spawn_visual_feedback(world, target_id, interaction_name, interaction_data)

    def _spawn_visual_feedback(self, world: World, entity_id: int, interaction_name: str, data: Dict):
        """
        Spawns floating text or icons based on interaction result.
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

    def _apply_impact(self, world: World, subject_id: int, other_id: int, data: Dict, role: str):
        """
        Applies the social impact to the subject regarding the other.
        """
        # We generally only care about how the TARGET is affected by the ACTOR's action.
        if role == "actor":
            # Optional: Actor might feel satisfaction or guilt.
            # For now, we only update target's feelings towards actor.
            return

        registry = world.get_component(subject_id, RelationshipRegistry)
        if not registry:
            registry = RelationshipRegistry()
            world.add_component(subject_id, registry)

        if other_id not in registry.relationships:
            registry.relationships[other_id] = RelationshipData()

        rel = registry.relationships[other_id]

        # Base Impact
        social_impact = data.get("social_impact", {})

        d_affinity = social_impact.get("affinity", 0.0)
        d_trust = social_impact.get("trust", 0.0)
        d_fear = social_impact.get("fear", 0.0)
        d_familiarity = social_impact.get("familiarity", 0.0)

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

            # Check Mood (not implemented fully in component, but slot exists)
            # Assuming mood is stored in personality.mood
            mood_key = f"mood:{subject_personality.mood}"
            if mood_key in modifiers:
                mod = modifiers[mood_key]
                d_affinity += mod.get("affinity", 0.0)

        # Update values clamped
        rel.affinity = max(-100, min(100, rel.affinity + d_affinity))
        rel.trust = max(0, min(100, rel.trust + d_trust))
        rel.fear = max(0, min(100, rel.fear + d_fear))
        rel.familiarity = max(0, min(100, rel.familiarity + d_familiarity))

        # Add Memory
        base_impact_score = data.get("base_impact", 0.0)
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
