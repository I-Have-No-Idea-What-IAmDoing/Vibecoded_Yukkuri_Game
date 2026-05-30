"""
Regression test suite for AI, Systems, and Architectural bugfixes.
"""

import pymunk
from py_trees.common import Status

from yukkuri_game.engine.components import MovementController, Transform
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


def test_navigation_overlap_arrival_deadlock(game_driver: GameDriver) -> None:
    """
    Verify that an entity trying to reach another entity with an acceptance
    radius smaller than their physical radii sum (collision distance)
    successfully arrives and stops rather than deadlocking in Status.RUNNING.
    """
    driver = game_driver
    driver.setup()

    # Spawn two Adult Yukkuris (radius 20 each, so physical overlap is 40)
    # Spawn them 100px apart
    y1_id = driver.create_yukkuri("reimu", 100.0, 100.0)
    y2_id = driver.create_yukkuri("reimu", 200.0, 100.0)

    # Apply components queue
    driver.world.commands.apply_all()

    # Verify initial distance
    import math
    from yukkuri_game.engine.components import Transform
    trans1 = driver.world.get_component(y1_id, Transform)
    trans2 = driver.world.get_component(y2_id, Transform)
    assert math.hypot(trans2.x - trans1.x, trans2.y - trans1.y) == 100.0

    # Put y1 into "Talk" action targeting y2.
    # Talk has MoveToTarget with acceptance_radius=30.0 (< 40 overlap).
    driver.set_ai_action(y1_id, "Talk", y2_id)
    driver.set_ai_action(y2_id, "Idle")
    
    # Run the simulation until they are close (physical collision contact) and
    # they successfully arrive (which triggers MoveToTarget SUCCESS).
    driver.run_until(
        predicate=lambda: math.hypot(
            trans2.x - trans1.x, trans2.y - trans1.y
        ) < 45.0,
        timeout=5.0,
        description="Yukkuris reach close physical proximity",
    )
    
    # Let it tick a few more times to complete the MoveToTarget node
    driver.run_for(seconds=0.2)
    
    # Verify they did not get stuck in a direct-steering collision deadlock
    # and they successfully stopped moving (target_velocity becomes 0)
    from yukkuri_game.engine.components import MovementController
    ctrl = driver.world.get_component(y1_id, MovementController)
    assert ctrl.target_velocity.length < 1.0


def test_behavior_tree_goal_switching_cleanup(game_driver: GameDriver) -> None:
    """
    Verify that when an entity's goal dynamically changes, the previous goal
    sequence (e.g. Wander) is correctly aborted and cleans up target states,
    rather than bypassing goal checks and running indefinitely.
    """
    driver = game_driver
    driver.setup()

    y_id = driver.create_yukkuri("reimu", 100.0, 100.0)
    driver.world.commands.apply_all()

    # 1. Set goal to Wander
    driver.set_ai_action(y_id, "Wander")
    
    # 2. Tick to initialize Wander
    driver.run_for(seconds=0.2)

    # 3. Verify Wander target is set in ai.state_data
    ai = driver.world.get_component(y_id, AIState)
    assert ai.state_data is not None
    assert "target_x" in ai.state_data
    assert "target_y" in ai.state_data

    # 4. Programmatically switch action to Idle
    driver.set_ai_action(y_id, "Idle")

    # 5. Tick behavioral system to run the tree
    driver.run_for(seconds=0.2)

    # 6. Verify state_data is cleaned up and target coords are popped
    assert "target_x" not in ai.state_data
    assert "target_y" not in ai.state_data
    assert "path_destination" not in ai.state_data


def test_same_cell_navigation_no_cell_center_loop(
    game_driver: GameDriver,
) -> None:
    """
    Verify that when navigating to a target in the same grid cell, the returned
    path contains the exact target world coordinates, rather than the grid cell
    center. This prevents the entity from looping back and forth to the center.
    """
    driver = game_driver
    driver.setup()

    y_id = driver.create_yukkuri("reimu", 100.0, 100.0)
    driver.world.commands.apply_all()

    # Get components
    ai = driver.world.get_component(y_id, AIState)

    # Call navigate_to directly targeting a point in the same cell
    # (both (100.0, 100.0) and (115.0, 120.0) convert to cell (2, 2))
    from yukkuri_game.game.ai.navigation_controller import NavigationController
    from py_trees.common import Status
    import pymunk

    target_pos = pymunk.Vec2d(115.0, 120.0)

    # The first call will request the path async
    status = NavigationController.navigate_to(
        world=driver.world,
        entity_id=y_id,
        target_pos=target_pos,
        target_entity_id=999,
        speed=100.0,
        acceptance_radius=5.0,
    )
    assert status == Status.RUNNING
    assert ai.state_data is not None
    assert ai.state_data.get("path_requesting") is True

    # Process pathfinding queue deterministic update
    from yukkuri_game.game.ai.navigation_service import NavigationService
    nav_service = driver.world.services.get(NavigationService)
    nav_service.update(driver.world.time)

    # Retrieve results in NavigationSystem
    from yukkuri_game.game.systems.navigation_system import NavigationSystem
    nav_system = driver.world.get_system(NavigationSystem)
    nav_system.update(driver.world, 0.016)

    # Verify path is computed and contains the exact end coordinates
    assert ai.path is not None
    assert len(ai.path) > 0
    assert ai.path[-1] == (115.0, 120.0)


