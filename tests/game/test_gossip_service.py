
import pytest
from unittest.mock import MagicMock
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.services import GameService
from yukkuri_game.game.yukkuri_components import YukkuriStats, GossipQueue, GossipPacket, EmotionalState, RelationshipRegistry
from yukkuri_game.engine.audio import AudioManager

def test_gossip_exchange_integrity():
    """
    Tests that social interaction properly exchanges gossip using the add_packet method,
    ensuring no duplicates are created and the queue remains sorted/managed.
    This serves as a regression test for the bug where packets were blindly appended.
    """
    world = World()

    # Mock AudioManager
    audio_manager = MagicMock(spec=AudioManager)
    world.services.register(audio_manager, AudioManager)

    game_service = GameService(world)

    # Create two entities
    entity_a = world.create_entity()
    world.add_component(entity_a, YukkuriStats(name="A", type_id="reimu"))
    world.add_component(entity_a, EmotionalState())
    world.add_component(entity_a, GossipQueue())
    world.add_component(entity_a, RelationshipRegistry())

    entity_b = world.create_entity()
    world.add_component(entity_b, YukkuriStats(name="B", type_id="marisa"))
    world.add_component(entity_b, EmotionalState())
    world.add_component(entity_b, GossipQueue())
    world.add_component(entity_b, RelationshipRegistry())

    # Create a gossip packet for A
    packet = GossipPacket(target_id=999, event_type="Fight", value=10.0, timestamp=0.0)

    # Use the proper method to add to A initially
    queue_a = world.get_component(entity_a, GossipQueue)
    queue_a.add_packet(packet)

    assert len(queue_a.priority_queue) == 1

    # Interaction 1: A talks to B. A should share the gossip.
    game_service.interact_social(entity_a, entity_b, "Talk")

    queue_b = world.get_component(entity_b, GossipQueue)

    # B should have received the gossip
    assert len(queue_b.priority_queue) == 1
    assert queue_b.priority_queue[0].target_id == 999

    # Interaction 2: A talks to B again.
    # A still has the packet. A should share it again.
    # The fix ensures duplicates are handled by add_packet logic.
    game_service.interact_social(entity_a, entity_b, "Talk")

    # Check B's queue length. It should remain 1 if deduplication works.
    # If the bug regresses (direct append), it would be > 1.
    assert len(queue_b.priority_queue) == 1, f"Queue grew unexpectedly: {len(queue_b.priority_queue)}"

    # Ensure queue is sorted (though with 1 element it's trivial)
    # Let's add another different packet to verify adding works
    packet2 = GossipPacket(target_id=888, event_type="Dance", value=20.0, timestamp=0.0)
    queue_a.add_packet(packet2)

    game_service.interact_social(entity_a, entity_b, "Talk")

    # Now B should have 2 packets
    assert len(queue_b.priority_queue) == 2
    # And sorted by value (descending)
    assert queue_b.priority_queue[0].value == 20.0
    assert queue_b.priority_queue[1].value == 10.0
