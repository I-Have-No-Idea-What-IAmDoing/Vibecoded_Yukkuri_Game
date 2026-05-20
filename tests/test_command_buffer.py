"""Tests for the ECS CommandBuffer.

This module verifies that the CommandBuffer properly defers ECS structural changes
(creating/destroying entities, adding/removing components) to the end of the frame
or until apply_all() is explicitly invoked.
"""

from unittest.mock import MagicMock

from yukkuri_game.engine.ecs import Component, World
from yukkuri_game.engine.event_bus import EventBus


class MockComponent(Component):
    """A mock component for testing ECS command buffering."""

    pass


class MockComponent2(Component):
    """A second mock component for testing multiple components."""

    pass


def test_command_buffer_create_entity() -> None:
    """Verifies that create_entity immediately returns an ID but defers component addition."""
    world = World()
    mock_event_bus = MagicMock(spec=EventBus)
    world.services.register(mock_event_bus, EventBus)

    comp1 = MockComponent()
    comp2 = MockComponent2()

    # Deferred create
    entity = world.commands.create_entity(comp1, comp2)

    # Entity ID should exist immediately
    assert world.entity_exists(entity)

    # Components should NOT be added yet
    assert not world.has_component(entity, MockComponent)
    mock_event_bus.publish.assert_not_called()

    # Apply commands
    world.commands.apply_all()

    # Now components should exist
    assert world.has_component(entity, MockComponent)
    assert world.has_component(entity, MockComponent2)

    # Events should be published
    assert mock_event_bus.publish.call_count == 2
    world.destroy()


def test_command_buffer_destroy_entity() -> None:
    """Verifies that destroy_entity defers the destruction of an entity."""
    world = World()
    entity = world.create_entity()

    world.commands.destroy_entity(entity)
    assert world.entity_exists(entity)

    world.commands.apply_all()
    assert not world.entity_exists(entity)
    world.destroy()


def test_command_buffer_add_remove_component() -> None:
    """Verifies that add_component and remove_component defer their operations."""
    world = World()
    entity = world.create_entity()
    comp = MockComponent()

    world.commands.add_component(entity, comp)
    assert not world.has_component(entity, MockComponent)

    world.commands.apply_all()
    assert world.has_component(entity, MockComponent)

    world.commands.remove_component(entity, MockComponent)
    assert world.has_component(entity, MockComponent)

    world.commands.apply_all()
    assert not world.has_component(entity, MockComponent)
    world.destroy()
