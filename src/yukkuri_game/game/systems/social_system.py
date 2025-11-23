from typing import TYPE_CHECKING, List, Optional, Dict
from loguru import logger
import time

from ...engine.ecs import World, System
from ..yukkuri_components import Personality, RelationshipRegistry, RelationshipData, MemoryRecord, YukkuriStats
from ..components import Transform
from ..services import TraitService, TimeService
from ..game_manager import GameManager
from ..events import EntitySoldEvent, EntityTrainedEvent, EntityPunishedEvent, RelationshipChangedEvent
from ...engine.event_bus import EventBus

class SocialSystem(System):
    """
    System responsible for managing social interactions, relationships, and memories.
    """
    def __init__(self, world: World):
        super().__init__()

        self.ecs_world = world
        self.world = world
        self.trait_service = world.services.try_get(TraitService)
        self.event_bus = world.services.try_get(EventBus)
        self.time_service = world.services.try_get(TimeService)
        self.family_manager = FamilyManager(world)

    def update(self, dt: float) -> None:
        """
        Updates relationships (decay) and processes social queue if any.
        """
        pass

    def process_interaction(self, actor_id: int, target_id: int, interaction_type: str):
        """
        Processes a social interaction between two entities.
        """
        if not self.trait_service:
            self.trait_service = self.world.services.try_get(TraitService)
            if not self.trait_service:
                logger.warning("TraitService missing in SocialSystem")
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

        # Note: We removed strict YukkuriStats check because maybe not all entities have it (e.g. Items?)
        # But plan assumes Yukkuri interaction.
        # Let's allow it if Stats are missing, or check properly.
        # The test adds YukkuriStats.
        # Let's log what is missing.

        if not actor_rels: logger.warning(f"Actor {actor_id} missing RelationshipRegistry")
        if not target_rels: logger.warning(f"Target {target_id} missing RelationshipRegistry")
        if not actor_pers: logger.warning(f"Actor {actor_id} missing Personality")
        if not target_pers: logger.warning(f"Target {target_id} missing Personality")

        if not (actor_rels and target_rels and actor_pers and target_pers):
            return

        # Apply immediate impacts (Happiness, Stress, etc.)
        base_impact = interaction_def.get("base_impact", 0.0)

        # Apply Social Impact to Target's view of Actor
        social_impact = interaction_def.get("social_impact", {})
        self._update_relationship(target_id, actor_id, social_impact, interaction_type, base_impact, target_pers, actor_pers)

        # Family Logic hooks
        can_recruit = interaction_def.get("can_recruit_family", False)
        if can_recruit:
            self.family_manager.try_family_recruit(actor_id, target_id)

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

        old_affinity = rel.affinity

        # Base changes
        d_affinity = impact_data.get("affinity", 0.0)
        d_trust = impact_data.get("trust", 0.0)
        d_fear = impact_data.get("fear", 0.0)

        # Fetch modifiers
        interaction_def = self.trait_service.get_interaction(interaction_type)
        modifiers = interaction_def.get("modifiers", {}) if interaction_def else {}

        # Check Subject Traits
        for trait in subject_pers.traits:
            key = f"trait:{trait}"
            if key in modifiers:
                mod = modifiers[key]
                d_affinity += mod.get("affinity", 0.0)
                d_trust += mod.get("trust", 0.0)
                d_fear += mod.get("fear", 0.0)

        rel.affinity = max(-100.0, min(100.0, rel.affinity + d_affinity))
        rel.trust = max(0.0, min(100.0, rel.trust + d_trust))
        rel.fear = max(0.0, min(100.0, rel.fear + d_fear))

        # Add Memory
        if abs(raw_impact) > 5.0 or abs(d_affinity) > 5.0:
            current_time = self.time_service.time_elapsed if self.time_service else time.time()
            rel.memories.append(MemoryRecord(
                timestamp=current_time,
                actor_id=object_id,
                action_type=interaction_type,
                impact=raw_impact
            ))
            if len(rel.memories) > 50:
                rel.memories.pop(0)

        # Check for significant shift
        if abs(rel.affinity - old_affinity) > 10.0:
            change_type = "positive" if rel.affinity > old_affinity else "negative"
            subject_trans = self.world.get_component(subject_id, Transform)
            pos = (subject_trans.x, subject_trans.y) if subject_trans else (0, 0)

            if self.event_bus:
                self.event_bus.publish(RelationshipChangedEvent(
                    subject_id=subject_id,
                    target_id=object_id,
                    change_type=change_type,
                    position=pos
                ))

class FamilyManager:
    """
    Manages family groups and logic.
    """
    def __init__(self, world: World):
        self.world = world
        self.next_group_id = 1

    def create_family(self, members: List[int]) -> int:
        """Creates a new family group."""
        group_id = self.next_group_id
        self.next_group_id += 1

        for entity_id in members:
            registry = self.world.get_component(entity_id, RelationshipRegistry)
            if registry:
                registry.family_group_id = group_id

        return group_id

    def add_to_family(self, entity_id: int, group_id: int):
        """Adds an entity to a family group."""
        registry = self.world.get_component(entity_id, RelationshipRegistry)
        if registry:
            registry.family_group_id = group_id

    def try_family_recruit(self, recruiter_id: int, target_id: int):
        """
        Attempt to recruit target into recruiter's family.
        """
        recruiter_rels = self.world.get_component(recruiter_id, RelationshipRegistry)
        target_rels = self.world.get_component(target_id, RelationshipRegistry)

        if not recruiter_rels or not target_rels:
            return

        # Check affinity
        recruiter_view = recruiter_rels.relationships.get(target_id)
        target_view = target_rels.relationships.get(recruiter_id)

        if not recruiter_view or not target_view:
            return

        if recruiter_view.affinity > 50 and target_view.affinity > 50:
            # Form family or join
            if recruiter_rels.family_group_id is None and target_rels.family_group_id is None:
                # New family
                self.create_family([recruiter_id, target_id])
                logger.info(f"New family formed: {recruiter_id} and {target_id}")
            elif recruiter_rels.family_group_id is not None and target_rels.family_group_id is None:
                # Join recruiter
                self.add_to_family(target_id, recruiter_rels.family_group_id)
                logger.info(f"{target_id} joined family {recruiter_rels.family_group_id}")
