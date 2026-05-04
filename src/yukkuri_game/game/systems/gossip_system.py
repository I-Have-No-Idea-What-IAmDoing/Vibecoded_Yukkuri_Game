"""
Gossip System - Social Information Propagation.

Manages the witnessing and exchange of social information between entities.
Gossip enables emergent social dynamics where Yukkuris can:
-   Witness interactions between others and form opinions.
-   Share information through verbal exchanges (Talk, Greet, Chat).
-   Prioritize gossip by interest group membership (family, pack).

Propagation Mechanics:
-   Witnesses within range (visual or auditory) receive gossip packets.
-   Gossip value decays with each retransmission (GOSSIP_DECAY).
-   Family/pack members receive boosted value (HEARING_BONUS_MULTIPLIER).
-   Low-value gossip is filtered by WITNESS_THRESHOLD.
"""

import math
from typing import cast

import pymunk

from ...engine.ecs import System, World
from ...engine.event_bus import EventBus
from ...engine.types import EntityID
from ..components import Transform
from ..events import SocialInteractionEvent
from ..trait_service import TraitService
from ..yukkuri_components import (
    GossipPacket,
    GossipQueue,
    RelationshipRegistry,
    YukkuriStats,
)
from .physics import PhysicsSystem
from .sector_system import SectorMap


class GossipSystem(System):
    """
    System responsible for managing Gossip (witnessing and exchanging).
    Uses SectorMap for efficient witnessing.

    Attributes:
        event_bus (EventBus): The event bus instance.
        physics_system (PhysicsSystem | None): The physics system instance.
        sector_map (SectorMap | None): The sector map instance.
        trait_service (TraitService | None): The trait service instance.
    """

    # Minimum gossip value required to be recorded as a witness
    WITNESS_THRESHOLD = 5.0

    # Gossip value multiplier when retransmitting (simulates information decay)
    GOSSIP_DECAY = 0.9

    # Value boost for family/pack members (prioritizes group-relevant info)
    HEARING_BONUS_MULTIPLIER = 1.2

    # Fixed bonus added when witnessing group member interactions
    INTEREST_GROUP_BONUS_VALUE = 5.0

    # Base value assigned to witnessed events
    BASE_WITNESS_VALUE = 10.0

    # Default maximum gossip packets per entity queue
    DEFAULT_MAX_GOSSIP_LENGTH = 10

    def __init__(self) -> None:
        """
        Initializes the GossipSystem.
        """
        super().__init__()
        self.event_bus: EventBus
        self.physics_system: PhysicsSystem | None = None
        self.sector_map: SectorMap | None = None
        self.trait_service: TraitService | None = None

    def initialize(self) -> None:
        """Called when the system is added to the world."""
        self.event_bus = self.ecs_world.services.get(EventBus)
        self.event_bus.subscribe(SocialInteractionEvent, self.on_social_interaction)

    def update(self, world: World, dt: float) -> None:
        """
        Updates the system and lazily fetches dependencies.

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
            event (SocialInteractionEvent): The event data.
        """
        if not hasattr(self, "ecs_world"):
            return
        world = self.ecs_world

        actor_trans = world.get_component(event.initiator_id, Transform)
        if not actor_trans:
            return

        now = world.time

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
            if interaction_data:
                range_type = interaction_data.range_type
            elif event.interaction_type in ["Scream", "Shout"]:
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
            value = self.BASE_WITNESS_VALUE
            if self._is_in_same_interest_group(world, witness_id, event.initiator_id):
                value += self.INTEREST_GROUP_BONUS_VALUE  # Boost value (Hearing Bonus)

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
            hit_body = query.shape.body
            if hit_body and hit_body.userdata:
                # Check if hit point is closer than target (obstacle blocking view).
                hit_dist = math.hypot(
                    query.point.x - start_pos[0], query.point.y - start_pos[1]
                )
                total_dist = math.hypot(
                    end_pos[0] - start_pos[0], end_pos[1] - start_pos[1]
                )

                if hit_dist < total_dist - 5.0:
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
            sender_id (int): Source entity.
            receiver_id (int): Destination entity.
        """
        sender_queue = world.get_component(sender_id, GossipQueue)
        receiver_queue = world.get_component(receiver_id, GossipQueue)

        if not sender_queue or not receiver_queue:
            return

        # Get Max Gossip Length from Config
        from ...config import GameConfig

        config = world.services.try_get(GameConfig)
        max_length = self.DEFAULT_MAX_GOSSIP_LENGTH
        if config and hasattr(config.rules, "social"):
            max_length = config.rules.social.max_gossip_length

        is_group_member = self._is_in_same_interest_group(world, sender_id, receiver_id)

        for packet in sender_queue.priority_queue:
            if packet.target_id == receiver_id:  # Don't tell receiver about themselves.
                continue

            new_value = packet.value * self.GOSSIP_DECAY

            if is_group_member:  # Prioritize group member's info.
                new_value *= self.HEARING_BONUS_MULTIPLIER

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
            witness_id (int): The witness causing the gossip.
            event (SocialInteractionEvent): The event being witnessed.
            now (float): Current timestamp.
            value (float): Initial value of the gossip.
        """
        if value < self.WITNESS_THRESHOLD:
            return

        gossip = world.get_component(witness_id, GossipQueue)
        if not gossip:
            return

        from ...config import GameConfig

        config = world.services.try_get(GameConfig)
        max_length = self.DEFAULT_MAX_GOSSIP_LENGTH
        if config and hasattr(config.rules, "social"):
            max_length = config.rules.social.max_gossip_length

        packet = GossipPacket(
            target_id=cast(EntityID, event.initiator_id),
            event_type=event.interaction_type,
            value=value,
            timestamp=now,
        )
        gossip.add_packet(packet, max_length=max_length)
