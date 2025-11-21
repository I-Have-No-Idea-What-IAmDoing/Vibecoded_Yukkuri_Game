
import pytest
from src.yukkuri_game.engine.ecs import World
from src.yukkuri_game.game.components import Sprite, Animator
from src.yukkuri_game.engine.data_models import AnimationDefinition
from src.yukkuri_game.game.systems.animation import AnimationSystem

def test_animator_update_size_override():
    world = World()
    system = AnimationSystem()

    # Define animations with size override
    small_anim = AnimationDefinition(
        name="small",
        frames=[0],
        frame_duration=1.0,
        loop=True,
        width=32,
        height=32
    )

    big_anim = AnimationDefinition(
        name="big",
        frames=[0],
        frame_duration=1.0,
        loop=True,
        width=64,
        height=64,
        image="big_sprite.png"
    )

    animations = {"small": small_anim, "big": big_anim}

    # Create entity with initial small animation
    animator = Animator(
        animations=animations,
        current_animation="small"
    )
    sprite = Sprite(
        image_name="test.png",
        width=10,
        height=10
    )

    entity = world.create_entity()
    world.add_component(entity, animator)
    world.add_component(entity, sprite)

    # First update should apply "small" override
    system.update(world, 0.1)
    assert sprite.width == 32
    assert sprite.height == 32
    assert sprite.image_name == "test.png" # No override in small

    # Switch to "big"
    animator.current_animation = "big"
    system.update(world, 0.1)
    assert sprite.width == 64
    assert sprite.height == 64
    assert sprite.image_name == "big_sprite.png"

    # Switch back to "small"
    animator.current_animation = "small"
    system.update(world, 0.1)
    assert sprite.width == 32
    assert sprite.height == 32
    # Note: "small" does not have 'image' override, so 'image_name' remains "big_sprite.png"
    # This is the expected behavior of "override if present".
    # If we wanted to revert, we'd need to store base state or enforce explicit state.
    # Given the current implementation, this is correct.
    assert sprite.image_name == "big_sprite.png"

def test_animator_looping():
    world = World()
    system = AnimationSystem()

    loop_anim = AnimationDefinition(
        name="loop",
        frames=[0, 1],
        frame_duration=0.1,
        loop=True
    )

    animator = Animator(animations={"loop": loop_anim}, current_animation="loop")
    sprite = Sprite(image_name="t.png", width=32, height=32)

    entity = world.create_entity()
    world.add_component(entity, animator)
    world.add_component(entity, sprite)

    # Frame 0
    system.update(world, 0.05)
    assert sprite.current_frame == 0

    # Frame 1 (0.05 + 0.06 = 0.11)
    system.update(world, 0.06)
    assert sprite.current_frame == 1

    # Wrap to 0 (0.11 + 0.1 = 0.21) -> 2 frames passed -> index 0
    system.update(world, 0.1)
    assert sprite.current_frame == 0
