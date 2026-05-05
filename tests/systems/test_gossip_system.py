"""
Consolidated tests for the Gossip System.
Merged from test_gossip_system.py, test_gossip_system_game.py, and test_gossip_service.py.
"""

import pytest
from test_utils import make_configured_world
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
    Needs,
    EmotionalState,
    Personality,
)
from yukkuri_game.game.components import Transform, InteractionRequest
from yukkuri_game.game.systems.spatial_system import SpatialService
from yukkuri_game.game.systems.physics import PhysicsSystem
from yukkuri_game.game.trait_service import TraitService
from yukkuri_game.config import GameConfig


class TestGossipSystem:
    """Tests for GossipSystem logic."""

    @pytest.fixture
    def event_bus(self):
        return MagicMock(spec=EventBus)

    @pytest.fixture
    def system(self, event_bus):
        sys = GossipSystem()
        world = MagicMock(spec=World)
        world.services = MagicMock()
        world.services.get.side_effect = lambda t: event_bus if t == EventBus else None
        sys.ecs_world = world
        sys.initialize()
        return sys

    @pytest.fixture
    def mock_world(self, system):
        world = system.ecs_world
        world.services = MagicMock()

        physics = MagicMock(spec=PhysicsSystem)
        physics.space = MagicMock(spec=pymunk.Space)
        spatial_service = MagicMock(spec=SpatialService)
        trait_service = MagicMock(spec=TraitService)
        game_config = MagicMock(spec=GameConfig)

        game_config.rules = MagicMock()
        game_config.rules.social = MagicMock()
        game_config.rules.social.max_gossip_length = 10
        game_config.rules.social.witness_threshold = 5.0

        service_map = {
            PhysicsSystem: physics,
            SpatialService: spatial_service,
            TraitService: trait_service,
            GameConfig: game_config,
        }
        world.services.try_get.side_effect = lambda t: service_map.get(t)
        return world

    # --- Initialization ---
    def test_initialization(self, system, event_bus):
        """Test system initialization and subscription."""
        event_bus.subscribe.assert_called_with(
            SocialInteractionEvent, system.on_social_interaction
        )

    # --- Gossip Exchange ---
    def test_gossip_exchange_talk(self, system, mock_world):
        """Test gossip exchange when talking."""
        config = mock_world.services.try_get(GameConfig)
        config.rules.social.max_gossip_length = 10

        sender, receiver = 1, 2
        sender_queue = GossipQueue()
        packet = GossipPacket(
            target_id=3, event_type="TestEvent", value=10.0, timestamp=100.0
        )
        sender_queue.add_packet(packet, max_length=10)
        receiver_queue = GossipQueue()

        def get_component(eid, comp_type):
            if comp_type == GossipQueue:
                return sender_queue if eid == sender else receiver_queue
            if comp_type == RelationshipRegistry:
                return RelationshipRegistry()
            if comp_type == Transform:
                return Transform(x=0, y=0)
            return None

        mock_world.get_component.side_effect = get_component
        mock_world.entity_exists.return_value = True

        spatial_service = mock_world.services.try_get(SpatialService)
        spatial_service.get_entities_in_range.return_value = []

        event = SocialInteractionEvent(
            initiator_id=sender, target_id=receiver, interaction_type="Talk"
        )
        system.on_social_interaction(event)

        assert len(receiver_queue.priority_queue) == 1
        received = receiver_queue.priority_queue[0]
        assert received.target_id == 3
        assert received.value < 10.0  # Decay applied

    def test_gossip_exchange_same_group_bonus(self, system, mock_world):
        """Test gossip exchange bonus for same family group."""
        config = mock_world.services.try_get(GameConfig)
        config.rules.social.max_gossip_length = 10

        sender, receiver = 1, 2
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
        system.spatial_service = MagicMock()
        system.spatial_service.get_entities_in_range.return_value = []

        event = SocialInteractionEvent(
            initiator_id=sender, target_id=receiver, interaction_type="Chat"
        )
        system.on_social_interaction(event)

        received = receiver_queue.priority_queue[0]
        assert received.value == pytest.approx(10.0 * 0.9 * 1.2)  # Decay * family bonus

    # --- Witnessing ---
    def test_witnessing(self, system, mock_world):
        """Test a third party witnessing an event."""
        config = mock_world.services.try_get(GameConfig)
        config.rules.social.witness_threshold = 5.0

        actor, target, witness = 1, 2, 3
        actor_trans = Transform(x=100, y=100)
        witness_trans = Transform(x=150, y=100)
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
        mock_world.has_component.return_value = True

        spatial_service = mock_world.services.try_get(SpatialService)
        spatial_service.get_entities_in_range.return_value = [witness]

        physics = mock_world.services.try_get(PhysicsSystem)
        physics.space.segment_query_first.return_value = None

        event = SocialInteractionEvent(
            initiator_id=actor, target_id=target, interaction_type="Punch"
        )
        system.on_social_interaction(event)

        assert len(witness_queue.priority_queue) == 1
        packet = witness_queue.priority_queue[0]
        assert packet.target_id == actor
        assert packet.event_type == "Punch"

    def test_line_of_sight_blocked(self, system, mock_world):
        """Test witnessing blocked by obstacle."""
        actor, witness = 1, 3
        actor_trans = Transform(x=0, y=0)
        witness_trans = Transform(x=100, y=0)
        witness_queue = GossipQueue()

        def get_component(eid, comp_type):
            if eid == actor and comp_type == Transform:
                return actor_trans
            if eid == witness:
                if comp_type == Transform:
                    return witness_trans
                if comp_type == GossipQueue:
                    return witness_queue
                if comp_type == YukkuriStats:
                    return YukkuriStats(name="Reimu", type_id="reimu")
            return None

        mock_world.get_component.side_effect = get_component
        mock_world.has_component.return_value = True

        spatial_service = mock_world.services.try_get(SpatialService)
        spatial_service.get_entities_in_range.return_value = [witness]

        trait_service = mock_world.services.try_get(TraitService)
        trait_service.get_interaction.return_value = None

        physics = mock_world.services.try_get(PhysicsSystem)
        query_res = MagicMock()
        query_res.point = pymunk.Vec2d(50, 0)
        query_res.shape.body.userdata = "Wall"
        physics.space.segment_query_first.return_value = query_res

        event = SocialInteractionEvent(
            initiator_id=actor, target_id=2, interaction_type="Wave"
        )
        system.on_social_interaction(event)

        assert len(witness_queue.priority_queue) == 0


