import math
import time
from typing import Optional, Dict, List, Tuple
from loguru import logger
import random

from ...engine.ecs import System, World
from ...engine.event_bus import EventBus
from ..components import Transform
from ..yukkuri_components import (
    YukkuriStats, RelationshipRegistry, RelationshipData, MemoryRecord, Personality,
    GossipQueue, GossipPacket
)
from ..trait_service import TraitService
from ..entity_factory import EntityFactory
from ..events import SocialInteractionEvent
from ..ai.navigation_service import NavigationService

class SocialSystem(System):
    """
    System responsible for managing social relationships, memory decay, and applying interaction effects.
    """

    def __init__(self, event_bus: EventBus):
        super().__init__()
        self.trait_service: Optional[TraitService] = None
        # Distributed cleanup state
        self.cleanup_index = 0
        self.cleanup_batch_size = 10
        self.event_bus = event_bus

        # Sector System
        self.sector_grid_size = 4 # 4x4 grid
        self.world_dims = (3000, 3000) # Fallback, should update from config

        self.event_bus.subscribe(SocialInteractionEvent, self.on_social_interaction)

    def update(self, world: World, dt: float) -> None:
        """
        Updates social states.
        Handles distributed cleanup of old relationships and Mood decay.
        """
        if not self.trait_service:
            self.trait_service = world.services.try_get(TraitService)
            # Try to get world dimensions from NavigationService if available
            nav = world.services.try_get(NavigationService)
            if nav:
                self.world_dims = (nav.world_width, nav.world_height)

        # 1. Mood Decay (for all entities, but this is lighter than relationship map iteration)
        # Ideally, this should also be distributed or event-driven, but for now we iterate stats
        # to decay mood score.
        entities_with_personality = world.get_entities_with(Personality)
        for entity in entities_with_personality:
            pers = world.get_component(entity, Personality)
            if pers.mood_score > 0:
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
                cutoff = now - 600 # 10 minutes retention for inactive relationships

                for other_id, rel_data in registry.relationships.items():
                    # If not permanent (family/mate) and old
                    # (Mate/Family logic usually kept elsewhere or flagged, assuming ID check is enough)
                    is_special = (other_id == registry.mate_id) or \
                                 (registry.family_group_id is not None and \
                                  world.has_component(other_id, RelationshipRegistry) and \
                                  world.get_component(other_id, RelationshipRegistry).family_group_id == registry.family_group_id)

                    if not is_special and (now - rel_data.last_update > cutoff):
                        to_remove.append(other_id)

                for rid in to_remove:
                    del registry.relationships[rid]

        self.cleanup_index = (self.cleanup_index + self.cleanup_batch_size) % max(1, count)

    def _get_sector(self, x: float, y: float) -> Tuple[int, int]:
        """Calculates sector coordinates for a given position."""
        w, h = self.world_dims
        sx = int(x / (w / self.sector_grid_size))
        sy = int(y / (h / self.sector_grid_size))
        return (max(0, min(self.sector_grid_size - 1, sx)),
                max(0, min(self.sector_grid_size - 1, sy)))

    def _get_entities_in_sectors(self, world: World, sectors: List[Tuple[int, int]]) -> List[int]:
        """Retrieves all entities within the specified sectors."""
        candidates = []
        # Optimization: A spatial partition grid component would be better than iterating all transforms.
        # But for now, we iterate.
        # world.get_components(Transform) returns Dict[int, Transform], not List[Tuple[int, Transform]]
        # Iterate over items() to get (entity_id, component)
        for entity, transform in world.get_components(Transform).items():
            s_coords = self._get_sector(transform.x, transform.y)
            if s_coords in sectors:
                candidates.append(entity)
        return candidates

    def _broadcast_event(self, world: World, origin_entity: int, event_type: str, data: Dict):
        """
        Broadcasts visual/auditory events to relevant sectors.
        """
        origin_trans = world.get_component(origin_entity, Transform)
        if not origin_trans:
            return

        origin_sector = self._get_sector(origin_trans.x, origin_trans.y)
        sx, sy = origin_sector

        # Determine adjacent sectors
        adjacent_sectors = []
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                nx, ny = sx + dx, sy + dy
                if 0 <= nx < self.sector_grid_size and 0 <= ny < self.sector_grid_size:
                    adjacent_sectors.append((nx, ny))

        # Determine broadcast scope based on event type
        is_loud = data.get("loud", False)
        is_visual = data.get("visual", True) # Most interactions are visual

        target_sectors = []
        if is_loud == "very":
            target_sectors = adjacent_sectors # All adjacent
        elif is_loud: # Normal loud (same sector + adjacent maybe? Spec says "same sector (loud) or adjacent (very loud)")
             # Logic from spec: "Broadcast to same sector (loud) or adjacent (very loud)"
             # I interpret "Loud" as Same Sector, "Very Loud" as Adjacent.
             target_sectors = [origin_sector]
        elif is_visual:
             # Spec: "Broadcast only to entities in the same or adjacent sectors who have Line-of-Sight"
             target_sectors = adjacent_sectors

        potential_witnesses = self._get_entities_in_sectors(world, target_sectors)

        for witness_id in potential_witnesses:
            if witness_id == origin_entity:
                continue

            # Line of Sight check (Simplified distance check for now)
            witness_trans = world.get_component(witness_id, Transform)
            dist = math.hypot(witness_trans.x - origin_trans.x, witness_trans.y - origin_trans.y)

            # Visual Limit
            if is_visual and dist > 400: # Arbitrary visual range
                continue

            # Auditory Limit
            if not is_visual and dist > 800 and is_loud != "very":
                 continue

            # Process Witness
            self._process_witness(world, witness_id, origin_entity, data)

    def _process_witness(self, world: World, witness_id: int, actor_id: int, data: Dict):
        """
        Witness generates a Gossip Packet.
        """
        # Create Gossip Packet
        gossip = GossipPacket(
            source_id=actor_id,
            target_id=data.get("target_id", -1), # Who was the actor interacting with?
            content=data.get("interaction_name", "Unknown"),
            timestamp=time.time(),
            impact=data.get("base_impact", 0.0)
        )

        # Add to Witness's Outgoing Queue
        if not world.has_component(witness_id, GossipQueue):
            world.add_component(witness_id, GossipQueue())

        queue_comp = world.get_component(witness_id, GossipQueue)
        queue_comp.queue.insert(0, gossip)
        if len(queue_comp.queue) > 10: # Keep top 10 recent rumors
            queue_comp.queue.pop()

    def on_social_interaction(self, event: SocialInteractionEvent) -> None:
        """
        Event handler for social interactions.
        """
        # We need access to the world. System has self.ecs_world injected by World.add_system
        if not hasattr(self, 'ecs_world'):
            # Should be set by World when system added
            return

        self.register_interaction(self.ecs_world, event.initiator_id, event.target_id, event.interaction_type)

    def _update_relationship_decay(self, rel_data: RelationshipData):
        """
        Lazily updates relationship values based on time elapsed since last update.
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

    def _exchange_gossip(self, world: World, actor_id: int, target_id: int):
        """
        Exchanges top 3 gossip packets between two entities.
        """
        if not world.has_component(actor_id, GossipQueue) or not world.has_component(target_id, GossipQueue):
            return

        q1 = world.get_component(actor_id, GossipQueue).queue
        q2 = world.get_component(target_id, GossipQueue).queue

        # Share top 3
        to_share_1 = q1[:3]
        to_share_2 = q2[:3]

        # Simple merge: Add if not present (simplified check by timestamp/source)
        for gossip in to_share_1:
            if gossip not in q2:
                q2.insert(0, gossip)

        for gossip in to_share_2:
             if gossip not in q1:
                 q1.insert(0, gossip)

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
            logger.warning(f"Unknown interaction: {interaction_name}")
            return

        # Gossip Exchange (Viral Propagation)
        if interaction_name == "Talk":
            self._exchange_gossip(world, actor_id, target_id)

        # Apply impacts
        self._apply_impact(world, actor_id, target_id, interaction_data, role="actor")
        self._apply_impact(world, target_id, actor_id, interaction_data, role="target")

        # Broadcast Event (Witness Logic)
        broadcast_data = interaction_data.copy()
        broadcast_data["interaction_name"] = interaction_name
        broadcast_data["target_id"] = target_id
        # Define visual/auditory nature
        if interaction_name in ["Talk", "Greet"]:
             broadcast_data["loud"] = False
             broadcast_data["visual"] = False # Mostly auditory
        elif interaction_name in ["Fight", "Hit"]:
             broadcast_data["loud"] = True
             broadcast_data["visual"] = True

        self._broadcast_event(world, actor_id, interaction_name, broadcast_data)

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
                locked=False
            )

            # Determine buffer
            is_trivial = abs(base_impact_score) < 15 and not memory.locked

            if is_trivial:
                rel.trivial_memories.append(memory)
                if len(rel.trivial_memories) > 25:
                    rel.trivial_memories.pop(0)
            else:
                # Check for space in Core Memories
                if len(rel.core_memories) < 35:
                     rel.core_memories.append(memory)
                else:
                    # Find a non-locked memory to replace
                    replaced = False
                    for i, mem in enumerate(rel.core_memories):
                        if not mem.locked and abs(mem.impact) < abs(memory.impact):
                            rel.core_memories[i] = memory
                            replaced = True
                            break
                    # If all locked or more important, we discard the new one (or it's just not core enough)
                    # For now, let's just append and pop 0 if not locked, effectively treating it as a buffer
                    # if we didn't find a weak slot.
                    if not replaced:
                        # Fallback: simple FIFO for unlocked memories?
                        # Or maybe we just discard it?
                        pass

        logger.debug(f"Interaction {role}: Entity {subject_id} view of {other_id} -> Aff:{rel.affinity:.1f}, Trust:{rel.trust:.1f}")
