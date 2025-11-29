"""
Module defining the GossipSystem.
"""
from typing import List
from ...engine.ecs import System, World
from ..yukkuri_components import GossipQueue, GossipPacket, YukkuriStats
from ..components import Transform
from ..events import SocialInteractionEvent
from ...engine.event_bus import EventBus
import time
from ..services import TimeService

class GossipSystem(System):
    """
    System responsible for managing Gossip (witnessing and exchanging).
    """
    def __init__(self, event_bus: EventBus):
        super().__init__()
        self.event_bus = event_bus
        self.event_bus.subscribe(SocialInteractionEvent, self.on_social_interaction)

    def update(self, world: World, dt: float) -> None:
        pass

    def on_social_interaction(self, event: SocialInteractionEvent) -> None:
        """
        When interaction happens, check for witnesses.
        """
        if not hasattr(self, 'ecs_world'): return
        world = self.ecs_world

        actor_trans = world.get_component(event.initiator_id, Transform)
        if not actor_trans: return

        entities = world.get_entities_with(YukkuriStats, Transform, GossipQueue)

        time_service = world.services.try_get(TimeService)
        now = time_service.time_elapsed if time_service else time.time()

        for eid in entities:
            if eid == event.initiator_id or eid == event.target_id:
                continue

            witness_trans = world.get_component(eid, Transform)

            # Distance check (visual range e.g. 300)
            dist_sq = (witness_trans.x - actor_trans.x)**2 + (witness_trans.y - actor_trans.y)**2
            if dist_sq < 300*300:
                gossip = world.get_component(eid, GossipQueue)
                packet = GossipPacket(
                    target_id=event.initiator_id,
                    event_type=event.interaction_type,
                    value=0.0,
                    timestamp=now
                )
                gossip.priority_queue.append(packet)
                if len(gossip.priority_queue) > 3:
                     gossip.priority_queue.pop(0)