class TestGossipExchangeIntegrity:
    """Regression tests for gossip queue integrity (no duplicates)."""

    def test_gossip_exchange_no_duplicates(self):
        """Ensure duplicate packets are not added when sharing gossip multiple times."""
        from yukkuri_game.engine.audio import AudioManager
        from yukkuri_game.game.systems.social_system import SocialSystem
        from yukkuri_game.game.systems.interaction_system import InteractionSystem
        from yukkuri_game.game.skill_service import SkillService

        world = make_configured_world()

        audio_manager = MagicMock(spec=AudioManager)
        world.services.register(audio_manager, AudioManager)

        trait_service = MagicMock(spec=TraitService)
        trait_service.get_interaction.return_value = {
            "type": "SOCIAL",
            "base_impact": 10.0,
        }
        trait_service.get_trait.return_value = {}
        trait_service.calculate_overrides.return_value = {}
        world.services.register(trait_service, TraitService)

        skill_service = MagicMock(spec=SkillService)
        world.services.register(skill_service, SkillService)

        social_system = SocialSystem()
        world.services.register(social_system, SocialSystem)
        world.add_system(social_system)

        gossip_system = GossipSystem()
        world.add_system(gossip_system)

        interaction_system = InteractionSystem()
        world.add_system(interaction_system)

        # Create two entities
        entity_a = world.create_entity()
        world.add_component(entity_a, YukkuriStats(name="A", type_id="reimu"))
        world.add_component(entity_a, Needs())
        world.add_component(entity_a, EmotionalState())
        world.add_component(entity_a, GossipQueue())
        world.add_component(entity_a, RelationshipRegistry())
        world.add_component(entity_a, Transform(0, 0))
        world.add_component(entity_a, Personality())

        entity_b = world.create_entity()
        world.add_component(entity_b, YukkuriStats(name="B", type_id="marisa"))
        world.add_component(entity_b, Needs())
        world.add_component(entity_b, EmotionalState())
        world.add_component(entity_b, GossipQueue())
        world.add_component(entity_b, RelationshipRegistry())
        world.add_component(entity_b, Transform(0, 0))
        world.add_component(entity_b, Personality())

        # Add packet to A
        packet = GossipPacket(
            target_id=999, event_type="Fight", value=10.0, timestamp=0.0
        )
        queue_a = world.get_component(entity_a, GossipQueue)
        queue_a.add_packet(packet)

        # Interact twice
        world.add_component(
            entity_a, InteractionRequest(target_id=entity_b, action="Talk")
        )
        interaction_system.update(world, 0.1)

        world.add_component(
            entity_a, InteractionRequest(target_id=entity_b, action="Talk")
        )
        interaction_system.update(world, 0.1)

        queue_b = world.get_component(entity_b, GossipQueue)
        assert len(queue_b.priority_queue) == 1, (
            "Queue grew unexpectedly (duplicates not handled)"
        )
