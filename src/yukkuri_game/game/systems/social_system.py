from typing import TYPE_CHECKING, List, Dict, Optional, Any
from ..engine.ecs import System, World
from ..engine.event_bus import EventBus
from ..yukkuri_components import RelationshipRegistry, RelationshipData, MemoryRecord, Personality, YukkuriStats
from ..trait_service import TraitService
from ..services import TimeService
import time

if TYPE_CHECKING:
    from ..events import SocialInteractionEvent

class SocialSystem(System):
    """
    System responsible for managing social interactions, relationships, and memory.
    """
    def __init__(self, world: World):
        self.world = world
        self.trait_service = world.services.get(TraitService)
        self.time_service = world.services.get(TimeService)

        # Subscribe to social events if EventBus is available
        self.event_bus = world.services.try_get(EventBus)
        if self.event_bus:
            # Import locally to avoid circular imports if any, though likely safe
            from ..events import SocialInteractionEvent
            self.event_bus.subscribe(SocialInteractionEvent, self.on_social_interaction)

    def on_social_interaction(self, event: 'SocialInteractionEvent') -> None:
        """
        Handles SocialInteractionEvent.
        """
        self.process_interaction(event.actor_id, event.target_id, event.interaction_type, event.context or {})

    def process_interaction(self, actor_id: int, target_id: int, interaction_type: str, context: Dict[str, Any] = {}) -> None:
        """
        Processes a social interaction between two entities.

        Args:
            actor_id: The ID of the actor.
            target_id: The ID of the target.
            interaction_type: The type of interaction (key in interactions.toml).
            context: Additional context for the interaction.
        """
        interaction_def = self.trait_service.get_interaction(interaction_type)
        if not interaction_def:
            return

        current_time = self.time_service.time_elapsed

        # 1. Apply immediate impact to target (e.g. stats)
        # This might be handled by the action implementation itself,
        # but social consequences are handled here.

        # 2. Update Relationship (Target views Actor)
        self._update_relationship(target_id, actor_id, interaction_type, interaction_def, current_time)

        # 3. Update Relationship (Actor views Target) - optional, depending on interaction
        # Usually interactions are symmetric in some way, or trigger a reaction.

    def _update_relationship(self, observer_id: int, subject_id: int, action_type: str, interaction_def: Dict[str, Any], timestamp: float):
        """
        Updates how observer views subject based on an action.
        """
        registry = self.world.get_component(observer_id, RelationshipRegistry)
        if not registry:
            return

        if subject_id not in registry.relationships:
            registry.relationships[subject_id] = RelationshipData()
            # Initialize timestamp if new
            registry.relationships[subject_id].last_interaction_time = timestamp

        rel = registry.relationships[subject_id]

        # Apply decay before applying new changes
        self._apply_decay(rel, timestamp)

        # Base impacts
        social_impact = interaction_def.get("social_impact", {})

        # Apply modifiers based on Observer's traits (how they perceive it)
        # and Subject's traits (how they are perceived).

        observer_personality = self.world.get_component(observer_id, Personality)
        subject_personality = self.world.get_component(subject_id, Personality)

        affinity_change = social_impact.get("affinity", 0.0)
        trust_change = social_impact.get("trust", 0.0)
        fear_change = social_impact.get("fear", 0.0)

        # Check interaction modifiers
        modifiers = interaction_def.get("modifiers", {})

        # Apply trait-based modifiers
        # Check both Subject (Actor) and Observer (Victim) traits

        # Check Subject traits (e.g., if Actor is "Mean", they deal more fear)
        if subject_personality:
            for trait in subject_personality.traits:
                key = f"actor_trait:{trait}"
                if key in modifiers:
                    mod = modifiers[key]
                    affinity_change += mod.get("affinity", 0.0)
                    trust_change += mod.get("trust", 0.0)
                    fear_change += mod.get("fear", 0.0)

        # Check Observer traits (e.g., if Victim is "Weak", they take more fear)
        # The design doc example was "trait:WEAK", implying the trait is on the entity being affected (the observer of the relationship)
        # or it could be generic. Let's support "trait:TRAIT" (Observer) and "actor_trait:TRAIT" (Subject) conventions.
        if observer_personality:
            for trait in observer_personality.traits:
                key = f"trait:{trait}"
                if key in modifiers:
                    mod = modifiers[key]
                    affinity_change += mod.get("affinity", 0.0)
                    trust_change += mod.get("trust", 0.0)
                    fear_change += mod.get("fear", 0.0)

        # Apply changes
        rel.affinity = max(-100.0, min(100.0, rel.affinity + affinity_change))
        rel.trust = max(0.0, min(100.0, rel.trust + trust_change))
        rel.fear = max(0.0, min(100.0, rel.fear + fear_change))
        rel.familiarity = max(0.0, min(100.0, rel.familiarity + 1.0)) # Interaction increases familiarity

        # Add Memory
        base_impact = interaction_def.get("base_impact", 0.0)
        memory = MemoryRecord(
            timestamp=timestamp,
            actor_id=subject_id,
            action_type=action_type,
            impact=base_impact,
            permanent=False # TODO: Logic for trauma
        )
        rel.memories.append(memory)

        # Limit memory size
        if len(rel.memories) > 50:
            rel.memories.pop(0)

    def _apply_decay(self, rel: RelationshipData, current_time: float):
        """
        Applies decay to relationship metrics based on elapsed time.
        """
        if rel.last_interaction_time <= 0.0:
            rel.last_interaction_time = current_time
            return

        elapsed = current_time - rel.last_interaction_time
        if elapsed <= 0:
            return

        # Decay rates (per second) - TODO: Make configurable
        decay_rate = 0.05 # 5% per 100 seconds effectively if handled right?
        # Let's say decay is 1 point per 60 seconds towards 0
        decay_amount = (elapsed / 60.0) * 0.5

        # Decay affinity towards 0
        if rel.affinity > 0:
            rel.affinity = max(0.0, rel.affinity - decay_amount)
        elif rel.affinity < 0:
            rel.affinity = min(0.0, rel.affinity + decay_amount)

        # Decay fear towards 0
        if rel.fear > 0:
            rel.fear = max(0.0, rel.fear - decay_amount)

        # Trust decays towards 0? Or stays? Usually trust is hard to build, easy to lose.
        # Let's say trust decays very slowly if not reinforced.
        if rel.trust > 0:
            rel.trust = max(0.0, rel.trust - (decay_amount * 0.1))

        rel.last_interaction_time = current_time

    def update(self, world: World, dt: float) -> None:
        """
        Periodic updates.
        """
        pass
