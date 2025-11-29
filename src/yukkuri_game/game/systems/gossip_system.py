"""
Module defining the GossipSystem.
"""
from typing import List, Tuple, Optional
import pymunk
from ...engine.ecs import System, World
from ..yukkuri_components import GossipQueue, GossipPacket, YukkuriStats
from ..components import Transform, PhysicsBody
from ..events import SocialInteractionEvent
from ...engine.event_bus import EventBus
import time
from ..services import TimeService
from .physics import PhysicsSystem
import math

class GossipSystem(System):
    """
    System responsible for managing Gossip (witnessing and exchanging).
    Uses PhysicsSystem spatial queries for efficient witnessing.
    """

    def __init__(self, event_bus: EventBus):
        super().__init__()
        self.event_bus = event_bus
        self.event_bus.subscribe(SocialInteractionEvent, self.on_social_interaction)
        self.physics_system: Optional[PhysicsSystem] = None

    def update(self, world: World, dt: float) -> None:
        if not self.physics_system:
            self.physics_system = world.services.try_get(PhysicsSystem)

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
        # Use Pymunk Point Query
        if not self.physics_system:
             self.physics_system = world.services.try_get(PhysicsSystem)

        if self.physics_system and self.physics_system.space:
             self._process_witnesses_spatial(world, event, actor_trans, now)
        else:
             # Fallback if physics system not ready (shouldn't happen in normal gameplay)
             pass

    def _process_witnesses_spatial(self, world: World, event: SocialInteractionEvent, actor_trans: Transform, now: float):
        """
        Uses spatial query to find witnesses.
        """
        visual_range = 300.0

        # Pymunk query: query for shapes within visual_range of the actor
        point = (actor_trans.x, actor_trans.y)
        results = self.physics_system.space.point_query(point, visual_range, pymunk.ShapeFilter())

        for shape_query_info in results:
            shape = shape_query_info.shape
            body = shape.body
            if not body or not body.userdata:
                continue

            witness_id = body.userdata

            # Entity ID must be int
            if not isinstance(witness_id, int):
                continue

            if witness_id == event.initiator_id or witness_id == event.target_id:
                continue

            # Must have GossipQueue and YukkuriStats
            if not world.has_component(witness_id, GossipQueue) or not world.has_component(witness_id, YukkuriStats):
                continue

            # TODO: LOS Check could go here

            # Add Witness Gossip
            self._add_witness_gossip(world, witness_id, event, now, value=10.0)

    def _exchange_gossip(self, world: World, sender_id: int, receiver_id: int):
        sender_queue = world.get_component(sender_id, GossipQueue)
        receiver_queue = world.get_component(receiver_id, GossipQueue)

        if not sender_queue or not receiver_queue:
            return

        # Get Max Gossip Length from Config
        from ...config import GameConfig
        config = world.services.try_get(GameConfig)
        max_length = 10
        if config and hasattr(config.rules, 'social'):
            max_length = config.rules.social.max_gossip_length

        # Share top packets
        for packet in sender_queue.priority_queue:
            # Don't share gossip about the receiver to the receiver
            if packet.target_id == receiver_id:
                continue

            new_packet = GossipPacket(
                target_id=packet.target_id,
                event_type=packet.event_type,
                value=packet.value * 0.9,
                timestamp=packet.timestamp
            )
            receiver_queue.add_packet(new_packet, max_length=max_length)

    def _add_witness_gossip(self, world: World, witness_id: int, event: SocialInteractionEvent, now: float, value: float):
        gossip = world.get_component(witness_id, GossipQueue)
        if not gossip: return

        # Get Max Gossip Length from Config
        from ...config import GameConfig
        config = world.services.try_get(GameConfig)
        max_length = 10
        if config and hasattr(config.rules, 'social'):
            max_length = config.rules.social.max_gossip_length

        packet = GossipPacket(
            target_id=event.initiator_id,
            event_type=event.interaction_type,
            value=value,
            timestamp=now
        )
        gossip.add_packet(packet, max_length=max_length)