def test_same_cell_navigation_infinite_loop_deadlock(
    game_driver: GameDriver,
) -> None:
    """
    Verify that when navigating to a target in the same grid cell with an
    acceptance radius smaller than 10px (e.g. 5px), the entity does not get
    stuck in an infinite loop of path requests due to the passive
    SteeringSystem prematurely deleting/popping the final path waypoint.
    """
    driver = game_driver
    driver.setup()

    y_id = driver.create_yukkuri("reimu", 100.0, 100.0)
    driver.world.commands.apply_all()

    ai = driver.world.get_component(y_id, AIState)

    from yukkuri_game.game.ai.navigation_controller import NavigationController
    from py_trees.common import Status
    import pymunk

    # Place target at 108.0, 100.0 (8px away, within same cell and < 10px)
    target_pos = pymunk.Vec2d(108.0, 100.0)

    # Frame 1: Call navigate_to directly to request the path async
    status = NavigationController.navigate_to(
        world=driver.world,
        entity_id=y_id,
        target_pos=target_pos,
        target_entity_id=999,
        speed=100.0,
        acceptance_radius=5.0,
    )
    assert status == Status.RUNNING
    assert ai.state_data.get("path_requesting") is True

    # Frame 2: Process pathfinding queue deterministic update
    from yukkuri_game.game.ai.navigation_service import NavigationService
    nav_service = driver.world.services.get(NavigationService)
    nav_service.update(driver.world.time)

    # Retrieve results in NavigationSystem
    from yukkuri_game.game.systems.navigation_system import NavigationSystem
    nav_system = driver.world.get_system(NavigationSystem)
    nav_system.update(driver.world, 0.016)

    # Path is now set and is of length 1
    assert ai.path is not None
    assert len(ai.path) == 1

    # Frame 2: Run SteeringSystem.
    # It calculates steering force.
    # If the bug exists, SteeringSystem will see dist_sq < 100.0 and pop the
    # last waypoint immediately, setting ai.path = None in the exact same frame!
    from yukkuri_game.game.systems.steering_system import SteeringSystem
    steering_system = driver.world.get_system(SteeringSystem)
    steering_system.update(driver.world, 0.016)

    # Frame 3: Call navigate_to again.
    # If the bug is present, because ai.path was deleted, navigate_to will NOT
    # return success or continue moving; it will start a NEW path request!
    # Let's assert that the path remains intact so it continues moving,
    # rather than being cleared and starting a new request!
    assert ai.path is not None, "Path was prematurely cleared"
    assert not ai.state_data.get("path_requesting"), "Re-requested path"


def test_wander_acceptance_radius_boundary_stuck(
    game_driver: GameDriver,
) -> None:
    """
    Verify that the Wander action uses an acceptance radius (e.g. 35.0px) that
    safely exceeds the default physical body radius of Adult Yukkuris (20.0px).
    This ensures that when a target coordinate is generated close to a boundary
    obstacle, physical collision contact does not permanently block and
    paralyze the entity's path/wander progression.
    """
    driver = game_driver
    driver.setup()

    y_id = driver.create_yukkuri("reimu", 100.0, 100.0)
    driver.world.commands.apply_all()

    # Trigger Wander action
    driver.set_ai_action(y_id, "Wander")
    driver.run_for(seconds=0.1)

    # Resolve behavior tree to find Wander child
    from yukkuri_game.game.systems.behavior import BehaviorSystem
    behavior_sys = driver.world.get_system(BehaviorSystem)
    tree = behavior_sys.trees[y_id]
    
    # Recursively find the Wander action node in the behavior tree
    def find_wander(node):
        if node.__class__.__name__ == "Wander":
            return node
        if hasattr(node, "children"):
            for child in node.children:
                w = find_wander(child)
                if w is not None:
                    return w
        if hasattr(node, "child"):
            return find_wander(node.child)
        return None

    wander_node = find_wander(tree.root)
    assert wander_node is not None, "Wander behavior node not found in tree"

    # Assert that the Wander action's acceptance radius is set to 35.0 (or at least > 25.0)
    # to comfortably clear the Adult physical radius (20.0px)
    assert wander_node.acceptance_radius >= 30.0, (
        f"Wander acceptance radius ({wander_node.acceptance_radius}) is too small, "
        "could cause boundary deadlocks."
    )
    
    # Verify that the underlying MoveToTarget is constructed with this acceptance radius
    assert wander_node.move_action is not None, "MoveToTarget action not initialized"
    assert wander_node.move_action.acceptance_radius == wander_node.acceptance_radius


