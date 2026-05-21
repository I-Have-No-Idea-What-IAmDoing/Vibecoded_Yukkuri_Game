"""
Regression test suite for AI, Systems, and Architectural bugfixes.
"""

import pymunk
from py_trees.common import Status

from yukkuri_game.engine.components import MovementController
from yukkuri_game.engine.services.time_service import TimeService
from yukkuri_game.game.components import MoveCommand, Needs, AIState
from yukkuri_game.game.systems.behavior import BehaviorSystem
from yukkuri_game.testing.driver import GameDriver


def test_new_entity_paralysis(game_driver: GameDriver) -> None:
    """
    Verify that newly spawned AI entities tick on their first frame of existence.
    """
    driver = game_driver
    driver.setup()

    # Spawn a fresh AI entity
    yukkuri_id = driver.create_yukkuri("reimu", 100.0, 100.0)

    # Run for 1 single physics frame (0.016s) to trigger system detection and tick
    driver.run_for(seconds=0.016)

    # Get BehaviorSystem
    behavior_sys = driver.world.get_system(BehaviorSystem)
    assert behavior_sys is not None

    # Verify that the entity has been added to last_update_times
    assert yukkuri_id in behavior_sys.last_update_times

    # Verify that the entity's behavior tree ticked immediately in the first frame
    # (its status is not py_trees.common.Status.INVALID)
    tree = behavior_sys.trees[yukkuri_id]
    assert tree.root.status != Status.INVALID


def test_deferred_command_race_condition(game_driver: GameDriver) -> None:
    """
    Verify that when a MoveCommand is queued for removal, SteeringSystem does

    not overwrite the brain's zeroed target velocity in the same frame.
    """
    driver = game_driver
    driver.setup()

    # Create a yukkuri
    yukkuri_id = driver.create_yukkuri("reimu", 100.0, 100.0)

    # Give it a MoveCommand
    move_cmd = MoveCommand(
        target_pos=pymunk.Vec2d(300, 300),
        active=True
    )
    driver.world.commands.add_component(yukkuri_id, move_cmd)
    driver.world.commands.apply_all()

    # Verify component exists
    assert driver.world.has_component(yukkuri_id, MoveCommand)

    # Simulate behavior action stopping the entity:
    # 1. Queue component removal
    driver.world.commands.remove_component(yukkuri_id, MoveCommand)

    # Verify it was immediately set to inactive
    retrieved_cmd = driver.world.get_component(yukkuri_id, MoveCommand)
    assert retrieved_cmd.active is False

    # 2. Directly zero the controller target velocity
    controller = driver.world.get_component(yukkuri_id, MovementController)
    assert controller is not None
    controller.target_velocity = pymunk.Vec2d(0, 0)

    # Run world systems update (which triggers SteeringSystem, then commands)
    driver.world.update(0.016)

    # Verify target velocity remained exactly (0, 0) and command is removed
    assert controller.target_velocity == pymunk.Vec2d(0, 0)
    assert not driver.world.has_component(yukkuri_id, MoveCommand)


def test_ai_starvation() -> None:
    """
    Verify that BehaviorSystem.max_updates_per_frame scales dynamically
    with the queue length to prevent AI update starvation under load.
    """
    from yukkuri_game.engine.ecs import World
    from yukkuri_game.config import (
        GameConfig,
        WorldSettings,
        TimeSettings,
        RulesFile,
    )

    world = World()
    world_settings = WorldSettings(width=2000, height=2000)
    time_settings = TimeSettings()
    rules_settings = RulesFile()
    config = GameConfig(
        world=world_settings,
        time=time_settings,
        rules=rules_settings,
    )
    world.services.register(config)

    behavior_sys = BehaviorSystem()
    world.add_system(behavior_sys)

    # Baseline with empty queue
    assert behavior_sys.max_updates_per_frame == 10

    # Fill queue with mock entities
    for i in range(120):
        behavior_sys.update_queue.append(i)

    # Update behavior system
    behavior_sys.update(world, 0.016)

    # Expected: max(10, (120 + 5) // 6) = max(10, 20) = 20
    assert behavior_sys.max_updates_per_frame == 20


def test_double_scaling(game_driver: GameDriver) -> None:
    """
    Verify that sleep energy recovery scales linearly, not quadratically,

    with game speed.
    """
    driver = game_driver
    driver.setup()

    # Test at 1.0x speed
    time_service = driver.world.services.get(TimeService)
    time_service.game_speed = 1.0

    yukkuri_1 = driver.create_yukkuri("reimu", 100.0, 100.0)
    needs_1 = driver.world.get_component(yukkuri_1, Needs)
    needs_1.energy = 50.0

    # Put to sleep
    driver.set_ai_action(yukkuri_1, "Sleep")
    driver.run_for(seconds=1.0)
    recovery_1x = needs_1.energy - 50.0

    # Test at 2.0x speed
    time_service.game_speed = 2.0
    yukkuri_2 = driver.create_yukkuri("reimu", 150.0, 150.0)
    needs_2 = driver.world.get_component(yukkuri_2, Needs)
    needs_2.energy = 50.0

    driver.set_ai_action(yukkuri_2, "Sleep")
    driver.run_for(seconds=1.0)  # 1s real time at 2x speed = 2s simulated time
    recovery_2x = needs_2.energy - 50.0

    # With linear scaling, recovery at 2.0x speed should be exactly double
    # the recovery at 1.0x speed. If it was quadratically double scaled,
    # recovery_2x would be 4x of recovery_1x.
    assert abs(recovery_2x - 2.0 * recovery_1x) < 0.5


def test_needs_clamping() -> None:
    """
    Verify that the Needs component automatically clamps physiological needs

    and health boundaries at the property assignment level.
    """
    needs = Needs(energy=95.0)

    # Direct over-clamp
    needs.energy = 150.0
    assert needs.energy == 100.0

    # Direct under-clamp
    needs.energy = -50.0
    assert needs.energy == 0.0

    # Relative operations trigger clamping
    needs.energy = 90.0
    needs.energy += 20.0
    assert needs.energy == 100.0

    # Health clamped to max_health
    needs.max_health = 120.0
    needs.health = 130.0
    assert needs.health == 120.0

    # Max health reduction clamps current health
    needs.max_health = 80.0
    assert needs.health == 80.0
