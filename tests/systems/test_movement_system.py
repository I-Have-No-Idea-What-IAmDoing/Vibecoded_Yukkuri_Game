
import math
import pymunk
from pymunk.vec2d import Vec2d as Vector2
import pytest

from src.yukkuri_game.engine.ecs import World
from src.yukkuri_game.game.components import (
    PhysicsBody,
    MovementController,
    VisualTransform,
)
from src.yukkuri_game.game.systems.movement_system import MovementSystem

@pytest.fixture
def world_with_entity():
    """Creates a World and a test entity with required components."""
    world = World()
    entity = world.create_entity()

    # Create a dummy physics body
    body = pymunk.Body(1, 100)
    shape = pymunk.Circle(body, 10)

    world.add_component(entity, PhysicsBody(body, shape))
    world.add_component(entity, MovementController())
    world.add_component(entity, VisualTransform())

    return world, entity

def test_velocity_is_applied(world_with_entity):
    """Tests that the target_velocity from MovementController is applied to the PhysicsBody."""
    world, entity = world_with_entity
    movement_system = MovementSystem()

    controller = world.get_component(entity, MovementController)
    phys_body = world.get_component(entity, PhysicsBody)

    # Set a target velocity
    target_vel = Vector2(100, -50)
    controller.target_velocity = target_vel

    # Run the system
    movement_system.update(world, dt=0.1)

    # Assert
    assert phys_body.body.velocity == target_vel

def test_visual_bob_timer_advances_on_move(world_with_entity):
    """Tests that the visual_bob_timer increases when the entity is moving."""
    world, entity = world_with_entity
    movement_system = MovementSystem()

    controller = world.get_component(entity, MovementController)
    controller.target_velocity = Vector2(100, 0)
    initial_timer = controller.visual_bob_timer

    # Run the system
    movement_system.update(world, dt=0.1)

    # Assert
    assert controller.visual_bob_timer > initial_timer

def test_visual_bob_timer_is_stationary(world_with_entity):
    """Tests that the visual_bob_timer does not increase when the entity is not moving."""
    world, entity = world_with_entity
    movement_system = MovementSystem()

    controller = world.get_component(entity, MovementController)
    controller.target_velocity = Vector2(0, 0)
    initial_timer = controller.visual_bob_timer

    # Run the system
    movement_system.update(world, dt=0.1)

    # Assert
    assert controller.visual_bob_timer == initial_timer

def test_vertical_offset_is_calculated(world_with_entity):
    """Tests that the vertical_offset is calculated based on the bobbing timer."""
    world, entity = world_with_entity
    movement_system = MovementSystem()

    controller = world.get_component(entity, MovementController)
    visual_transform = world.get_component(entity, VisualTransform)

    controller.target_velocity = Vector2(100, 0)
    controller.bob_height = 15.0
    controller.bob_speed = 5.0

    # Run the system
    movement_system.update(world, dt=0.1)

    # Manually calculate the expected offset
    expected_timer = 0.1 * 5.0
    expected_offset = abs(math.sin(expected_timer)) * 15.0

    # Assert
    assert visual_transform.vertical_offset == pytest.approx(expected_offset)

def test_shadow_position_is_synced(world_with_entity):
    """Tests that the shadow_position is updated to match the PhysicsBody's position."""
    world, entity = world_with_entity
    movement_system = MovementSystem()

    phys_body = world.get_component(entity, PhysicsBody)
    visual_transform = world.get_component(entity, VisualTransform)

    # Set a position for the physics body
    phys_body.body.position = Vector2(123, 456)

    # Run the system
    movement_system.update(world, dt=0.1)

    # Assert
    assert visual_transform.shadow_position == phys_body.body.position
