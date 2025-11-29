"""
Module implementing the social system for Yukkuri interaction and relationship management.
Refactored for the "Clear-Cut" Personality & Social System.
"""
import math
import time
from typing import Optional, Dict, List, Any, Set
from collections import deque
from loguru import logger
import random
import heapq

from ...engine.ecs import System, World
from ...engine.event_bus import EventBus
from ..components import Transform
from ..yukkuri_components import (
    YukkuriStats, RelationshipRegistry, RelationshipData,
    MemoryRecord, Personality, GossipPacket, GossipQueue,
    EmotionalState
)
from ..trait_service import TraitService
from ..services import TimeService
from ..entity_factory import EntityFactory
from ..events import SocialInteractionEvent
from ...config import GameConfig

class SocialSystem(System):
    """
    System responsible for managing social relationships, interaction propagation (Sector System),
    Memory (Headline System), and Gossip.

    Attributes:
        trait_service (Optional[TraitService]): The service for accessing trait/interaction data.
        sector_size (int): Size of the sectors for broadcasting.
        event_bus (EventBus): The event bus.
        world_width (int): World width for sector calculation.
        world_height (int): World height for sector calculation.
    """

    def __init__(self, event_bus: EventBus):
        """
        Initializes the SocialSystem.

        Args:
            event_bus (EventBus): The global event bus.
        """
        super().__init__()
        self.trait_service: Optional[TraitService] = None
        self.event_bus = event_bus
        self.event_bus.subscribe(SocialInteractionEvent, self.on_social_interaction)

        # Sector System Configuration
        self.sector_size = 500 # Adjust based on typical map size/density
        self.world_width = 3000
        self.world_height = 3000

        self.initialized = False

        # Spatial Cache (Sector -> List[EntityID])
        self.sector_map: Dict[str, List[int]] = {}
        self.last_cache_update = 0.0
        self.cache_update_interval = 0.0 # Update every frame for now to fix test/ensure correctness, or check dt

    def _ensure_initialized(self, world: World):
        if self.initialized:
            return

        self.trait_service = world.services.try_get(TraitService)
        config = world.services.try_get(GameConfig)
        if config:
            self.world_width = config.world.width
            self.world_height = config.world.height

        self.initialized = True

    def update(self, world: World, dt: float) -> None:
        """
        Updates social states.
        Handles distributed cleanup of old relationships.
        Also updates Spatial Cache periodically.
        """
        self._ensure_initialized(world)

        time_service = world.services.try_get(TimeService)
        now = time_service.time_elapsed if time_service else time.time()

        # Force update for now to debug or use low interval
        if now - self.last_cache_update >= self.cache_update_interval:
            self._update_sector_map(world)
            self.last_cache_update = now

    def _update_sector_map(self, world: World):
        """
        Updates the spatial hash map.
        """
        self.sector_map.clear()
        count = 0
        for entity, (trans,) in world.get_components_tuple(Transform):
            sx = int(trans.x // self.sector_size)
            sy = int(trans.y // self.sector_size)
            key = f"{sx},{sy}"
            if key not in self.sector_map:
                self.sector_map[key] = []
            self.sector_map[key].append(entity)
            count += 1
        # print(f"DEBUG: Updated sector map with {count} entities. Keys: {self.sector_map.keys()}")

    def on_social_interaction(self, event: SocialInteractionEvent) -> None:
        """
        Event handler for social interactions.
        Triggers the Sector System broadcasting.

        Args:
            event (SocialInteractionEvent): The social interaction event.
        """
        if not hasattr(self, 'ecs_world'):
            return

        self._ensure_initialized(self.ecs_world)

        # 1. Process the direct interaction between Initiator and Target
        self._process_interaction(self.ecs_world, event.initiator_id, event.target_id, event.interaction_type)

        # 2. Broadcast to Witnesses (Sector System)
        self._broadcast_event(self.ecs_world, event)

    def _process_interaction(self, world: World, actor_id: int, target_id: int, interaction_name: str) -> None:
        """
        Handles the direct effect of an interaction (Opinion update, Memory creation).
        Also triggers Gossip Exchange if it's a "Talk" interaction.
        """
        if not self.trait_service:
            return

        interaction_data = self.trait_service.get_interaction(interaction_name)
        if not interaction_data:
            return

        time_service = world.services.try_get(TimeService)
        now = time_service.time_elapsed if time_service else time.time()

        # Apply impacts to the Target (how they view the Actor)
        self._apply_impact(world, target_id, actor_id, interaction_data, now)

        # Visual Feedback
        self._spawn_visual_feedback(world, target_id, interaction_name, interaction_data)

        # Gossip Exchange (if applicable)
        if interaction_name in ["Talk", "Chat", "Gossip"]:
            self._exchange_gossip(world, actor_id, target_id)

    def _broadcast_event(self, world: World, event: SocialInteractionEvent) -> None:
        """
        Broadcasts the event to entities in the same or adjacent sectors.
        """
        # Get Initiator Position
        transform = world.get_component(event.initiator_id, Transform)
        if not transform:
            return

        initiator_pos = (transform.x, transform.y)
        sector_x = int(initiator_pos[0] // self.sector_size)
        sector_y = int(initiator_pos[1] // self.sector_size)

        # Get entities from cached map
        nearby_entities = []
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                key = f"{sector_x+dx},{sector_y+dy}"
                if key in self.sector_map:
                    nearby_entities.extend(self.sector_map[key])

        # print(f"DEBUG: Broadcasting event from {sector_x},{sector_y}. Found neighbors: {len(nearby_entities)} in cache. Cache keys: {self.sector_map.keys()}")

        for witness_id in nearby_entities:
            if witness_id == event.initiator_id or witness_id == event.target_id:
                continue

            self._witness_event(world, witness_id, event)

    def _witness_event(self, world: World, witness_id: int, event: SocialInteractionEvent) -> None:
        """
        A witness observes an event.
        1. Form an opinion/memory? (Maybe, if significant).
        2. Generate Gossip Packet.
        """
        # Generate Gossip Packet
        # Impact needs to be retrieved from interaction data
        interaction_data = self.trait_service.get_interaction(event.interaction_type)
        if not interaction_data:
            return

        base_impact = interaction_data.get("base_impact", 0.0)

        # Threshold for gossip?
        if abs(base_impact) < 5.0:
            return

        time_service = world.services.try_get(TimeService)
        now = time_service.time_elapsed if time_service else time.time()

        packet = GossipPacket(
            timestamp=now,
            source_id=witness_id,
            subject_id=event.initiator_id,
            target_id=event.target_id,
            action_type=event.interaction_type,
            impact=base_impact
        )

        # Add to Witness's Gossip Queue
        gossip_queue = world.get_component(witness_id, GossipQueue)
        if not gossip_queue:
            gossip_queue = GossipQueue()
            world.add_component(witness_id, gossip_queue)

        # Add and Sort
        gossip_queue.queue.append(packet)
        # Sort using GossipPacket.__lt__ which is abs(impact) > abs(other.impact)
        # So "smaller" means "higher impact".
        # list.sort() sorts ascending (smallest first).
        # So high impact comes first.
        gossip_queue.queue.sort()

        if len(gossip_queue.queue) > 10:
            gossip_queue.queue = gossip_queue.queue[:10]

        # print(f"DEBUG: Witness {witness_id} added gossip. Queue len: {len(gossip_queue.queue)}")

    def _exchange_gossip(self, world: World, actor_id: int, target_id: int) -> None:
        """
        Exchanges top 3 gossip packets between two entities.
        """
        actor_queue = world.get_component(actor_id, GossipQueue)
        target_queue = world.get_component(target_id, GossipQueue)

        if not actor_queue or not target_queue:
            return

        # Actor shares with Target
        self._share_packets(actor_queue, target_queue, count=3)
        # Target shares with Actor
        self._share_packets(target_queue, actor_queue, count=3)

    def _share_packets(self, source_q: GossipQueue, dest_q: GossipQueue, count: int) -> None:
        shared = 0
        for packet in source_q.queue:
            if shared >= count:
                break

            # Check if packet already exists in dest
            exists = False
            for p in dest_q.queue:
                if (p.subject_id == packet.subject_id and
                    p.target_id == packet.target_id and
                    p.timestamp == packet.timestamp):
                    exists = True
                    break

            if not exists:
                dest_q.queue.append(packet)
                shared += 1

        # Re-sort destination
        dest_q.queue.sort() # Highest impact first (due to custom __lt__)
        if len(dest_q.queue) > 10:
            dest_q.queue = dest_q.queue[:10]

    def _apply_impact(self, world: World, subject_id: int, actor_id: int, data: Dict[str, Any], now: float) -> None:
        """
        Applies social impact: Memory creation + Opinion Update.
        Subject is the one forming the opinion (e.g., Target of a hit).
        Actor is the one who did the action.
        """
        registry = world.get_component(subject_id, RelationshipRegistry)
        if not registry:
            registry = RelationshipRegistry()
            world.add_component(subject_id, registry)

        if actor_id not in registry.relationships:
            registry.relationships[actor_id] = RelationshipData(last_update=now)

        rel = registry.relationships[actor_id]

        base_impact_score = data.get("base_impact", 0.0)
        action_type = data.get("type", "unknown") # e.g. "Physical", "Social"

        # Apply Behavioral Overrides (Lenses)
        subject_personality = world.get_component(subject_id, Personality)
        if subject_personality:
            base_impact_score = self._apply_trait_lenses(world, subject_id, actor_id, base_impact_score, subject_personality)

        # 1. Create Memory (Headline System)
        self._add_memory(rel, now, actor_id, action_type, base_impact_score)

        # 2. Recalculate Opinion
        self._recalculate_opinion(world, subject_id, actor_id, rel)

        # 3. Update Familiarity (always increases with interaction)
        rel.familiarity = min(100.0, rel.familiarity + 1.0)

        # 4. Immediate emotional reaction (EmotionalState)
        self._trigger_emotional_reaction(world, subject_id, base_impact_score)

    def _apply_trait_lenses(self, world: World, subject_id: int, actor_id: int, base_impact: float, personality: Personality) -> float:
        """
        Applies trait-based behavioral overrides (Lenses).
        """
        final_impact = base_impact

        # Check Traits
        for trait in personality.traits:
            if trait == "GESU": # Scum/Gesu
                if base_impact > 0:
                    final_impact *= 0.5
            elif trait == "NICE":
                if base_impact > 0:
                    final_impact *= 1.5
                elif base_impact < 0:
                    final_impact *= 0.8

        return final_impact

    def _add_memory(self, rel: RelationshipData, now: float, actor_id: int, action_type: str, impact: float) -> None:
        """
        Adds a memory to the appropriate buffer (Trivial vs Core) with Locking logic.
        """
        # Threshold for Core Memory
        CORE_THRESHOLD = 20.0
        MAX_CORE_MEMORIES = 35

        is_core = abs(impact) >= CORE_THRESHOLD

        is_locked = False
        if abs(impact) >= 80.0:
            is_locked = True

        memory = MemoryRecord(
            timestamp=now,
            actor_id=actor_id,
            action_type=action_type,
            impact=impact,
            description=f"{action_type} ({impact})",
            is_locked=is_locked
        )

        if is_core:
            if len(rel.core_memories) < MAX_CORE_MEMORIES:
                rel.core_memories.append(memory)
            else:
                # Buffer full. Try to replace an unlocked memory.
                replaced = False
                for i, mem in enumerate(rel.core_memories):
                    if not mem.is_locked:
                        rel.core_memories[i] = memory
                        replaced = True
                        break

                if not replaced:
                    # All are locked.
                    pass
        else:
            rel.trivial_events.append(memory)

    def _recalculate_opinion(self, world: World, subject_id: int, target_id: int, rel: RelationshipData) -> None:
        """
        Opinion = Base Compatibility + Sum(CoreMemories) + Sum(TrivialEvents)
        """
        # 1. Base Compatibility
        base = self._calculate_base_compatibility(world, subject_id, target_id)

        # 2. Sum Memories
        core_sum = sum(m.impact for m in rel.core_memories)
        trivial_sum = sum(m.impact for m in rel.trivial_events)

        total_score = base + core_sum + trivial_sum

        rel.affinity = max(-100, min(100, total_score))

        if total_score > 0:
            rel.trust = min(100, total_score)
            rel.fear = 0
        else:
            rel.trust = 0
            rel.fear = min(100, abs(total_score))

    def _calculate_base_compatibility(self, world: World, subject_id: int, target_id: int) -> float:
        """
        Calculated from Personality Axis comparison.
        """
        p1 = world.get_component(subject_id, Personality)
        p2 = world.get_component(target_id, Personality)

        if not p1 or not p2:
            return 0.0

        score = 0.0

        # Similarity Bonus
        score += 20 if abs(p1.kindness - p2.kindness) < 50 else -10
        score += 10 if abs(p1.energy - p2.energy) < 50 else -5

        if p1.greed > 50 and p2.greed > 50:
            score -= 30

        return score

    def _trigger_emotional_reaction(self, world: World, entity_id: int, impact: float) -> None:
        """
        Adjusts EmotionalState based on impact.
        """
        emo = world.get_component(entity_id, EmotionalState)
        if not emo:
            return

        # Impact > 0 -> Happiness
        # Impact < 0 -> Stress + Sadness

        if impact > 0:
            emo.happiness = min(100, emo.happiness + impact)
            emo.stress = max(0, emo.stress - (impact * 0.5))
        else:
            emo.happiness = max(-100, emo.happiness + impact) # Impact is negative
            emo.stress = min(100, emo.stress + abs(impact))

        # Sync to YukkuriStats (deprecated fields)
        stats = world.get_component(entity_id, YukkuriStats)
        if stats:
            stats.happiness = emo.happiness
            stats.stress = emo.stress

    def _spawn_visual_feedback(self, world: World, entity_id: int, interaction_name: str, data: Dict[str, Any]) -> None:
        """
        Spawns floating text or icons.
        """
        factory = world.services.try_get(EntityFactory)
        if not factory:
            return

        trans = world.get_component(entity_id, Transform)
        if not trans:
            return

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

        if base_impact < -10:
             text = "T_T"
             color = (100, 100, 255)

        fx = trans.x + random.uniform(-10, 10)
        fy = trans.y - 30

        factory.create_floating_text(fx, fy, text, color, size=24, lifetime=1.5)
