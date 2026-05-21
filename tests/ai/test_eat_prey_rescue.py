"""
Test EatPrey rescue mechanic to demonstrate the bug where multiple prey standing together render themselves immune.
"""

from yukkuri_game.engine.application import Application
from yukkuri_game.testing.driver import GameDriver
from yukkuri_game.game.components import Predator, YukkuriStats, AIState, Needs
from yukkuri_game.game.ai.behaviors.actions.interaction import EatPrey
from yukkuri_game.engine.components import Transform
from yukkuri_game.engine.types import EntityID
from py_trees.common import Status

def test_eat_prey_rescue_bug():
    app = Application()
    driver = GameDriver(app)
    driver.setup()
    
    # Create predator
    predator_id = driver.create_yukkuri("reimu", x=0, y=0)
    driver.world.add_component(predator_id, Predator(prey_sense_radius=100.0, dps=10, prey_tags={"marisa"}))
    ai = driver.get_component(predator_id, AIState)
    
    # Create primary target
    prey1_id = driver.create_yukkuri("marisa", x=30, y=0)
    ai.current_target_id = EntityID(prey1_id)
    
    eat_action = EatPrey(entity_id=predator_id, world=driver.world)
    eat_action.initialise()
    
    # Run once - should be RUNNING or SUCCESS depending on logic
    status = eat_action.update()
    assert status == Status.RUNNING, f"Expected RUNNING, got {status}"
    
    # Now create a SECOND prey next to the first one
    prey2_id = driver.create_yukkuri("marisa", x=40, y=0)
    print(f"prey2_id={prey2_id}, has_stats={driver.world.has_component(prey2_id, YukkuriStats)}, has_trans={driver.world.has_component(prey2_id, Transform)}")
    
    # Run EatPrey again
    status = eat_action.update()
    
    # If the bug is fixed, the predator will not drop target and will continue eating (RUNNING)
    assert status == Status.RUNNING, f"Expected RUNNING after rescue check is removed, but got {status}"
