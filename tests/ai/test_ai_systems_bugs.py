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


def test_seek_light_stress_reduction(game_driver: GameDriver) -> None:
    """
    Verify that an entity in the 'SeekLight' action state correctly moves
    to a light source, calms down, and successfully resolves its stress.
    """
    from yukkuri_game.engine.components import LightSource, Transform
    from yukkuri_game.game.components import EmotionalState

    driver = game_driver
    driver.setup()

    # Set time to daytime (noon) so SeekLight doesn't remain the highest utility action at night
    time_service = driver.world.services.get(TimeService)
    time_service.time_elapsed = 12.0 * 3600.0

    # 1. Spawn a stressed Yukkuri at (100.0, 100.0)
    yukkuri_id = driver.create_yukkuri("reimu", 100.0, 100.0)
    emo = driver.world.get_component(yukkuri_id, EmotionalState)
    assert emo is not None
    emo.stress = 80.0

    # 2. Spawn a LightSource at (150.0, 150.0)
    light_ent = driver.world.create_entity()
    driver.world.add_component(
        light_ent,
        LightSource(
            radius=300.0,
            color=(255, 255, 220),
            intensity=1.0,
        ),
    )
    driver.world.add_component(light_ent, Transform(x=150.0, y=150.0))

    # Apply components queue
    driver.world.commands.apply_all()

    # Verify state before action
    trans = driver.world.get_component(yukkuri_id, Transform)
    assert trans.x == 100.0
    assert trans.y == 100.0

    # Manually tick SpatialSystem to ensure all entities are registered in the spatial index
    # before we run the behavior tree for the first time.
    from yukkuri_game.engine.systems.spatial import SpatialSystem
    spatial_sys = driver.world.get_system(SpatialSystem)
    assert spatial_sys is not None
    spatial_sys.update(driver.world, 0.016)

    # 3. Manually force SeekLight goal/action
    driver.set_ai_action(yukkuri_id, "SeekLight")

    print("STARTING TICK LOOP")
    for tick in range(100):
        driver.run_for(seconds=0.016)
        ai_comp = driver.world.get_component(yukkuri_id, AIState)
        t_comp = driver.world.get_component(yukkuri_id, Transform)
        cmd_comp = driver.world.try_get_component(yukkuri_id, MoveCommand)
        cmd_str = f"MoveCommand(target={cmd_comp.target_pos})" if cmd_comp else "No MoveCommand"
        print(f"Tick {tick}: Pos=({t_comp.x:.2f}, {t_comp.y:.2f}), Action={ai_comp.current_action}, Override={ai_comp.manual_override}, Target={ai_comp.current_target_id}, Cmd={cmd_str}")

    # Entity should be close to the light source center (150.0, 150.0)
    trans = driver.world.get_component(yukkuri_id, Transform)
    import math
    dist = math.hypot(trans.x - 150.0, trans.y - 150.0)
    print(f"DIAGNOSTIC - Yukkuri Pos: ({trans.x}, {trans.y}), Target Light: (150.0, 150.0), Dist: {dist}")
    assert dist <= 60.0  # acceptance_radius is 50.0

    # Stress should be decreasing or fully resolved
    # Wait/run until stress calms down completely (stress <= 0.0)
    driver.run_until(
        predicate=lambda: emo.stress <= 0.0,
        timeout=10.0,
        description="stress fully resolves to 0.0",
    )

    # Let the behavior tree tick once more so the UtilitySelector runs
    # with manual_override=False and selects a new action.
    # Since the entity is now "stable" (Status.SUCCESS), the BehaviorSystem
    # applies a stable tick throttling multiplier (3.0x), making the minimum tick
    # interval 0.3s. We run for 0.5s to ensure a tick is executed.
    driver.run_for(seconds=0.5)

    # After stress is 0, the CalmAtLight action finishes with Status.SUCCESS
    # and the utility selector will select Wander or Idle
    ai = driver.world.get_component(yukkuri_id, AIState)
    assert ai.current_action != "SeekLight"


def test_pathfinding_failed_recovery(game_driver: GameDriver) -> None:
    """
    Verify that an entity handles a failed pathfinding result correctly.

    The entity must return Status.FAILURE on its next movement behavior tick
    when pathfinding fails and path_requesting is False, clearing transient
    keys and successfully picking a new action (e.g. Wander or Idle) instead
    of softlocking in Status.RUNNING indefinitely.
    """
    driver = game_driver
    driver.setup()

    # Create a Reimu yukkuri
    yukkuri_id = driver.create_yukkuri("reimu", 100.0, 100.0)

    # Spawn an item to act as food (so target is valid)
    from yukkuri_game.game.components import ItemStats
    from yukkuri_game.engine.components import Transform
    food_id = driver.world.create_entity()
    driver.world.add_component(food_id, Transform(x=500.0, y=500.0))
    driver.world.add_component(
        food_id,
        ItemStats(
            name="Beanpaste Food",
            type_id="beanpaste",
            cost=10,
            nutrition=50.0,
        ),
    )
    driver.world.commands.apply_all()

    # Manually tick SpatialSystem to register food in spatial index
    from yukkuri_game.engine.systems.spatial import SpatialSystem
    spatial_sys = driver.world.get_system(SpatialSystem)
    assert spatial_sys is not None
    spatial_sys.update(driver.world, 0.016)

    # Set manual override action to force Eat with food_id as the target
    driver.set_ai_action(yukkuri_id, "Eat", food_id)

    # Let the system run to locate the food and request a path first
    driver.run_for(seconds=0.016)

    # Verify that the food was indeed targeted
    ai = driver.world.get_component(yukkuri_id, AIState)
    assert ai is not None
    assert ai.current_target_id == food_id

    # Simulate pathfinding failing by injecting a failed PathResult into
    # NavigationService. This is exactly how NavigationSystem gets failures.
    from yukkuri_game.game.ai.navigation_service import (
        NavigationService,
        PathResult,
    )
    import queue
    nav_service = driver.world.services.get(NavigationService)

    # Drain any successful results or pending requests
    for q in (nav_service.result_queue, nav_service.request_queue):
        try:
            while True:
                q.get_nowait()
        except queue.Empty:
            pass

    # Inject the failed pathfinding result
    ai.path = None
    nav_service.result_queue.put(
        PathResult(entity_id=yukkuri_id, path=[], success=False)
    )

    # Tick BehaviorSystem again. navigate_to should process this
    # pathfinding failure, return Status.FAILURE, and clear flags
    driver.run_for(seconds=0.1)

    # Check that failed target was registered in failed_targets
    assert food_id in ai.failed_targets
    assert not ai.state_data.get("path_failed")
    assert not ai.state_data.get("path_requesting")

    # Reset hunger and stress to 0.0 so that the UtilitySelector selects Wander
    # or Idle instead of Eat or triggering a Stress Break (Panic Freeze)
    needs = driver.world.get_component(yukkuri_id, Needs)
    needs.hunger = 0.0
    from yukkuri_game.game.components import EmotionalState
    emo = driver.world.get_component(yukkuri_id, EmotionalState)
    if emo:
        emo.stress = 0.0

    # Let the behavior system tick again so that it recovers
    # and selects a different action (e.g. Wander or Idle) since Eat failed
    driver.run_for(seconds=0.5)

    # Confirm the entity has no active MoveCommand (has stopped attempting to move)
    assert not driver.world.has_component(yukkuri_id, MoveCommand)

    # Confirm we recovered and transitioned away from the Eat action
    assert ai.current_action != "Eat"





