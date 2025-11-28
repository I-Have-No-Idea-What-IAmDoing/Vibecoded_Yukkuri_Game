import pytest
from unittest.mock import MagicMock
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.components import Transform, MovementController
from yukkuri_game.game.yukkuri_components import YukkuriStats, AIState, ItemStats
from yukkuri_game.game.systems.behavior import BehaviorSystem
from yukkuri_game.game.systems.stat_decay import StatDecaySystem
from yukkuri_game.game.systems.interaction_system import InteractionSystem
from yukkuri_game.config import StatDecaySettings
from yukkuri_game.game.services import GameService
from yukkuri_game.game.ai.utility import UtilityAIEngine
from yukkuri_game.game.ai.navigation_service import NavigationService

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
    world.add_component(yukkuri, MovementController())
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

    behavior_system = BehaviorSystem(world_width=1000, world_height=1000)
    stat_decay_system = StatDecaySystem(StatDecaySettings(hunger=2.0, cleanliness=2.0)) # Set specific decay rates
    interaction_system = InteractionSystem()

    return behavior_system, stat_decay_system, mock_ai_engine, interaction_system

def test_simulation_update_decay(simulation_world, systems):
    world, yukkuri, _ = simulation_world
    _, stat_decay_system, _, _ = systems

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
    behavior_system, _, mock_ai_engine, interaction_system = systems

    # Force AI to choose Eat
    mock_ai_engine.select_action.return_value = "Eat"
    # Register mock engine so UtilitySelector finds it
    world.services.register(mock_ai_engine, UtilityAIEngine)

    # BehaviorSystem drives UtilitySelector which sets current_action
    ai = world.get_component(yukkuri, AIState)

    # 1st Tick: UtilitySelector sets Eat -> Eat Seq -> Goal=Eat? (Yes) -> Eat Exec -> Have Target? (No) -> Find Food (Success, sets target)
    behavior_system.update(world, 0.1)

    assert ai.current_action == "Eat"
    # 1st Tick: Eat Seq -> Goal=Eat? (Yes) -> Eat Exec -> Have Target? (No) -> Find Food (Success, sets target)
    behavior_system.update(world, 0.1)

    assert ai.current_target_id == item

    # 2nd Tick: Eat Exec -> Have Target? (Yes) -> MoveToTarget
    # Move closer. Dist 100 -> 90 (Speed 100 * 0.1)
    trans = world.get_component(yukkuri, Transform)
    initial_x = trans.x
    behavior_system.update(world, 0.1)
    # BehaviorSystem updates MoveToTarget, which sets target_velocity in MovementController.
    # We need to manually simulate movement application since we don't have PhysicsSystem/MovementSystem in this test.
    controller = world.get_component(yukkuri, MovementController)

    # Apply velocity
    trans.x += controller.target_velocity.x * 0.1
    trans.y += controller.target_velocity.y * 0.1

    # Check if we moved.
    assert trans.x > initial_x # Should have moved towards 100

    # Move until close enough (Dist <= 30 for Interact, < 15 for MoveToTarget success)
    for _ in range(20):
        behavior_system.update(world, 0.1)
        # Manually apply velocity
        trans.x += controller.target_velocity.x * 0.1
        trans.y += controller.target_velocity.y * 0.1

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
    behavior_system, _, mock_ai_engine, _ = systems

    mock_ai_engine.select_action.return_value = "Wander"
    # Register mock engine so UtilitySelector finds it
    world.services.register(mock_ai_engine, UtilityAIEngine)

    # BehaviorSystem
    # 1st Tick: UtilitySelector sets Wander -> Wander Seq -> Goal=Wander? (Yes) -> Wander Action
    # Wander Action initialise -> Pick random target -> Create MoveToTarget
    behavior_system.update(world, 0.1)

    ai = world.get_component(yukkuri, AIState)
    assert ai.current_action == "Wander"
    assert ai.state_data is not None
    assert "target_x" in ai.state_data

    # 2nd Tick: Move
    trans = world.get_component(yukkuri, Transform)
    initial_x, initial_y = trans.x, trans.y

    behavior_system.update(world, 0.1)

    # Manually apply velocity
    controller = world.get_component(yukkuri, MovementController)
    trans.x += controller.target_velocity.x * 0.1
    trans.y += controller.target_velocity.y * 0.1

    # Should have moved
    assert trans.x != initial_x or trans.y != initial_y
