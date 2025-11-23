import math
import time
from typing import Optional, Dict, List
from loguru import logger

from ...engine.ecs import System, World
from ..components import Transform
from ..yukkuri_components import YukkuriStats, RelationshipRegistry, RelationshipData, MemoryRecord, Personality
from ..trait_service import TraitService

# We'll define a new component for Social Interaction Requests similar to InteractionRequest
# Or we can reuse InteractionRequest if we expand it, but a separate one is cleaner for now.
# For this task, I'll assume we process interactions triggered by behaviors or events.
# Since I don't have a "SocialInteractionRequest" component defined yet, I'll define a helper class/method
# that systems can call, OR I can scan for a new component.

# Let's create a SocialSystem that handles decay and provides an API for interactions.
# Actual interaction logic (e.g. performing the "Hit") might be in a Behavior, which then calls this system
# to register the social impact.

class SocialSystem(System):
    """
    System responsible for managing social relationships, memory decay, and applying interaction effects.
    """

    def __init__(self):
        super().__init__()
        self.trait_service: Optional[TraitService] = None

    def update(self, world: World, dt: float) -> None:
        """
        Updates social states. This includes decaying temporary emotions/relationship values.
        Optimization: We don't need to decay every frame. We can do it on access or periodically.
        For simplicity, we'll do a periodic check or just skip detailed decay here and rely on
        "on-access" decay or specific event-driven updates.

        However, if we want to simulate "forgetting" over time, we might need a slow process.
        Let's just iterate a subset of entities each frame?
        For MVP, let's not iterate everything every frame.
        """
        if not self.trait_service:
            self.trait_service = world.services.try_get(TraitService)

        # We can implement a lazy decay mechanism or a very slow tick.
        # For now, we will leave the update loop empty regarding decay
        # and assume decay happens when interactions occur or when we query relationships.
        pass

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
                logger.warning("TraitService not available for social interaction.")
                return

        interaction_data = self.trait_service.get_interaction(interaction_name)
        if not interaction_data:
            logger.warning(f"Unknown interaction: {interaction_name}")
            return

        # Apply impacts
        self._apply_impact(world, actor_id, target_id, interaction_data, role="actor")
        self._apply_impact(world, target_id, actor_id, interaction_data, role="target")

    def _apply_impact(self, world: World, subject_id: int, other_id: int, data: Dict, role: str):
        """
        Applies the social impact to the subject regarding the other.

        If role is "target", we look at how the target feels about the actor (affinity changes etc).
        If role is "actor", we might update how the actor feels (e.g. guilt, or satisfaction).
        Usually interactions define impact on the TARGET.

        data: The interaction definition from TOML.
        """
        # We generally only care about how the TARGET is affected by the ACTOR's action.
        # But sometimes the Actor also changes opinion (e.g. if I hit you, I might like you less or more).
        # The current data structure `social_impact` in TOML usually implies effect on the Target's view of Actor.

        if role == "actor":
            return # For now, ignore actor's internal shift unless specified

        registry = world.get_component(subject_id, RelationshipRegistry)
        if not registry:
            # Add one if missing?
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
        # Check traits of Subject (Subject is the one reacting)
        subject_personality = world.get_component(subject_id, Personality)
        modifiers = data.get("modifiers", {})

        if subject_personality:
            # Traits modifiers
            for trait in subject_personality.traits:
                key = f"trait:{trait}"
                if key in modifiers:
                    mod = modifiers[key]
                    d_affinity += mod.get("affinity", 0.0)
                    d_trust += mod.get("trust", 0.0)
                    d_fear += mod.get("fear", 0.0)

            # Mood modifiers
            if subject_personality.mood:
                key = f"mood:{subject_personality.mood}"
                if key in modifiers:
                    mod = modifiers[key]
                    d_affinity += mod.get("affinity", 0.0)
                    d_trust += mod.get("trust", 0.0)
                    d_fear += mod.get("fear", 0.0)

            # Value modifiers (e.g. Compassion, Greed)
            # Plan says: "Values act as multipliers".
            # Implementation: We don't have data on which value multiplies what,
            # but if we had, it would go here. For now, mood support is critical.

        # Update values clamped
        rel.affinity = max(-100, min(100, rel.affinity + d_affinity))
        rel.trust = max(0, min(100, rel.trust + d_trust))
        rel.fear = max(0, min(100, rel.fear + d_fear))
        rel.familiarity = max(0, min(100, rel.familiarity + d_familiarity))

        # Add Memory
        base_impact_score = data.get("base_impact", 0.0)
        if abs(base_impact_score) > 0:
            memory = MemoryRecord(
                timestamp=time.time(), # Game time would be better
                actor_id=other_id,
                action_type=data.get("type", "unknown"),
                impact=base_impact_score,
                permanent=False # Logic for trauma could go here
            )
            rel.memories.append(memory)
            # Trim memories
            if len(rel.memories) > 20:
                rel.memories.pop(0)

        logger.debug(f"Interaction {role}: Entity {subject_id} view of {other_id} -> Aff:{rel.affinity}, Trust:{rel.trust}")
