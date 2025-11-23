from typing import TYPE_CHECKING, List, Optional
from loguru import logger

from ...engine.ecs import World, System
from ..yukkuri_components import Personality, RelationshipRegistry, RelationshipData, MemoryRecord, YukkuriStats
from ..components import Transform
from ..services import TraitService
from ..game_manager import GameManager
from ..events import EntitySoldEvent, EntityTrainedEvent, EntityPunishedEvent

if TYPE_CHECKING:
    from ...engine.event_bus import EventBus

class SocialSystem(System):
    """
    System responsible for managing social interactions, relationships, and memories.
    """
    def __init__(self, world: World):
        super().__init__(world)
        self.trait_service = world.services.try_get(TraitService)
        # We might want to subscribe to events here if ECS supports it, or poll interactions
        # For now, let's assume interactions are triggered by AI or Input and we process the consequences.
        # But we need a way to invoke interaction logic.

        # Also handle decay.

    def update(self, dt: float) -> None:
        """
        Updates relationships (decay) and processes social queue if any.
        """
        # Decay logic could be expensive if run every frame for every relationship.
        # Maybe run it periodically or only on access?
        # The plan says: "Do not iterate all relationships to apply decay every tick. Apply decay calculation only when the relationship is accessed or modified"
        # So we won't do global decay loop here.
        pass

    def process_interaction(self, actor_id: int, target_id: int, interaction_type: str):
        """
        Processes a social interaction between two entities.
        """
        if not self.trait_service:
            self.trait_service = self.world.services.try_get(TraitService)
            if not self.trait_service:
                return

        interaction_def = self.trait_service.get_interaction(interaction_type)
        if not interaction_def:
            logger.warning(f"Unknown interaction type: {interaction_type}")
            return

        # Get Components
        actor_rels = self.world.get_component(actor_id, RelationshipRegistry)
        target_rels = self.world.get_component(target_id, RelationshipRegistry)
        actor_pers = self.world.get_component(actor_id, Personality)
        target_pers = self.world.get_component(target_id, Personality)
        actor_stats = self.world.get_component(actor_id, YukkuriStats)
        target_stats = self.world.get_component(target_id, YukkuriStats)

        if not (actor_rels and target_rels and actor_pers and target_pers):
            return

        # Apply immediate impacts (Happiness, Stress, etc.)
        base_impact = interaction_def.get("base_impact", 0.0)
        # TODO: Modifiers based on Actor traits? e.g. "Strong" actor hits harder?

        # Apply Social Impact to Target's view of Actor
        social_impact = interaction_def.get("social_impact", {})
        self._update_relationship(target_id, actor_id, social_impact, interaction_type, base_impact, target_pers, actor_pers)

        # Apply Social Impact to Actor's view of Target (maybe different?)
        # For now, let's assume interactions are symmetric in acknowledgement but asymmetric in effect.
        # e.g. If I hit you, you hate me. Do I hate you? Maybe less so, or maybe I feel guilty?
        # The data definition mainly describes the effect on the Receiver (Target) or the relationship generally?
        # "social_impact = { affinity = -10.0 }" implies affinity goes down.
        # Usually implies Target's affinity towards Actor goes down.

    def _update_relationship(self, subject_id: int, object_id: int, impact_data: dict, interaction_type: str, raw_impact: float, subject_pers: Personality, object_pers: Personality):
        """
        Updates Subject's relationship with Object.
        """
        registry = self.world.get_component(subject_id, RelationshipRegistry)
        if not registry:
            return

        if object_id not in registry.relationships:
            registry.relationships[object_id] = RelationshipData()

        rel = registry.relationships[object_id]

        # Calculate Decay since last update?
        # For now, we just apply delta.

        # Base changes
        d_affinity = impact_data.get("affinity", 0.0)
        d_trust = impact_data.get("trust", 0.0)
        d_fear = impact_data.get("fear", 0.0)

        # Apply Modifiers based on Subject's Traits (e.g. "Forgiving", "Paranoid")
        # And Object's Traits (e.g. "Scary", "Cute")
        # The interactions.toml has modifiers like "trait:WEAK" -> fear += 15

        # We need to look up modifiers in the interaction definition passed down?
        # I should have passed the interaction definition or fetched it again.
        # Let's fetch it again or pass it.
        interaction_def = self.trait_service.get_interaction(interaction_type)
        modifiers = interaction_def.get("modifiers", {})

        # Check Subject Traits (e.g. "I am Cowardly, so I fear more")
        # The key syntax in TOML was "trait:WEAK". Is that Subject or Object?
        # "If the victim is "Weak", fear increases more" -> Subject is victim in this context (Target of interaction).
        # So we check Subject's traits.
        for trait in subject_pers.traits:
            key = f"trait:{trait}"
            if key in modifiers:
                mod = modifiers[key]
                d_affinity += mod.get("affinity", 0.0)
                d_trust += mod.get("trust", 0.0)
                d_fear += mod.get("fear", 0.0)

        # What about Object traits? "If Attacker is Scary..."
        # Maybe syntax "target_trait:SCARY"?
        # For now stick to the plan's example which seemed to imply Victim's traits affecting the outcome on themselves.

        rel.affinity = max(-100.0, min(100.0, rel.affinity + d_affinity))
        rel.trust = max(0.0, min(100.0, rel.trust + d_trust))
        rel.fear = max(0.0, min(100.0, rel.fear + d_fear))

        # Add Memory
        # Only if impact is significant?
        if abs(raw_impact) > 5.0 or abs(d_affinity) > 5.0:
            import time
            rel.memories.append(MemoryRecord(
                timestamp=time.time(), # Use game time if possible?
                actor_id=object_id,
                action_type=interaction_type,
                impact=raw_impact
            ))
            # Limit memories
            if len(rel.memories) > 50:
                rel.memories.pop(0)

class FamilyManager:
    """
    Manages family groups and logic.
    """
    pass
