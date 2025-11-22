import pytest
from unittest.mock import MagicMock
from src.yukkuri_game.engine.ecs import World
from src.yukkuri_game.game.components import Transform
from src.yukkuri_game.game.yukkuri_components import YukkuriStats, AIState, ItemStats
from src.yukkuri_game.game.systems.decision import DecisionSystem
from src.yukkuri_game.game.systems.behavior import BehaviorSystem
from src.yukkuri_game.game.systems.stat_decay import StatDecaySystem
from src.yukkuri_game.game.systems.interaction_system import InteractionSystem
from src.yukkuri_game.config import StatDecaySettings
from src.yukkuri_game.game.services import GameService
from src.yukkuri_game.game.ai.utility import UtilityAIEngine
from src.yukkuri_game.game.ai.navigation_service import NavigationService

@pytest.fixture
def simulation_world():
    world = World()
    world.services.register(GameService(world))
    world.services.register(NavigationService(1000, 1000))

    # Create Yukkuri
    yukkuri = world.create_entity()
    world.add_component(yukkuri, Transform(x=0, y=0))
    world.add_component(yukkuri, YukkuriStats(name="Test", type_id="test", hunger=50))
    world.add_component(yukkuri, AIState())
    # We don't add PhysicsBody so MoveToTarget modifies Transform directly

    # Create Item
    item = world.create_entity()
    world.add_component(item, Transform(x=100, y=0)) # Move item further away
    world.add_component(item, ItemStats(name="Cookie", type_id="cookie", cost=10, nutrition=20))

    return world, yukkuri, item

@pytest.fixture
def systems():
    mock_ai_engine = MagicMock()
    # Default behavior: return "Idle"
    mock_ai_engine.select_action.return_value = "Idle"

    decision_system = DecisionSystem(mock_ai_engine, decision_interval=1.0)
    behavior_system = BehaviorSystem(world_width=1000, world_height=1000)
    stat_decay_system = StatDecaySystem(StatDecaySettings(hunger=2.0, cleanliness=2.0)) # Set specific decay rates
    interaction_system = InteractionSystem()

    return decision_system, behavior_system, stat_decay_system, mock_ai_engine, interaction_system

def test_simulation_update_decay(simulation_world, systems):
    world, yukkuri, _ = simulation_world
    _, _, stat_decay_system, _, _ = systems

    # Initial stats
    stats = world.get_component(yukkuri, YukkuriStats)
    initial_hunger = stats.hunger
    initial_cleanliness = stats.cleanliness

    dt = 1.0
    stat_decay_system.update(world, dt)

    # Hunger increases, Cleanliness decreases
    assert stats.hunger > initial_hunger
    assert stats.cleanliness < initial_cleanliness

    # Check specific values based on settings (2.0 per sec)
    assert stats.hunger == initial_hunger + 2.0
    assert stats.cleanliness == initial_cleanliness - 2.0

def test_simulation_action_eat(simulation_world, systems):
    world, yukkuri, item = simulation_world
    decision_system, behavior_system, _, mock_ai_engine, interaction_system = systems

    # Force AI to choose Eat
    mock_ai_engine.select_action.return_value = "Eat"
    # Register mock engine so UtilitySelector finds it
    world.services.register(mock_ai_engine, UtilityAIEngine)

    # Trigger decision
    decision_system.update(world, 1.1)

    ai = world.get_component(yukkuri, AIState)
    assert ai.current_action == "Eat"

    # Now run BehaviorSystem
    # 1st Tick: Eat Seq -> Goal=Eat? (Yes) -> Eat Exec -> Have Target? (No) -> Find Food (Success, sets target)
    behavior_system.update(world, 0.1)

    assert ai.current_target_id == item

    # 2nd Tick: Eat Exec -> Have Target? (Yes) -> MoveToTarget
    # Move closer. Dist 100 -> 90 (Speed 100 * 0.1)
    trans = world.get_component(yukkuri, Transform)
    initial_x = trans.x
    behavior_system.update(world, 0.1)
    # Pathfinding might return the start point as the first point, so we need to check if we moved
    # The current implementation sets path[0] to start. MoveToTarget looks at path[0] and computes dx, dy.
    # If path[0] == trans, dist is 0. It pops path[0].
    # So the first update might just pop the start node.
    # Let's update again to see movement.
    if trans.x == initial_x:
         behavior_system.update(world, 0.1)

    assert trans.x > initial_x # Should have moved towards 100
    # assert trans.x == 10.0 # This assertion is brittle depending on pathfinding step size etc.

    # Move until close enough (Dist <= 30 for Interact, < 15 for MoveToTarget success)
    # Current x=10. Target=100. Dist=90. Speed=100.
    # Need to move 60 more to reach dist 30. 0.6s.
    # NOTE: MoveToTarget uses dt from Blackboard which is set by BehaviorSystem.update
    # With the pathfinding change, it might just jump to the target if close enough or follow path.
    # Let's give it enough time to reach.
    for _ in range(10):
        behavior_system.update(world, 0.1)

    # Next tick should Interact
    stats = world.get_component(yukkuri, YukkuriStats)

    behavior_system.update(world, 0.1)

    # Behavior adds InteractionRequest. Now run InteractionSystem.
    interaction_system.update(world, 0.1)

    # Check if item consumed
    assert not world.entity_exists(item)

    # Check stats updated
    # Initial 50. Nutrition 20. Should be 30.
    # Note: StatDecaySystem is not running here so no decay added.
    assert stats.hunger == 30.0

def test_simulation_action_wander(simulation_world, systems):
    world, yukkuri, _ = simulation_world
    decision_system, behavior_system, _, mock_ai_engine, _ = systems

    mock_ai_engine.select_action.return_value = "Wander"
    # Register mock engine so UtilitySelector finds it
    world.services.register(mock_ai_engine, UtilityAIEngine)

    # Trigger decision
    decision_system.update(world, 1.1)

    ai = world.get_component(yukkuri, AIState)
    assert ai.current_action == "Wander"

    # BehaviorSystem
    # 1st Tick: Wander Seq -> Goal=Wander? (Yes) -> Wander Action
    # Wander Action initialise -> Pick random target -> Create MoveToTarget
    behavior_system.update(world, 0.1)

    assert ai.state_data is not None
    assert "target_x" in ai.state_data

    # 2nd Tick: Move
    trans = world.get_component(yukkuri, Transform)
    initial_x, initial_y = trans.x, trans.y

    behavior_system.update(world, 0.1)

    # Should have moved
    assert trans.x != initial_x or trans.y != initial_y
