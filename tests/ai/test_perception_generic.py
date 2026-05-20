"""
Test to ensure the perception system respects generic "Yukkuri" tags in prey_tags.
"""

from yukkuri_game.engine.application import Application
from yukkuri_game.testing.driver import GameDriver
from yukkuri_game.game.components import Predator, YukkuriStats, AIState, Blackboard
from yukkuri_game.game.systems.perception_system import PerceptionSystem
from yukkuri_game.engine.components import Transform
from yukkuri_game.engine.types import EntityID

def test_perception_system_resolves_generic_yukkuri_tag():
    app = Application()
    driver = GameDriver(app)
    driver.setup()
    
    # Create predator
    predator_id = driver.create_yukkuri("reimu", x=0, y=0)
    
    # Force generic "Yukkuri" tag
    pred = driver.get_component(predator_id, Predator)
    if pred is None:
        driver.world.add_component(predator_id, Predator(prey_sense_radius=100.0, dps=10, prey_tags={"Yukkuri"}))
    else:
        pred.prey_tags = {"Yukkuri"}
    
    # Create prey (another yukkuri, "marisa" not explicitly in prey_tags)
    prey_id = driver.create_yukkuri("marisa", x=50, y=0)
    
    # Set AI state to see each other
    pred_ai = driver.get_component(predator_id, AIState)
    pred_ai.visible_entities = {EntityID(prey_id)}
    
    prey_ai = driver.get_component(prey_id, AIState)
    prey_ai.visible_entities = {EntityID(predator_id)}
    
    pred_bb = driver.get_component(predator_id, Blackboard)
    if not pred_bb:
        pred_bb = Blackboard()
        driver.world.add_component(predator_id, pred_bb)
        
    prey_bb = driver.get_component(prey_id, Blackboard)
    if not prey_bb:
        prey_bb = Blackboard()
        driver.world.add_component(prey_id, prey_bb)
        
    # Run perception system manually
    system = PerceptionSystem()
    system.ecs_world = driver.world
    system.initialize()
    system.update(driver.world, 0.1)
    
    # Check predator blackboard
    assert pred_bb is not None
    assert prey_id in pred_bb.visible_targets
    assert pred_bb.visible_targets[prey_id].relation == "Prey", "Predator should resolve generic Yukkuri as prey"
    
    # Check prey blackboard
    assert prey_bb is not None
    assert predator_id in prey_bb.visible_targets
    assert prey_bb.visible_targets[predator_id].relation == "Threat", "Prey should resolve generic predator as threat"
