"""
Tests for the Physics System.
"""

import pytest
from unittest.mock import patch
import pymunk
from yukkuri_game.game.systems.physics import PhysicsSystem
from yukkuri_game.game.components import Transform, PhysicsBody
from yukkuri_game.engine.ecs import World


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
