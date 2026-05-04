from unittest.mock import MagicMock
from test_utils import make_configured_world
from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.game.systems.animation import AnimationSystem
from yukkuri_game.game.components import Sprite, Animator
from yukkuri_game.game.yukkuri_components import AIState
from yukkuri_game.engine.data_models import AnimationDefinition


def test_animation_event_trigger():
    world = make_configured_world()
    event_bus = world.services.get(EventBus)
    event_bus.publish = MagicMock()
    
    system = AnimationSystem()
    world.add_system(system)

    # Define animation with event
    anim_def = AnimationDefinition(
        name="attack", frames=[0, 1, 2], frame_duration=0.1, events={1: "hit"}
    )

    animator = Animator(animations={"attack": anim_def}, current_animation="attack")
    sprite = Sprite("img.png", width=32, height=32)

    entity = world.create_entity()
    world.add_component(entity, animator)
    world.add_component(entity, sprite)

    # Advance to frame 1
    # Current time 0. Need 0.1 to pass frame 0.
    system.update(world, 0.12)  # Should advance to frame 1

    assert event_bus.publish.called
    args, _ = event_bus.publish.call_args
    event = args[0]
    assert event.event_type == "hit"
    assert event.frame_index == 1


def test_sync_ai_animation():
    world = make_configured_world()
    system = AnimationSystem()
    world.add_system(system)

    anim_def_idle = AnimationDefinition(name="idle", frames=[0], frame_duration=1.0)
    anim_def_walk = AnimationDefinition(
        name="move", frames=[1, 2], frame_duration=1.0
    )  # AI action "Move" -> lower "move"

    animator = Animator(
        animations={"idle": anim_def_idle, "move": anim_def_walk},
        current_animation="idle",
    )
    sprite = Sprite("img.png", width=32, height=32)
    ai = AIState(current_action="Move")

    entity = world.create_entity()
    world.add_component(entity, animator)
    world.add_component(entity, sprite)
    world.add_component(entity, ai)

    system.update(world, 0.1)

    assert animator.current_animation == "move"


def test_auto_transition():
    world = make_configured_world()
    system = AnimationSystem()
    world.add_system(system)

    # Anim 1: plays once then transitions to Anim 2
    anim1 = AnimationDefinition(
        name="start", frames=[0], frame_duration=0.1, loop=False
    )

    anim2 = AnimationDefinition(name="loop", frames=[1], frame_duration=0.1, loop=True)

    animator = Animator(
        animations={"start": anim1, "loop": anim2},
        current_animation="start",
        next_animation="loop",
    )
    sprite = Sprite("img.png", width=32, height=32)

    entity = world.create_entity()
    world.add_component(entity, animator)
    world.add_component(entity, sprite)

    # Finish anim1
    system.update(world, 0.15)

    assert animator.current_animation == "loop"
    assert animator.current_frame_index == 0


def test_ping_pong_animation():
    world = make_configured_world()
    system = AnimationSystem()
    world.add_system(system)

    anim = AnimationDefinition(
        name="pingpong", frames=[0, 1, 2], frame_duration=0.1, ping_pong=True
    )

    animator = Animator(animations={"pingpong": anim}, current_animation="pingpong")
    sprite = Sprite("img.png", width=32, height=32)

    entity = world.create_entity()
    world.add_component(entity, animator)
    world.add_component(entity, sprite)

    # 0 -> 1
    system.update(world, 0.11)
    assert animator.current_frame_index == 1
    assert animator.forward

    # 1 -> 2
    system.update(world, 0.11)
    assert animator.current_frame_index == 2
    assert animator.forward

    # 2 -> 1 (Ping Pong back)
    system.update(world, 0.11)
    assert animator.current_frame_index == 1
    assert not animator.forward

    # 1 -> 0
    system.update(world, 0.11)
    assert animator.current_frame_index == 0
    assert not animator.forward

    # 0 -> 1 (Ping Pong forward again)
    system.update(world, 0.11)
    assert animator.current_frame_index == 1
    assert animator.forward