def test_empty_path_list_deadlock(game_driver: GameDriver) -> None:
    """
    Verify that an entity with an empty path list ([]) does not deadlock.

    Treating an empty list as None should correctly trigger a new async
    path request on the subsequent tick rather than trapping the Yukkuri in
    RUNNING indefinitely with zero target velocity.
    """
    driver = game_driver
    driver.setup()

    # Create a Reimu yukkuri
    y_id = driver.create_yukkuri("reimu", 100.0, 100.0)
    driver.world.commands.apply_all()

    ai = driver.world.get_component(y_id, AIState)
    assert ai is not None

    # Manually inject an empty path list
    ai.path = []

    # Target position is far away (500, 500)
    target_pos = pymunk.Vec2d(500.0, 500.0)

    # Call navigate_to directly with empty path
    from yukkuri_game.game.ai.navigation_controller import NavigationController

    status = NavigationController.navigate_to(
        world=driver.world,
        entity_id=y_id,
        target_pos=target_pos,
        target_entity_id=None,
        speed=100.0,
        acceptance_radius=40.0,
    )

    # It must successfully request a path rather than bypassing it
    assert status == Status.RUNNING
    assert ai.state_data is not None
    assert ai.state_data.get("path_requesting") is True


def test_wander_unreachable_target_recovery(
    game_driver: GameDriver,
) -> None:
    """
    Verify that when navigating to an unreachable target, if the entity
    reaches the end of the partial path (closest reachable point), the action
    successfully completes (Status.SUCCESS) instead of deadlocking in
    Status.RUNNING.
    """
    driver = game_driver
    driver.setup()

    yukkuri_id = driver.create_yukkuri("reimu", 200.0, 100.0)
    driver.world.commands.apply_all()

    ai = driver.world.get_component(yukkuri_id, AIState)
    assert ai is not None

    # Original target is at (700, 100), but path only gets us to (200, 100)
    target_pos = pymunk.Vec2d(700.0, 100.0)
    ai.state_data = {"target_x": 700.0, "target_y": 100.0}
    ai.path = [(200.0, 100.0)]

    from yukkuri_game.game.ai.navigation_controller import (
        NavigationController,
    )

    # We are already at (200, 100). Calling navigate_to should succeed
    # because we've reached the end of the path (closest reachable point).
    status = NavigationController.navigate_to(
        world=driver.world,
        entity_id=yukkuri_id,
        target_pos=target_pos,
        target_entity_id=None,
        speed=100.0,
        acceptance_radius=35.0,
    )
    assert status == Status.SUCCESS


def test_wander_successive_targets(game_driver: GameDriver) -> None:
    """
    Verify that when an entity completes a Wander action (reaches the target),
    the Wander action is re-initialized on the next tick and picks a different
    random target location.
    """
    driver = game_driver
    driver.setup()

    yukkuri_id = driver.create_yukkuri("reimu", 100.0, 100.0)
    driver.world.commands.apply_all()

    # Trigger Wander action
    driver.set_ai_action(yukkuri_id, "Wander")
    driver.run_for(seconds=0.1)

    ai = driver.world.get_component(yukkuri_id, AIState)
    assert ai is not None
    assert ai.state_data is not None
    assert "target_x" in ai.state_data

    tx1 = ai.state_data["target_x"]
    ty1 = ai.state_data["target_y"]

    # Manually warp the Yukkuri to the target location to simulate arrival
    trans = driver.world.get_component(yukkuri_id, Transform)
    trans.x = tx1
    trans.y = ty1
    from yukkuri_game.engine.components import PhysicsBody
    phys = driver.world.try_get_component(yukkuri_id, PhysicsBody)
    if phys:
        phys.body.position = (tx1, ty1)

    # Run for a few frames to let the navigation and behavior systems tick
    # and complete the current Wander action.
    driver.run_for(seconds=0.5)

    # Wander should have completed and generated a new target
    assert "target_x" in ai.state_data
    tx2 = ai.state_data["target_x"]
    ty2 = ai.state_data["target_y"]

    assert (tx1, ty1) != (tx2, ty2), "Target coordinates did not change!"


