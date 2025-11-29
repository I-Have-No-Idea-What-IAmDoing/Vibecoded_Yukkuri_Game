"""
Module defining the GossipSystem.
"""
from typing import List, Tuple
from ...engine.ecs import System, World
from ..yukkuri_components import GossipQueue, GossipPacket, YukkuriStats
from ..components import Transform
from ..events import SocialInteractionEvent
from ...engine.event_bus import EventBus
import time
from ..services import TimeService
import math

class GossipSystem(System):
    """
    System responsible for managing Gossip (witnessing and exchanging).
    """
    SECTOR_SIZE = 1000  # Assuming world is large, e.g. 4000x4000, 4x4 grid -> 1000 per sector

    def __init__(self, event_bus: EventBus):
        super().__init__()
        self.event_bus = event_bus
        self.event_bus.subscribe(SocialInteractionEvent, self.on_social_interaction)

    def update(self, world: World, dt: float) -> None:
        pass

    def _get_sector(self, x: float, y: float) -> Tuple[int, int]:
        return (int(x // self.SECTOR_SIZE), int(y // self.SECTOR_SIZE))

    def _get_adjacent_sectors(self, sector: Tuple[int, int]) -> List[Tuple[int, int]]:
        x, y = sector
        sectors = []
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                sectors.append((x + dx, y + dy))
        return sectors

    def on_social_interaction(self, event: SocialInteractionEvent) -> None:
        """
        When interaction happens, check for witnesses.
        """
        if not hasattr(self, 'ecs_world'): return
        world = self.ecs_world

        actor_trans = world.get_component(event.initiator_id, Transform)
        if not actor_trans: return

        time_service = world.services.try_get(TimeService)
        now = time_service.time_elapsed if time_service else time.time()

        # Handle Gossip Exchange (Talking)
        if event.interaction_type in ["Talk", "Greet", "Chat"]:
            self._exchange_gossip(world, event.initiator_id, event.target_id)
            self._exchange_gossip(world, event.target_id, event.initiator_id)

        # Handle Witnessing (Visual/Auditory)
        entities = world.get_entities_with(YukkuriStats, Transform, GossipQueue)

        actor_sector = self._get_sector(actor_trans.x, actor_trans.y)
        nearby_sectors = self._get_adjacent_sectors(actor_sector)

        for eid in entities:
            if eid == event.initiator_id or eid == event.target_id:
                continue

            witness_trans = world.get_component(eid, Transform)
            witness_sector = self._get_sector(witness_trans.x, witness_trans.y)

            # Optimization: Only check witnesses in same or adjacent sectors
            if witness_sector not in nearby_sectors:
                continue

            # Visual Check (LOS/Distance)
            dist_sq = (witness_trans.x - actor_trans.x)**2 + (witness_trans.y - actor_trans.y)**2
            visual_range = 300.0

            # TODO: Line of sight check would go here. For now, distance.
            if dist_sq < visual_range * visual_range:
                self._add_witness_gossip(world, eid, event, now, value=10.0) # Base value

    def _exchange_gossip(self, world: World, sender_id: int, receiver_id: int):
        sender_queue = world.get_component(sender_id, GossipQueue)
        receiver_queue = world.get_component(receiver_id, GossipQueue)

        if not sender_queue or not receiver_queue:
            return

        # Share top packets
        for packet in sender_queue.priority_queue:
            # Don't share gossip about the receiver to the receiver (unless intended?)
            # Usually we share "Hey did you know X did Y?"
            if packet.target_id == receiver_id:
                continue

            # Create a copy or new packet to avoid reference issues
            new_packet = GossipPacket(
                target_id=packet.target_id,
                event_type=packet.event_type,
                value=packet.value * 0.9, # Decay value slightly on transmission?
                timestamp=packet.timestamp
            )
            receiver_queue.add_packet(new_packet)

    def _add_witness_gossip(self, world: World, witness_id: int, event: SocialInteractionEvent, now: float, value: float):
        gossip = world.get_component(witness_id, GossipQueue)
        if not gossip: return

        packet = GossipPacket(
            target_id=event.initiator_id,
            event_type=event.interaction_type,
            value=value, # Value should depend on event severity
            timestamp=now
        )
        gossip.add_packet(packet)
