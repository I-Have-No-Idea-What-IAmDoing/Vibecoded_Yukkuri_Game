"""
Tests for the Gossip System.
"""
import pytest
from unittest.mock import MagicMock
from ..game.systems.gossip_system import GossipSystem
from ..game.events import SocialInteractionEvent
from ..game.components import Transform
from ..game.yukkuri_components import YukkuriStats, GossipQueue
from ..engine.ecs import World
from ..engine.event_bus import EventBus
import pymunk

@pytest.fixture # type: ignore[misc]
def world() -> World:
    """
    Creates a new ECS World for testing.

    Returns:
        World: A new ECS World instance.
    """
    return World()

@pytest.fixture # type: ignore[misc]
def event_bus() -> EventBus:
    """
    Creates a new EventBus for testing.

    Returns:
        EventBus: A new EventBus instance.
    """
    return EventBus()

@pytest.fixture # type: ignore[misc]
def gossip_system(event_bus: EventBus) -> GossipSystem:
    """
    Creates a GossipSystem for testing.

    Args:
        event_bus (EventBus): The event bus to use.

    Returns:
        GossipSystem: A new GossipSystem instance.
    """
    return GossipSystem(event_bus)

def test_witness_gossip_spatial(world: World, event_bus: EventBus, gossip_system: GossipSystem) -> None:
    """
    Tests that a witness entity correctly receives gossip when an interaction occurs nearby.

    Args:
        world (World): The ECS World fixture.
        event_bus (EventBus): The EventBus fixture.
        gossip_system (GossipSystem): The GossipSystem fixture.
    """
    # Mock PhysicsSystem
    physics_system = MagicMock()
    from ..game.systems.physics import PhysicsSystem
    world.services.register(physics_system, PhysicsSystem)

    # Setup Actors
    actor = world.create_entity()
    world.add_component(actor, Transform(x=100, y=100))
    world.add_component(actor, YukkuriStats(name="Actor", type_id="test"))

    target = world.create_entity()
    world.add_component(target, Transform(x=110, y=100))
    world.add_component(target, YukkuriStats(name="Target", type_id="test"))

    witness = world.create_entity()
    world.add_component(witness, Transform(x=150, y=100)) # Within 300 range
    world.add_component(witness, YukkuriStats(name="Witness", type_id="test"))
    world.add_component(witness, GossipQueue())

    # Mock Physics Query Result
    mock_shape = MagicMock()
    mock_shape.body.userdata = witness # Entity ID stored in userdata

    mock_info = MagicMock()
    mock_info.shape = mock_shape

    physics_system.space.point_query.return_value = [mock_info]
    # Mock clear line of sight
    physics_system.space.segment_query_first.return_value = None

    # Register SectorMap
    from ..game.systems.sector_system import SectorMap
    sector_map = SectorMap(1000, 1000, 500)
    world.services.register(sector_map, SectorMap)

    # Update sector map
    sector_map.update_entity(actor, 100, 100)
    sector_map.update_entity(target, 110, 100)
    sector_map.update_entity(witness, 150, 100)

    # Trigger Event
    event = SocialInteractionEvent(
        initiator_id=actor,
        target_id=target,
        interaction_type="Fight"
    )

    # Inject world into system manually (usually done by game manager)
    gossip_system.ecs_world = world
    gossip_system.physics_system = physics_system
    gossip_system.sector_map = sector_map # Manually set for test

    # Call handler
    gossip_system.on_social_interaction(event)

    # Verify Witness got gossip
    queue = world.get_component(witness, GossipQueue)
    assert queue is not None
    assert len(queue.priority_queue) == 1
    packet = queue.priority_queue[0]
    assert packet.target_id == actor
    assert packet.event_type == "Fight"
