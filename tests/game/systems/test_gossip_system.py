import pytest
from unittest.mock import MagicMock
import pymunk
from yukkuri_game.game.systems.gossip_system import GossipSystem
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.events import SocialInteractionEvent
from yukkuri_game.game.yukkuri_components import (
    GossipQueue,
    GossipPacket,
    YukkuriStats,
    RelationshipRegistry,
)
from yukkuri_game.game.components import Transform
from yukkuri_game.game.systems.sector_system import SectorMap
from yukkuri_game.game.systems.physics import PhysicsSystem
from yukkuri_game.game.trait_service import TraitService
from yukkuri_game.config import GameConfig


class TestGossipSystem:
    @pytest.fixture
    def event_bus(self):
        return MagicMock(spec=EventBus)

    @pytest.fixture
    def system(self, event_bus):
        sys = GossipSystem(event_bus)
        # Mock world for the system
        sys.ecs_world = MagicMock(spec=World)
        return sys

    @pytest.fixture
    def mock_world(self, system):
        world = system.ecs_world

        # Mock services
        world.services = MagicMock()

        # Create mocks once
        physics = MagicMock(spec=PhysicsSystem)
        physics.space = MagicMock(spec=pymunk.Space)
        sector_map = MagicMock(spec=SectorMap)
        trait_service = MagicMock(spec=TraitService)
        game_config = MagicMock(spec=GameConfig)

        # Setup config defaults to avoid issues
        game_config.rules = MagicMock()
        game_config.rules.social = MagicMock()
        game_config.rules.social.max_gossip_length = 10
        game_config.rules.social.witness_threshold = 5.0

        service_map = {
            PhysicsSystem: physics,
            SectorMap: sector_map,
            TraitService: trait_service,
            GameConfig: game_config,
        }

        world.services.try_get.side_effect = lambda t: service_map.get(t)

        return world

    def test_initialization(self, system, event_bus):
        """Test system initialization and subscription."""
        event_bus.subscribe.assert_called_with(
            SocialInteractionEvent, system.on_social_interaction
        )

    def test_gossip_exchange_talk(self, system, mock_world):
        """Test gossip exchange when talking."""
        # Mock GameConfig
        config = mock_world.services.try_get(GameConfig)
        config.rules.social.max_gossip_length = 10
        config.rules.social.witness_threshold = 5.0

        # Setup entities
        sender = 1
        receiver = 2

        # Components
        sender_queue = GossipQueue()
        packet = GossipPacket(
            target_id=3, event_type="TestEvent", value=10.0, timestamp=100.0
        )
        sender_queue.add_packet(packet, max_length=10)

        receiver_queue = GossipQueue()

        def get_component(eid, comp_type):
            if comp_type == GossipQueue:
                if eid == sender:
                    return sender_queue
                if eid == receiver:
                    return receiver_queue
            if comp_type == RelationshipRegistry:
                return RelationshipRegistry()  # Different families
            if comp_type == Transform:
                return Transform(x=0, y=0)
            return None

        mock_world.get_component.side_effect = get_component
        mock_world.entity_exists.return_value = True

        # Trigger event
        event = SocialInteractionEvent(
            initiator_id=sender, target_id=receiver, interaction_type="Talk"
        )

        # Mock sector map to return empty witnesses to focus on exchange
        sector_map = mock_world.services.try_get(SectorMap)
        sector_map.get_entities_in_range.return_value = []

        system.on_social_interaction(event)

        # Check receiver got the packet
        assert len(receiver_queue.priority_queue) == 1
        received = receiver_queue.priority_queue[0]
        assert received.target_id == 3
        assert received.value < 10.0  # Decay applied
        assert received.event_type == "TestEvent"

    def test_gossip_exchange_same_group_bonus(self, system, mock_world):
        """Test gossip exchange bonus for same group."""
        # Mock GameConfig
        config = mock_world.services.try_get(GameConfig)
        config.rules.social.max_gossip_length = 10

        sender = 1
        receiver = 2

        sender_queue = GossipQueue()
        packet = GossipPacket(target_id=3, event_type="Test", value=10.0, timestamp=100)
        sender_queue.add_packet(packet, max_length=10)
        receiver_queue = GossipQueue()

        reg_a = RelationshipRegistry()
        reg_a.family_group_id = 1
        reg_b = RelationshipRegistry()
        reg_b.family_group_id = 1

        def get_component(eid, comp_type):
            if comp_type == GossipQueue:
                return sender_queue if eid == sender else receiver_queue
            if comp_type == RelationshipRegistry:
                return reg_a if eid == sender else reg_b
            if comp_type == Transform:
                return Transform(x=0, y=0)
            return None

        mock_world.get_component.side_effect = get_component

        event = SocialInteractionEvent(
            initiator_id=sender, target_id=receiver, interaction_type="Chat"
        )
        system.sector_map = MagicMock()
        system.sector_map.get_entities_in_range.return_value = []

        system.on_social_interaction(event)

        received = receiver_queue.priority_queue[0]
        # Base decay 0.9, Bonus 1.2 -> 1.08
        assert received.value == pytest.approx(10.0 * 0.9 * 1.2)

    def test_witnessing(self, system, mock_world):
        """Test a third party witnessing an event."""
        # Mock GameConfig
        config = mock_world.services.try_get(GameConfig)
        config.rules.social.max_gossip_length = 10
        config.rules.social.witness_threshold = 5.0

        actor = 1
        target = 2
        witness = 3

        # Transforms
        actor_trans = Transform(x=100, y=100)
        witness_trans = Transform(x=150, y=100)  # Nearby

        # Witness components
        witness_queue = GossipQueue()
        witness_stats = YukkuriStats(name="Reimu", type_id="reimu")

        def get_component(eid, comp_type):
            if eid == actor and comp_type == Transform:
                return actor_trans
            if eid == witness:
                if comp_type == Transform:
                    return witness_trans
                if comp_type == GossipQueue:
                    return witness_queue
                if comp_type == YukkuriStats:
                    return witness_stats
                if comp_type == RelationshipRegistry:
                    return RelationshipRegistry()
            if eid == actor and comp_type == RelationshipRegistry:
                return RelationshipRegistry()
            return None

        mock_world.get_component.side_effect = get_component
        mock_world.has_component.side_effect = lambda eid, c: True  # Simplify

        # Sector map returns witness
        sector_map = mock_world.services.try_get(SectorMap)
        sector_map.get_entities_in_range.return_value = [witness]

        # Physics raycast clear
        physics = mock_world.services.try_get(PhysicsSystem)
        physics.space.segment_query_first.return_value = None  # No obstacle

        event = SocialInteractionEvent(
            initiator_id=actor, target_id=target, interaction_type="Punch"
        )

        system.on_social_interaction(event)

        # Witness should have queued a gossip packet about actor
        assert len(witness_queue.priority_queue) == 1
        packet = witness_queue.priority_queue[0]
        assert packet.target_id == actor
        assert packet.event_type == "Punch"
        assert packet.value >= 10.0

    def test_line_of_sight_blocked(self, system, mock_world):
        """Test witnessing blocked by obstacle."""
        # Mock GameConfig
        config = mock_world.services.try_get(GameConfig)
        config.rules.social.max_gossip_length = 10

        actor = 1
        witness = 3

        actor_trans = Transform(x=0, y=0)
        witness_trans = Transform(x=100, y=0)
        
        # Create persistent witness queue that we can check after the test
        witness_queue = GossipQueue()

        def get_component(eid, comp_type):
            if eid == actor and comp_type == Transform:
                return actor_trans
            if eid == witness:
                if comp_type == Transform:
                    return witness_trans
                if comp_type == GossipQueue:
                    return witness_queue  # Return the persistent queue
                if comp_type == YukkuriStats:
                    return YukkuriStats(name="Reimu", type_id="reimu")
            return None

        mock_world.get_component.side_effect = get_component
        mock_world.has_component.return_value = True

        sector_map = mock_world.services.try_get(SectorMap)
        sector_map.get_entities_in_range.return_value = [witness]

        # Ensure trait_service returns None for unknown interactions
        # so that range_type defaults to "visual" and LOS check is performed
        trait_service = mock_world.services.try_get(TraitService)
        trait_service.get_interaction.return_value = None

        # Physics raycast hits something (line of sight blocked)
        physics = mock_world.services.try_get(PhysicsSystem)
        query_res = MagicMock()
        query_res.point = pymunk.Vec2d(50, 0)  # Hit halfway
        query_res.shape.body.userdata = "Wall"
        physics.space.segment_query_first.return_value = query_res

        event = SocialInteractionEvent(
            initiator_id=actor, target_id=2, interaction_type="Wave"
        )

        system.on_social_interaction(event)

        # Should not have witnessed (no gossip added) because line of sight is blocked
        assert len(witness_queue.priority_queue) == 0

