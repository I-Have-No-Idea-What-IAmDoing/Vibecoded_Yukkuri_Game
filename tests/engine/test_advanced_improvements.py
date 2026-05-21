"""Tests for the advanced engine architectural improvements.

This module verifies:
1. Deeper Spatial Partitioning Integration (Pymunk + Grid sectors)
2. Generic, Type-Safe ECS Queries (World.get_components_tuple overloads)
3. Strict TOML Schema Validation using msgspec
4. Physics State Visual Interpolation history tracking
"""

import os
import tempfile
from unittest.mock import MagicMock

import pymunk
import pytest

from yukkuri_game.engine.audio import AudioManager
from yukkuri_game.engine.components import (
    MovementController,
    Occluder,
    PhysicsBody,
    Transform,
)
from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.engine.systems.physics import PhysicsSystem
from yukkuri_game.engine.systems.spatial import SpatialSystem


def test_spatial_pymunk_grid_integration() -> None:
    """Verifies that SpatialService combines Pymunk and Grid entities."""
    world = World()
    event_bus = EventBus()
    world.services.register(event_bus, EventBus)

    physics_system = PhysicsSystem()
    world.add_system(physics_system)
    world.services.register(physics_system, PhysicsSystem, replace=True)
    # Register under IPhysicsService protocol
    from yukkuri_game.engine.protocols import IPhysicsService

    world.services.register(physics_system, IPhysicsService, replace=True)

    spatial_system = SpatialSystem(event_bus=event_bus)
    world.add_system(spatial_system)

    # 1. Create a physical entity
    body = pymunk.Body(1.0, 1.0)
    body.position = (100.0, 100.0)
    shape = pymunk.Circle(body, 10.0)
    physics_system.space.add(body, shape)

    phys_ent = world.create_entity(
        Transform(x=100.0, y=100.0), PhysicsBody(body=body, shape=shape)
    )

    # 2. Create a non-physical entity
    grid_ent = world.create_entity(Transform(x=120.0, y=120.0))

    # Trigger systems to process and register
    world.update(0.016)

    spatial_service = spatial_system.spatial_service
    assert spatial_service is not None

    # Query range overlapping both (100, 100) and (120, 120)
    entities = spatial_service.get_entities_in_radius(100.0, 100.0, 50.0)
    assert phys_ent in entities
    assert grid_ent in entities

    # Test get_entities_in_range
    range_entities = spatial_service.get_entities_in_range(100.0, 100.0)
    assert phys_ent in range_entities
    assert grid_ent in range_entities

    # Test get_entities_in_rect
    rect_entities = spatial_service.get_entities_in_rect(
        90.0, 90.0, 40.0, 40.0
    )
    assert phys_ent in rect_entities
    assert grid_ent in rect_entities

    # 3. Dynamic transition: Remove PhysicsBody from phys_ent
    world.remove_component(phys_ent, PhysicsBody)
    world.commands.apply_all()
    world.update(0.016)

    # Both entities should now be in the grid sectors
    assert not world.has_component(phys_ent, PhysicsBody)
    entities_post_remove = spatial_service.get_entities_in_radius(
        100.0, 100.0, 50.0
    )
    assert phys_ent in entities_post_remove
    assert grid_ent in entities_post_remove

    # 4. Dynamic transition: Add PhysicsBody back
    world.add_component(phys_ent, PhysicsBody(body=body, shape=shape))
    world.commands.apply_all()
    world.update(0.016)

    assert world.has_component(phys_ent, PhysicsBody)
    entities_post_add = spatial_service.get_entities_in_radius(
        100.0, 100.0, 50.0
    )
    assert phys_ent in entities_post_add
    assert grid_ent in entities_post_add

    world.destroy()


def test_ecs_get_components_tuple_overloads() -> None:
    """Verifies that World.get_components_tuple behaves correctly."""
    world = World()

    ent1 = world.create_entity(
        Transform(x=1.0, y=2.0), MovementController()
    )

    # 1 component query
    res1 = world.get_components_tuple(Transform)
    assert len(res1) == 1
    assert res1[0][0] == ent1
    assert isinstance(res1[0][1][0], Transform)

    # 2 component query
    res2 = world.get_components_tuple(Transform, MovementController)
    assert len(res2) == 1
    assert res2[0][0] == ent1
    assert isinstance(res2[0][1][0], Transform)
    assert isinstance(res2[0][1][1], MovementController)

    world.destroy()


