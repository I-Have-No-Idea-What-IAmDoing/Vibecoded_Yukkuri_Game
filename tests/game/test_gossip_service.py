
import pytest
from unittest.mock import MagicMock
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.services import GameService
from yukkuri_game.game.yukkuri_components import YukkuriStats, GossipQueue, GossipPacket, EmotionalState, RelationshipRegistry, Personality
from yukkuri_game.game.components import Transform
from yukkuri_game.engine.audio import AudioManager
from yukkuri_game.game.systems.social_system import SocialSystem
from yukkuri_game.game.systems.gossip_system import GossipSystem
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.game.components import InteractionRequest
from yukkuri_game.game.trait_service import TraitService
from yukkuri_game.game.skill_service import SkillService

def test_gossip_exchange_integrity():
    """
    Tests that social interaction properly exchanges gossip using the add_packet method,
    ensuring no duplicates are created and the queue remains sorted/managed.
    This serves as a regression test for the bug where packets were blindly appended.
    """
    world = World()
    event_bus = EventBus()

    # Mock Services
    audio_manager = MagicMock(spec=AudioManager)
    world.services.register(audio_manager, AudioManager)

    trait_service = MagicMock(spec=TraitService)
    # Mock get_interaction to return something valid so SocialSystem doesn't bail
    trait_service.get_interaction.return_value = {"type": "SOCIAL", "base_impact": 10.0}
    trait_service.get_trait.return_value = {} # For personality checks
    world.services.register(trait_service, TraitService)

    skill_service = MagicMock(spec=SkillService)
    world.services.register(skill_service, SkillService)

    # Register Systems
    social_system = SocialSystem(event_bus)
    gossip_system = GossipSystem(event_bus)

    # Manually set ecs_world for GossipSystem as it's used in event handler
    gossip_system.ecs_world = world

    # We need to manually register the GossipSystem as a listener to SocialInteractionEvent
    # Wait, GossipSystem subscribes itself in __init__?
    # No, usually systems subscribe in __init__. Let's check GossipSystem.
    # It does subscribe to SocialInteractionEvent.

    # Create two entities
    entity_a = world.create_entity()
    world.add_component(entity_a, YukkuriStats(name="A", type_id="reimu"))
    world.add_component(entity_a, EmotionalState())
    world.add_component(entity_a, GossipQueue())
    world.add_component(entity_a, RelationshipRegistry())
    world.add_component(entity_a, Transform(0, 0))
    world.add_component(entity_a, Personality())

    entity_b = world.create_entity()
    world.add_component(entity_b, YukkuriStats(name="B", type_id="marisa"))
    world.add_component(entity_b, EmotionalState())
    world.add_component(entity_b, GossipQueue())
    world.add_component(entity_b, RelationshipRegistry())
    world.add_component(entity_b, Transform(0, 0))
    world.add_component(entity_b, Personality())

    # Create a gossip packet for A
    packet = GossipPacket(target_id=999, event_type="Fight", value=10.0, timestamp=0.0)

    # Use the proper method to add to A initially
    queue_a = world.get_component(entity_a, GossipQueue)
    queue_a.add_packet(packet)

    assert len(queue_a.priority_queue) == 1

    # Interaction 1: A talks to B. A should share the gossip.
    # REFACTOR: Use InteractionRequest
    world.add_component(entity_a, InteractionRequest(target_id=entity_b, action="Talk"))

    # Process Social System first to trigger SocialInteractionEvent
    social_system.update(world, 0.1)

    # GossipSystem reacts to the event by checking "Talk" interaction and exchanging gossip
    # But GossipSystem listens to events. We need to pump the event bus?
    # GossipSystem subscribes to event_bus.
    # SocialSystem publishes event.
    # If EventBus is synchronous (it usually is in simple impl), it should be fine.

    # Wait, does EventBus process immediately or queue?
    # yukkuri_game/engine/event_bus.py: publish calls listeners immediately.

    # However, GossipSystem needs to be updated?
    # Or does it handle logic in the event handler?
    # Let's check GossipSystem.

    # Assuming GossipSystem.on_social_interaction calls _share_gossip

    queue_b = world.get_component(entity_b, GossipQueue)

    # B should have received the gossip
    # NOTE: If GossipSystem uses probability, this might flake?
    # GossipSystem logic: share if len(queue) > 0.

    assert len(queue_b.priority_queue) == 1
    assert queue_b.priority_queue[0].target_id == 999

    # Interaction 2: A talks to B again.
    # A still has the packet. A should share it again.
    # The fix ensures duplicates are handled by add_packet logic.
    world.add_component(entity_a, InteractionRequest(target_id=entity_b, action="Talk"))
    social_system.update(world, 0.1)

    # Check B's queue length. It should remain 1 if deduplication works.
    # If the bug regresses (direct append), it would be > 1.
    assert len(queue_b.priority_queue) == 1, f"Queue grew unexpectedly: {len(queue_b.priority_queue)}"

    # Ensure queue is sorted (though with 1 element it's trivial)
    # Let's add another different packet to verify adding works
    packet2 = GossipPacket(target_id=888, event_type="Dance", value=20.0, timestamp=0.0)
    queue_a.add_packet(packet2)

    world.add_component(entity_a, InteractionRequest(target_id=entity_b, action="Talk"))
    social_system.update(world, 0.1)

    # Now B should have 2 packets
    assert len(queue_b.priority_queue) == 2
    # And sorted by value (descending)
    # Note: GossipSystem applies 0.9 decay on exchange
    assert queue_b.priority_queue[0].value == 20.0 * 0.9
    assert queue_b.priority_queue[1].value == 10.0 * 0.9
