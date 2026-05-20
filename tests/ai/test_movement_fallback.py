"""
Test to ensure Yukkuri falls back to direct steering when pathfinding fails or ai.path is None.
"""

from yukkuri_game.engine.application import Application
from yukkuri_game.testing.driver import GameDriver
from yukkuri_game.game.components.physics import MoveCommand
from yukkuri_game.game.components import AIState
import pymunk

def test_movement_fallback_when_path_none():
    app = Application()
    driver = GameDriver(app)
    driver.setup()
    
    yukkuri = driver.create_yukkuri("reimu", x=0, y=0)
    ai = driver.get_component(yukkuri, AIState)
    
    # Force ai.path to None and set a target
    ai.path = None
    ai.state_data = {"target_x": 100.0, "target_y": 0.0, "path_requesting": False, "path_failed": True}
    ai.current_target_id = -1
    
    from yukkuri_game.game.ai.behaviors.actions.movement import MoveToTarget
    action = MoveToTarget(entity_id=yukkuri, world=driver.world)
    
    # Run once
    action.update()
    driver.world.commands.apply_all()
    
    # We should have a MoveCommand now because fallback direct steering adds one
    assert driver.get_component(yukkuri, MoveCommand) is not None, "Fallback should set MoveCommand when ai.path is None"
    move_cmd = driver.get_component(yukkuri, MoveCommand)
    assert move_cmd.target_pos.x == 100.0
    assert move_cmd.target_pos.y == 0.0