def test_audio_manager_msgspec_toml() -> None:
    """Verifies AudioManager uses msgspec to validate TOML files strictly."""
    audio = AudioManager()
    if not audio.enabled:
        pytest.skip("Audio device not available for testing")

    # 1. Valid configuration
    valid_toml = """
    [sounds]
    click = "data/audio/click.wav"
    place = "data/audio/place.wav"
    """

    with tempfile.NamedTemporaryFile(suffix=".toml", delete=False) as tmp:
        tmp.write(valid_toml.encode("utf-8"))
        tmp_path = tmp.name

    try:
        # Pre-load sound file path mock to prevent actual file loading crash
        audio.load_sound = MagicMock()  # type: ignore[assignment]
        audio.load_from_config(tmp_path)

        assert audio.load_sound.call_count == 2
        audio.load_sound.assert_any_call("click", "data/audio/click.wav")
        audio.load_sound.assert_any_call("place", "data/audio/place.wav")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    # 2. Invalid configuration (invalid schema layout)
    invalid_toml = """
    [sounds]
    click = 12345
    """

    with tempfile.NamedTemporaryFile(suffix=".toml", delete=False) as tmp:
        tmp.write(invalid_toml.encode("utf-8"))
        tmp_path = tmp.name

    try:
        audio._load_fallback_sounds = MagicMock()  # type: ignore[assignment]
        audio.load_from_config(tmp_path)

        # Should fall back due to strict schema error (click is int, not str)
        audio._load_fallback_sounds.assert_called_once()
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_physics_visual_interpolation() -> None:
    """Verifies that PhysicsSystem maintains prev_x/prev_y properly."""
    world = World()
    physics_system = PhysicsSystem()
    world.add_system(physics_system)

    body = pymunk.Body(1.0, 1.0)
    body.position = (50.0, 50.0)
    shape = pymunk.Circle(body, 5.0)
    physics_system.space.add(body, shape)

    ent = world.create_entity(
        Transform(x=50.0, y=50.0), PhysicsBody(body=body, shape=shape)
    )

    # Initially, accumulator is 0.0
    physics_system.accumulator = 0.0
    trans = world.get_component(ent, Transform)

    # 1. Update with a tiny step that doesn't trigger a physics step
    # Accumulator becomes 0.005 < 0.01666
    dt = 0.005
    physics_system.update(world, dt)

    # prev_x should NOT have been updated or overwritten (should still be 50.0)
    assert trans.prev_x == 50.0
    assert trans.x == 50.0

    # Apply some velocity to the body
    body.velocity = (100.0, 0.0)

    # 2. Update with a step that triggers physics simulation step
    # Accumulator becomes 0.02 > 0.01666
    dt = 0.02
    physics_system.update(world, dt)

    # Since it ran a step, prev_x should capture the pre-simulation state (50.0)
    # and x should be updated with post-simulation body position (> 50.0)
    assert trans.prev_x == 50.0
    assert trans.x > 50.0

    world.destroy()


def test_spatial_no_duplicate_entities() -> None:
    """Verifies that physical entities with multiple shapes don't return duplicates."""
    world = World()
    event_bus = EventBus()
    world.services.register(event_bus, EventBus)

    physics_system = PhysicsSystem()
    world.add_system(physics_system)
    from yukkuri_game.engine.protocols import IPhysicsService
    world.services.register(physics_system, IPhysicsService, replace=True)

    spatial_system = SpatialSystem(event_bus=event_bus)
    world.add_system(spatial_system)

    # Create a physical entity with multiple shapes
    body = pymunk.Body(1.0, 1.0)
    body.position = (100.0, 100.0)
    shape1 = pymunk.Circle(body, 10.0, offset=(-5.0, 0.0))
    shape2 = pymunk.Circle(body, 10.0, offset=(5.0, 0.0))
    physics_system.space.add(body, shape1, shape2)

    phys_ent = world.create_entity(
        Transform(x=100.0, y=100.0),
        PhysicsBody(body=body, shape=shape1)
    )

    # Let the system register the mapping
    spatial_system.body_to_entity[body] = phys_ent

    world.update(0.016)

    spatial_service = spatial_system.spatial_service
    assert spatial_service is not None

    # Query range overlapping the entity
    entities = spatial_service.get_entities_in_radius(100.0, 100.0, 50.0)
    # Check that phys_ent is only returned once, not twice
    assert entities.count(phys_ent) == 1

    world.destroy()


def test_occluder_map_filtering() -> None:
    """Verifies that OccluderMap queries only return shadow-casting occluders."""
    world = World()
    event_bus = EventBus()
    world.services.register(event_bus, EventBus)

    physics_system = PhysicsSystem()
    world.add_system(physics_system)
    from yukkuri_game.engine.protocols import IPhysicsService
    world.services.register(physics_system, IPhysicsService, replace=True)

    spatial_system = SpatialSystem(event_bus=event_bus)
    world.add_system(spatial_system)

    # 1. Create a physical entity that has NO Occluder component
    body1 = pymunk.Body(1.0, 1.0)
    body1.position = (100.0, 100.0)
    shape1 = pymunk.Circle(body1, 10.0)
    physics_system.space.add(body1, shape1)
    non_occluder_ent = world.create_entity(
        Transform(x=100.0, y=100.0), PhysicsBody(body=body1, shape=shape1)
    )

    # 2. Create a physical entity that HAS an Occluder component
    body2 = pymunk.Body(1.0, 1.0)
    body2.position = (120.0, 120.0)
    shape2 = pymunk.Circle(body2, 10.0)
    physics_system.space.add(body2, shape2)
    occluder_ent = world.create_entity(
        Transform(x=120.0, y=120.0),
        PhysicsBody(body=body2, shape=shape2),
        Occluder()
    )

    world.update(0.016)

    occluder_map = spatial_system.occluder_map
    assert occluder_map is not None

    # Query range overlapping both physical entities (100, 100) and (120, 120)
    entities = occluder_map.get_entities_in_radius(100.0, 100.0, 50.0)

    # occluder_ent should be in the list, but non_occluder_ent should not be
    assert occluder_ent in entities
    assert non_occluder_ent not in entities

    world.destroy()
