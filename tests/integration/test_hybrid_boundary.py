"""Integration tests for the Blackboard and Command hybrid boundary.

Verifies that the CommandQueue and MotorDispatcher function perfectly under
the headless simulation environment and do not break existing ECS movements.
"""

from yukkuri_game.testing.driver import GameDriver
from yukkuri_game.game.ai.commands import CommandQueue, CommandType, Command
from yukkuri_game.game.components import AIState, MoveCommand, Needs
from yukkuri_game.engine.components import MovementController, Transform


def test_hybrid_boundary_command_queue_flow(game_driver: GameDriver) -> None:
    """Verify CommandQueue registration, command generation, and dispatch.

    Asserts that:
    1. CommandQueue is registered in the service locator.
    2. BehaviorTree's MoveToTarget publishes MOVE_TO commands.
    3. MotorDispatcher processes MOVE_TO commands into MoveCommand components.
    4. FLEE commands correctly assign direct velocities.

    Args:
        game_driver: The custom headless GameDriver fixture.
    """
    driver = game_driver
    driver.setup()

    # 1. Verify CommandQueue service is registered
    command_queue = driver.world.services.try_get(CommandQueue)
    assert command_queue is not None, "CommandQueue service must be registered"

    # Create a yukkuri and a cookie target
    start_pos = (100, 100)
    target_pos = (300, 100)
    yukkuri_id = driver.create_yukkuri("reimu", *start_pos)
    item_id = driver.create_item("cookie", *target_pos)

    # Clean any current MoveCommand to ensure a clean slate
    if driver.world.has_component(yukkuri_id, MoveCommand):
        driver.world.commands.remove_component(yukkuri_id, MoveCommand)
        driver.world.commands.apply_all()

    # Set AI to Eat the item manually to trigger movement behaviors
    driver.set_ai_action(yukkuri_id, "Eat", target_id=item_id)

    # Print state before running
    ai = driver.world.get_component(yukkuri_id, AIState)
    trans = driver.world.get_component(yukkuri_id, Transform)
    needs = driver.world.get_component(yukkuri_id, Needs)
    print(f"DEBUG: Before run: action={ai.current_action}, target={ai.current_target_id}, override={ai.manual_override}")
    print(f"DEBUG: yukkuri components: transform={trans is not None}, needs={needs is not None}")

    # Check if registered in BehaviorSystem
    from yukkuri_game.game.systems.behavior import BehaviorSystem
    behavior_sys = driver.world.get_system(BehaviorSystem)
    print(f"DEBUG: BT registered for yukkuri? {yukkuri_id in behavior_sys.trees}")

    # 2. Run for a single frame tick (simulate AI update)
    driver.run_for(seconds=0.02)

    # Print state after running
    print(f"DEBUG: After 0.1s run: commands count in queue={len(command_queue._commands)}")
    for c in command_queue._commands:
        print(f"  Command: type={c.type}, entity={c.entity_id}, payload={c.payload}")
    path_str = behavior_sys.get_active_node_path(yukkuri_id).replace(" \u2192 ", " -> ")
    print(f"DEBUG: BT path for yukkuri: {path_str}")

    # Verify that a MoveCommand component was successfully added back to the entity
    # as a result of the MOVE_TO action command!
    has_move_cmd = driver.world.has_component(yukkuri_id, MoveCommand)
    print(f"DEBUG: has_move_cmd={has_move_cmd}")
    assert has_move_cmd is True, "MotorDispatcher should have spawned MoveCommand"

    move_cmd = driver.world.get_component(yukkuri_id, MoveCommand)
    assert move_cmd.target_pos.x == target_pos[0]
    assert move_cmd.target_pos.y == target_pos[1]
    assert move_cmd.target_entity_id == item_id

    # 3. Test direct flee command dispatch
    # Clear move command again
    driver.world.commands.remove_component(yukkuri_id, MoveCommand)
    driver.world.commands.apply_all()

    # Push a manual FLEE command to the queue
    cmd = Command(
        CommandType.FLEE,
        yukkuri_id,
        {"velocity_x": 120.0, "velocity_y": 0.0},
    )
    command_queue.push(cmd)

    # Run for a frame tick
    driver.run_for(seconds=0.02)

    # Flee command should have set target velocity directly and removed MoveCommand
    controller = driver.world.get_component(yukkuri_id, MovementController)
    assert controller.target_velocity.x == 120.0
    assert controller.target_velocity.y == 0.0
    assert not driver.world.has_component(yukkuri_id, MoveCommand)