def test_wander_close_range_obstacle_recovery(
    game_driver: GameDriver,
) -> None:
    """
    Verify that when the target is close-range (< 150px) but blocked by a
    physics obstacle, the entity does not bypass obstacle checks via the
    150px direct-steering short-circuit, and correctly uses path-based
    navigation to complete the action.
    """
    driver = game_driver
    driver.setup()

    # Yukkuri is at (100, 100). Obstacle is in between (e.g. at (150, 100))
    # Target is at (200, 100) (distance 100px < 150px).
    yukkuri_id = driver.create_yukkuri("reimu", 100.0, 100.0)
    driver.world.commands.apply_all()

    # Let's mock a segment query hit on the physics space to simulate a wall
    from yukkuri_game.engine.protocols import IPhysicsService
    from unittest.mock import MagicMock
    
    mock_physics = MagicMock(spec=IPhysicsService)
    mock_space = MagicMock(spec=pymunk.Space)
    mock_physics.space = mock_space
    
    # Register mock physics service
    driver.world.services.register(
        mock_physics, IPhysicsService, replace=True
    )

    # Make segment_query_first return a hit (meaning wall is present)
    mock_shape = MagicMock(spec=pymunk.Shape)
    mock_shape.body = MagicMock(spec=pymunk.Body)
    mock_shape.sensor = False
    mock_hit = MagicMock(spec=pymunk.SegmentQueryInfo)
    mock_hit.shape = mock_shape
    mock_space.segment_query_first.return_value = mock_hit

    ai = driver.world.get_component(yukkuri_id, AIState)
    assert ai is not None

    target_pos = pymunk.Vec2d(200.0, 100.0)
    ai.state_data = {"target_x": 200.0, "target_y": 100.0}
    ai.path = [(120.0, 100.0)]

    from yukkuri_game.game.ai.navigation_controller import (
        NavigationController,
    )

    # Teleport to the end of the path (120.0, 100.0)
    trans = driver.world.get_component(yukkuri_id, Transform)
    trans.x = 120.0
    trans.y = 100.0

    # Since we are at the end of the path (closest walkable point),
    # navigate_to should succeed!
    status = NavigationController.navigate_to(
        world=driver.world,
        entity_id=yukkuri_id,
        target_pos=target_pos,
        target_entity_id=None,
        speed=100.0,
        acceptance_radius=35.0,
    )
    assert status == Status.SUCCESS


def test_wander_stuck_limit_recovery(game_driver: GameDriver) -> None:
    """
    Verify that when an entity gets stuck 3 times, the navigation fails,
    which aborts the current Wander action, wiggles/cools down, and subsequently
    allows it to choose a new target coordinate on its next wandering tick.
    """
    driver = game_driver
    driver.setup()

    yukkuri_id = driver.create_yukkuri("reimu", 100.0, 100.0)
    driver.world.commands.apply_all()

    # Trigger Wander action
    driver.set_ai_action(yukkuri_id, "Wander")
    driver.run_for(seconds=0.1)

    ai = driver.world.get_component(yukkuri_id, AIState)
    assert ai is not None
    assert "target_x" in ai.state_data

    tx1 = ai.state_data["target_x"]
    ty1 = ai.state_data["target_y"]

    # Directly set stuck_count to 3 in state_data
    ai.state_data["stuck_count"] = 3

    # Run for a tick - the navigation should detect stuck_count >= 3,
    # return Status.FAILURE, clean up the navigation state, and trigger Wander failure.
    driver.run_for(seconds=0.1)

    # The old target should be popped/cleaned up
    assert "target_x" not in ai.state_data or ai.state_data.get("target_x") != tx1


def test_obstacle_item_removal_unblocks_navigation(
    game_driver: GameDriver,
) -> None:
    """
    Verify that dynamic obstacle items are cleanly un-registered from the
    navigation grid when their PhysicsBody is removed from the world.
    """
    driver = game_driver
    driver.setup()

    from yukkuri_game.game.ai.navigation_constants import TraversalCapability
    from yukkuri_game.game.ai.navigation_service import NavigationService

    nav_service = driver.world.services.get(NavigationService)
    assert nav_service is not None

    obstacle_pos = (200.0, 200.0)

    # Convert coordinates to grid coordinates to inspect walkability
    gx, gy = nav_service._to_grid(obstacle_pos)

    # Before creating the item, the grid cell must be walkable
    assert nav_service.grid.is_walkable(gx, gy, TraversalCapability.WALK)

    # Spawn an obstacle item (bed) at the coordinates
    item_id = driver.create_item("bed", obstacle_pos[0], obstacle_pos[1])
    driver.world.commands.apply_all()

    # The grid cell must now be BLOCKED (walkable=False)
    assert not nav_service.grid.is_walkable(gx, gy, TraversalCapability.WALK)

    # Now destroy the obstacle item
    driver.world.destroy_entity(item_id)
    driver.world.commands.apply_all()

    # The grid cell must become WALKABLE again!
    assert nav_service.grid.is_walkable(gx, gy, TraversalCapability.WALK)


