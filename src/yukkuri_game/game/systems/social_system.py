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
from ..services import TimeService
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

        time_service = world.services.try_get(TimeService)
        now = time_service.time_elapsed if time_service else time.time()

        # 1. Update Mood based on Stats and Decay
        # Iterating over entities that have BOTH Personality and YukkuriStats for mood updates
        for entity, (pers, stats) in world.get_components_tuple(Personality, YukkuriStats):
            self._update_mood_components(pers, stats, dt)

        # 2. Update Relationships (Cleanup & Compatibility Drift)
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
                # Retention policy: inactive relationships are removed
                # cutoff: relationships older than this DURATION are removed
                max_age = 600 # 10 minutes

                for other_id, rel_data in registry.relationships.items():
                    # Compatibility Drift
                    self._process_compatibility_drift(world, eid, other_id, rel_data, dt)

                    # If not permanent (family/mate) and old
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
        """
        Slowly drifts affinity towards the natural compatibility level defined by traits.
        """
        if not self.trait_service:
            return

        subject_pers = world.get_component(subject_id, Personality)
        other_pers = world.get_component(other_id, Personality)

        if not subject_pers or not other_pers:
            return

        base_compatibility = 0.0

        # Calculate target compatibility based on Traits
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

        # Drift towards base_compatibility
        # Rate: 1 point per 60 seconds (approx)
        drift_speed = 1.0 / 60.0

        diff = base_compatibility - rel_data.affinity
        # Only drift if significant difference
        if abs(diff) > 1.0:
            change = math.copysign(drift_speed * dt, diff)
            # Don't overshoot
            if abs(change) > abs(diff):
                rel_data.affinity = base_compatibility
            else:
                rel_data.affinity += change


    def _update_mood_components(self, pers: Personality, stats: YukkuriStats, dt: float) -> None:
        """
        Updates the mood of an entity based on stats and decay.
        """
        # Decay current mood intensity
        if pers.mood_score > 0:
            pers.mood_score -= dt * 5.0 # Decay rate
            if pers.mood_score <= 0:
                pers.mood_score = 0
                pers.mood = "NEUTRAL"

        # Check for Stat-driven Moods (Overrides neutral or weak moods)
        # Priority: SCARED (Critical Health) > FURIOUS (Critical Stress) > SAD (Starving/Unhappy) > HAPPY (High needs)

        # If current mood is strong (>50), we might stick with it unless critical
        if pers.mood_score > 50.0:
            return

        new_mood = None
        new_score = 0.0

        if stats.health < stats.max_health * 0.3:
            new_mood = "SCARED"
            new_score = 80.0
        elif getattr(stats, 'stress', 0.0) > 80.0:
            new_mood = "FURIOUS"
            new_score = 70.0
        elif stats.hunger > 80.0 or stats.happiness < 20.0:
            new_mood = "SAD"
            new_score = 60.0
        elif stats.happiness > 90.0 and stats.hunger < 10.0:
            new_mood = "HAPPY"
            new_score = 60.0

        if new_mood and (new_mood != pers.mood or new_score > pers.mood_score):
            pers.mood = new_mood
            pers.mood_score = new_score

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

    def _update_relationship_decay(self, rel_data: RelationshipData, now: float) -> None:
        """
        Lazily updates relationship values based on time elapsed since last update.

        Args:
            rel_data (RelationshipData): The relationship data to update.
            now (float): Current game time.

        Returns:
            None
        """
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

        time_service = world.services.try_get(TimeService)
        now = time_service.time_elapsed if time_service else time.time()

        # Apply impacts
        self._apply_impact(world, actor_id, target_id, interaction_data, role="actor", now=now)
        self._apply_impact(world, target_id, actor_id, interaction_data, role="target", now=now)

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

    def _apply_impact(self, world: World, subject_id: int, other_id: int, data: Dict[str, Any], role: str, now: float) -> None:
        """
        Applies the social impact to the subject regarding the other.

        Args:
            world (World): The ECS World.
            subject_id (int): The subject entity ID.
            other_id (int): The other entity ID.
            data (Dict[str, Any]): The interaction data.
            role (str): The role of the subject ("actor" or "target").
            now (float): Current game time.

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
            registry.relationships[other_id] = RelationshipData(last_update=now)

        rel = registry.relationships[other_id]

        # LAZY DECAY: Update decay before applying new impact
        self._update_relationship_decay(rel, now)

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

            # Use Values to multiply impacts
            # Example: High Compassion -> Penalize bad acts more, reward nice acts more
            # Proposal: "Values act as multipliers for specific types of actions"
            # Since we don't have explicit 'action type' in impact data, we can infer from base_impact sign
            compassion = subject_personality.values.get("compassion", 50.0)

            # Compassion Multiplier
            # > 50 increases positive social impact, > 50 increases negative social impact (sensitivity)
            comp_mult = 1.0 + (compassion - 50.0) / 100.0 # 0.5 to 1.5

            if base_impact_score > 0:
                d_affinity *= comp_mult
                d_trust *= comp_mult
            elif base_impact_score < 0:
                # If negative, high compassion means they get MORE upset (lower affinity faster)
                d_affinity *= comp_mult
                d_trust *= comp_mult
                d_fear *= comp_mult

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
                timestamp=now,
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
