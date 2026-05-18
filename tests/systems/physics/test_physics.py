"""
Tests for the Physics System.
"""

import pytest
from unittest.mock import patch
import pymunk
from yukkuri_game.engine.systems.physics import PhysicsSystem
from yukkuri_game.engine.components import Transform, PhysicsBody
from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.events import EntityDestroyedEvent, PhysicsFixedUpdateEvent
from yukkuri_game.engine.event_bus import EventBus


@pytest.fixture
def physics_system() -> PhysicsSystem:
    """
    Creates a PhysicsSystem with defined gravity.
    """
    return PhysicsSystem(gravity=(0, 10))


def test_init(physics_system: PhysicsSystem) -> None:
    """
    Tests initialization of the PhysicsSystem.
    """
    assert physics_system.space.gravity == (0, 10)
    assert physics_system.accumulator == 0.0
    assert physics_system.time_step == 1.0 / 60.0
    assert physics_system.space.damping == 0.9


def test_update_step(physics_system: PhysicsSystem) -> None:
    """
    Tests that the physics simulation steps correctly when sufficient time passes.
    """
    world = World()

    # Mock space.step
    with patch.object(physics_system.space, "step") as mock_step:
        # Update with exactly one time step
        physics_system.update(world, 1.0 / 60.0)
        mock_step.assert_called_once_with(1.0 / 60.0)
        assert physics_system.accumulator == 0.0


def test_update_accumulator(physics_system: PhysicsSystem) -> None:
    """
    Tests that the accumulator handles partial time steps correctly.
    """
    world = World()

    with patch.object(physics_system.space, "step") as mock_step:
        # Update with half a time step
        physics_system.update(world, 1.0 / 120.0)
        mock_step.assert_not_called()
        assert physics_system.accumulator == 1.0 / 120.0

        # Update with another half
        physics_system.update(world, 1.0 / 120.0)
        # Should trigger step now (approx)
        mock_step.assert_called_once_with(1.0 / 60.0)
        # Accumulator might be slightly off due to float precision but should be close to 0


def test_sync_transform(physics_system: PhysicsSystem) -> None:
    """
    Tests that physics body positions are synced to Transform components.
    """
    world = World()

    # Create an entity with PhysicsBody and Transform
    entity = world.create_entity()

    body = pymunk.Body(1, 1)
    body.position = (10, 20)
    phys_component = PhysicsBody(body=body, shape=pymunk.Circle(body, 10))

    trans_component = Transform(x=0, y=0)

    world.add_component(entity, phys_component)
    world.add_component(entity, trans_component)

    # Run update (force step)
    physics_system.update(world, 1.0 / 60.0)

    # Transform should be updated to match body position
    assert trans_component.x == 10
    assert trans_component.y == 20


def test_clear_space(physics_system: PhysicsSystem) -> None:
    """
    Tests that the clear method removes bodies, shapes, and constraints.
    """
    body = pymunk.Body(1, 1)
    shape = pymunk.Circle(body, 10)
    physics_system.space.add(body, shape)

    # Add a constraint
    static_body = physics_system.space.static_body
    constraint = pymunk.PinJoint(body, static_body)
    physics_system.space.add(constraint)

    assert len(physics_system.space.bodies) == 1
    assert len(physics_system.space.shapes) == 1
    assert len(physics_system.space.constraints) == 1

    physics_system.clear()

    assert len(physics_system.space.bodies) == 0
    assert len(physics_system.space.shapes) == 0
    assert len(physics_system.space.constraints) == 0


def test_on_entity_destroyed(physics_system: PhysicsSystem) -> None:
    """
    Tests that physics components are removed when an entity is destroyed.
    """
    world = World()

    # Inject world into system (as it would be by World.add_system)
    physics_system.ecs_world = world

    # Create an entity with PhysicsBody
    entity = world.create_entity()
    body = pymunk.Body(1, 1)
    shape = pymunk.Circle(body, 10)
    phys_component = PhysicsBody(body=body, shape=shape)

    world.add_component(entity, phys_component)
    physics_system.space.add(body, shape)

    assert body in physics_system.space.bodies
    assert shape in physics_system.space.shapes

    # Trigger EntityDestroyedEvent
    event = EntityDestroyedEvent(entity_id=entity)
    physics_system.on_entity_destroyed(event)

    # Body and shape should be removed from space
    assert body not in physics_system.space.bodies
    assert shape not in physics_system.space.shapes


def test_on_entity_destroyed_wrong_event(physics_system: PhysicsSystem) -> None:
    """
    Tests that on_entity_destroyed ignores other event types.
    """
    # Should simply do nothing and return
    physics_system.on_entity_destroyed(PhysicsFixedUpdateEvent(dt=0.1))


def test_update_max_frame_time(physics_system: PhysicsSystem) -> None:
    """
    Tests that dt is clamped to max_frame_time.
    """
    world = World()

    with patch.object(physics_system.space, "step") as mock_step:
        # Pass a very large dt
        large_dt = 10.0
        physics_system.update(world, large_dt)

        # Accumulator should have increased by max_frame_time (0.25), not large_dt
        # And steps should have occurred. 0.25 / (1/60) = 15 steps

        expected_steps = int(0.25 / (1.0 / 60.0))
        assert mock_step.call_count == expected_steps


def test_update_publishes_event(physics_system: PhysicsSystem) -> None:
    """
    Tests that PhysicsFixedUpdateEvent is published during steps.
    """
    world = World()
    event_bus = EventBus()
    world.services.register(event_bus, EventBus)

    physics_system.update(world, 0)  # Initialize event_bus in system

    received_events = []

    def on_fixed_update(event: PhysicsFixedUpdateEvent):
        received_events.append(event)

    event_bus.subscribe(PhysicsFixedUpdateEvent, on_fixed_update)

    # Step once
    # We use a slightly larger dt to ensure floating point issues don't prevent the loop from running
    physics_system.update(world, 1.0 / 60.0 + 0.0001)

    assert len(received_events) == 1
    assert received_events[0].dt == 1.0 / 60.0
