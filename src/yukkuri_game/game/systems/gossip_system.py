"""
Module defining the GossipSystem.
"""

import pymunk
from ...engine.ecs import System, World
from ..yukkuri_components import (
    GossipQueue,
    GossipPacket,
    YukkuriStats,
    RelationshipRegistry,
)
from ..components import Transform
from ..events import SocialInteractionEvent
from ...engine.event_bus import EventBus
import time
from ..services import TimeService
from .physics import PhysicsSystem
from .sector_system import SectorMap
from ..trait_service import TraitService
import math


class GossipSystem(System):
    """
    System responsible for managing Gossip (witnessing and exchanging).
    Uses SectorMap for efficient witnessing.

    Attributes:
        event_bus (EventBus): The event bus instance.
        physics_system (Optional[PhysicsSystem]): The physics system instance.
        sector_map (Optional[SectorMap]): The sector map instance.
        trait_service (Optional[TraitService]): The trait service instance.
    """

    def __init__(self, event_bus: EventBus):
        """
        Initializes the GossipSystem.

        Args:
            event_bus (EventBus): The event bus instance.
        """
        super().__init__()
        self.event_bus = event_bus
        self.event_bus.subscribe(SocialInteractionEvent, self.on_social_interaction)
        self.physics_system: PhysicsSystem | None = None
        self.sector_map: SectorMap | None = None
        self.trait_service: TraitService | None = None

    def update(self, world: World, dt: float) -> None:
        """
        Updates the system.
        Lazily fetches dependencies.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.
        """
        if not self.physics_system:
            self.physics_system = world.services.try_get(PhysicsSystem)
        if not self.sector_map:
            self.sector_map = world.services.try_get(SectorMap)
        if not self.trait_service:
            self.trait_service = world.services.try_get(TraitService)

    def on_social_interaction(self, event: SocialInteractionEvent) -> None:
        """
        Handles SocialInteractionEvent to trigger gossip and witnessing.

        Args:
            event (SocialInteractionEvent): The interaction event.
        """
        if not hasattr(self, "ecs_world"):
            return
        world = self.ecs_world

        actor_trans = world.get_component(event.initiator_id, Transform)
        if not actor_trans:
            return

        time_service = world.services.try_get(TimeService)
        now = time_service.time_elapsed if time_service else time.time()

        # Handle Gossip Exchange (Talking)
        if event.interaction_type in ["Talk", "Greet", "Chat"]:
            self._exchange_gossip(world, event.initiator_id, event.target_id)
            self._exchange_gossip(world, event.target_id, event.initiator_id)

        # Handle Witnessing (Sector-based)
        if not self.sector_map:
            self.sector_map = world.services.try_get(SectorMap)

        if self.sector_map:
            self._process_witnesses_sector(world, event, actor_trans, now)

    def _process_witnesses_sector(
        self,
        world: World,
        event: SocialInteractionEvent,
        actor_trans: Transform,
        now: float,
    ) -> None:
        """
        Processes potential witnesses in relevant sectors.

        Args:
            world (World): The ECS World.
            event (SocialInteractionEvent): The event data.
            actor_trans (Transform): The transform of the actor.
            now (float): Current timestamp.
        """
        if not self.sector_map:
            return

        range_type = "visual"

        # Determine range type from TraitService if available
        if not self.trait_service:
            self.trait_service = world.services.try_get(TraitService)

        if self.trait_service:
            interaction_data = self.trait_service.get_interaction(
                event.interaction_type
            )
            if interaction_data and "range_type" in interaction_data:
                range_type = interaction_data["range_type"]
            elif event.interaction_type in ["Scream", "Shout"]:
                # Fallback if not defined in TOML yet (though we updated it)
                range_type = (
                    "auditory_loud"
                    if event.interaction_type == "Scream"
                    else "auditory"
                )

        candidates = self.sector_map.get_entities_in_range(
            actor_trans.x, actor_trans.y, range_type
        )

        for witness_id in candidates:
            if witness_id == event.initiator_id or witness_id == event.target_id:
                continue

            # Must have GossipQueue and YukkuriStats
            if not world.has_component(
                witness_id, GossipQueue
            ) or not world.has_component(witness_id, YukkuriStats):
                continue

            witness_trans = world.get_component(witness_id, Transform)
            if not witness_trans:
                continue

            # Visual Check: Line of Sight
            if range_type == "visual":
                if not self._check_line_of_sight(world, actor_trans, witness_trans):
                    continue

            # Interest Group Bonus
            value = 10.0
            if self._is_in_same_interest_group(world, witness_id, event.initiator_id):
                value += 5.0  # Boost value (Hearing Bonus)

            # Add Witness Gossip
            self._add_witness_gossip(world, witness_id, event, now, value=value)

    def _check_line_of_sight(
        self, world: World, start_trans: Transform, end_trans: Transform
    ) -> bool:
        """
        Checks if there is a clear line of sight between two transforms.
        Uses PhysicsSystem raycast.

        Args:
            world (World): The ECS World.
            start_trans (Transform): Origin transform.
            end_trans (Transform): Target transform.

        Returns:
            bool: True if line of sight exists, False otherwise.
        """
        if not self.physics_system:
            self.physics_system = world.services.try_get(PhysicsSystem)

        if not self.physics_system:
            return True  # Fallback if no physics

        start_pos = (start_trans.x, start_trans.y)
        end_pos = (end_trans.x, end_trans.y)

        query = self.physics_system.space.segment_query_first(
            start_pos, end_pos, 1.0, pymunk.ShapeFilter()
        )

        if query:
            # Check what we hit
            hit_body = query.shape.body
            if hit_body and hit_body.userdata:
                # Optimization: checking if hit point is close to end_pos
                hit_dist = math.hypot(
                    query.point.x - start_pos[0], query.point.y - start_pos[1]
                )
                total_dist = math.hypot(
                    end_pos[0] - start_pos[0], end_pos[1] - start_pos[1]
                )

                if hit_dist < total_dist - 5.0:  # Hit something else
                    return False

        return True

    def _is_in_same_interest_group(
        self, world: World, entity_a: int, entity_b: int
    ) -> bool:
        """
        Checks if two entities are in the same interest group (Family, Pack).

        Args:
            world (World): The ECS World.
            entity_a (int): Entity A ID.
            entity_b (int): Entity B ID.

        Returns:
            bool: True if in the same group.
        """
        reg_a = world.get_component(entity_a, RelationshipRegistry)
        reg_b = world.get_component(entity_b, RelationshipRegistry)

        if not reg_a or not reg_b:
            return False

        # Check Family
        if (
            reg_a.family_group_id is not None
            and reg_a.family_group_id == reg_b.family_group_id
        ):
            return True

        return False

    def _exchange_gossip(self, world: World, sender_id: int, receiver_id: int) -> None:
        """
        Exchanges gossip from sender to receiver.

        Args:
            world (World): The ECS World.
            sender_id (int): Sender entity ID.
            receiver_id (int): Receiver entity ID.
        """
        sender_queue = world.get_component(sender_id, GossipQueue)
        receiver_queue = world.get_component(receiver_id, GossipQueue)

        if not sender_queue or not receiver_queue:
            return

        # Get Max Gossip Length from Config
        from ...config import GameConfig

        config = world.services.try_get(GameConfig)
        max_length = 10
        if config and hasattr(config.rules, "social"):
            max_length = config.rules.social.max_gossip_length

        is_group_member = self._is_in_same_interest_group(world, sender_id, receiver_id)

        # Share ALL packets (respecting max_length on receiver side implicitly)
        # Iterate over a copy since we are not modifying sender_queue here, but good practice
        for packet in sender_queue.priority_queue:
            # Don't share gossip about the receiver to the receiver
            if packet.target_id == receiver_id:
                continue

            # Apply decay
            new_value = packet.value * 0.9

            # Apply Hearing Bonus if in same group (prioritize group member's info)
            if is_group_member:
                new_value *= 1.2

            new_packet = GossipPacket(
                target_id=packet.target_id,
                event_type=packet.event_type,
                value=new_value,
                timestamp=packet.timestamp,
            )
            receiver_queue.add_packet(new_packet, max_length=max_length)

    def _add_witness_gossip(
        self,
        world: World,
        witness_id: int,
        event: SocialInteractionEvent,
        now: float,
        value: float,
    ) -> None:
        """
        Adds a gossip packet to a witness's queue.

        Args:
            world (World): The ECS World.
            witness_id (int): Witness entity ID.
            event (SocialInteractionEvent): The event witnessed.
            now (float): Current timestamp.
            value (float): Importance value of the gossip.
        """
        # Threshold Check
        from ...config import GameConfig

        config = world.services.try_get(GameConfig)
        witness_threshold = 5.0
        if config and hasattr(config.rules, "social"):
            witness_threshold = config.rules.social.witness_threshold

        if value < witness_threshold:
            return

        gossip = world.get_component(witness_id, GossipQueue)
        if not gossip:
            return

        # Get Max Gossip Length from Config
        from ...config import GameConfig

        config = world.services.try_get(GameConfig)
        max_length = 10
        if config and hasattr(config.rules, "social"):
            max_length = config.rules.social.max_gossip_length

        packet = GossipPacket(
            target_id=event.initiator_id,
            event_type=event.interaction_type,
            value=value,
            timestamp=now,
        )
        gossip.add_packet(packet, max_length=max_length)
