"""
Tests for Game Simulation (Systems integration).
"""

import pytest
from unittest.mock import MagicMock
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.components import Transform, MovementController
from yukkuri_game.game.yukkuri_components import YukkuriStats, Needs, AIState, ItemStats
from yukkuri_game.game.systems.behavior import BehaviorSystem
from yukkuri_game.game.systems.emotion_system import EmotionSystem
from yukkuri_game.game.systems.interaction_system import InteractionSystem
from yukkuri_game.config import StatDecaySettings
from yukkuri_game.game.services import GameService
from yukkuri_game.game.ai.utility import UtilityAIEngine
from yukkuri_game.game.ai.navigation_service import NavigationService


@pytest.fixture
def simulation_world() -> tuple[World, int, int]:
    """
    Sets up a world with a Yukkuri and an Item for simulation tests.
    """
    world = World()
    world.services.register(GameService(world))
    world.services.register(NavigationService(1000, 1000))

    # Create Yukkuri
    yukkuri = world.create_entity()
    world.add_component(yukkuri, Transform(x=0, y=0))
    world.add_component(yukkuri, YukkuriStats(name="Test", type_id="test"))
    world.add_component(yukkuri, Needs(hunger=50))
    world.add_component(yukkuri, AIState())
    world.add_component(yukkuri, MovementController())
    # We don't add PhysicsBody so MoveToTarget modifies Transform directly

    # Create Item
    item = world.create_entity()
    world.add_component(item, Transform(x=100, y=0))  # Move item further away
    world.add_component(
        item, ItemStats(name="Cookie", type_id="cookie", cost=10, nutrition=20)
    )

    return world, yukkuri, item


@pytest.fixture
def systems() -> tuple[BehaviorSystem, EmotionSystem, MagicMock, InteractionSystem]:
    """
    Sets up the systems used in the simulation tests.
    """
    mock_ai_engine = MagicMock()
    # Default behavior: return "Idle"
    mock_ai_engine.select_action.return_value = "Idle"

    behavior_system = BehaviorSystem(world_width=1000, world_height=1000)
    stat_decay_system = EmotionSystem(
        StatDecaySettings(hunger=2.0, cleanliness=2.0)
    )  # Set specific decay rates
    interaction_system = InteractionSystem()

    return behavior_system, stat_decay_system, mock_ai_engine, interaction_system


def test_simulation_update_decay(
    simulation_world: tuple[World, int, int],
    systems: tuple[BehaviorSystem, EmotionSystem, MagicMock, InteractionSystem],
) -> None:
    """
    Tests that stats decay over time via the EmotionSystem.
    """
    world, yukkuri, _ = simulation_world
    _, stat_decay_system, _, _ = systems

    # Initial stats
    needs = world.get_component(yukkuri, Needs)
    initial_hunger = needs.hunger
    initial_cleanliness = needs.cleanliness

    dt = 1.0
    stat_decay_system.update(world, dt)

    # Hunger increases, Cleanliness decreases
    assert needs.hunger > initial_hunger
    assert needs.cleanliness < initial_cleanliness

    # Check specific values based on settings (2.0 per sec)
    assert needs.hunger == initial_hunger + 2.0
    assert needs.cleanliness == initial_cleanliness - 2.0


def test_simulation_action_eat(
    simulation_world: tuple[World, int, int],
    systems: tuple[BehaviorSystem, EmotionSystem, MagicMock, InteractionSystem],
) -> None:
    """
    Tests the full 'Eat' action cycle: Utility Selection -> Moving -> Interaction.
    """
    world, yukkuri, item = simulation_world
    behavior_system, _, mock_ai_engine, interaction_system = systems

    # Force AI to choose Eat
    mock_ai_engine.select_action.return_value = "Eat"
    # Register mock engine so UtilitySelector finds it
    world.services.register(mock_ai_engine, UtilityAIEngine)

    # BehaviorSystem drives UtilitySelector which sets current_action
    ai = world.get_component(yukkuri, AIState)

    # BehaviorSystem has throttling (10Hz). Need to tick enough to ensure update happens.
    # Initial stagger is entity_id dependent. With entity_id=1, stagger=0.01.
    # We tick 0.2s to be safe.

    # 1st Tick: UtilitySelector sets Eat -> Eat Seq -> Goal=Eat? (Yes) -> Eat Exec -> Have Target? (No) -> Find Food (Success, sets target)
    behavior_system.update(world, 0.2)
    # Check if updated (depends on staggering, but 0.2 should cover it)

    # If still Idle, it means throttling prevented update or stagger logic.
    # We can peek at behavior_system.next_update_times if needed, but 0.2 should be enough if total_time started at 0.

    if ai.current_action == "Idle":
         # Try another update
         behavior_system.update(world, 0.2)

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
    assert trans.x > initial_x  # Should have moved towards 100

    # Move until close enough (Dist <= 30 for Interact, < 15 for MoveToTarget success)
    for _ in range(30): # Increased range to be safe
        behavior_system.update(world, 0.1)
        # Manually apply velocity
        trans.x += controller.target_velocity.x * 0.1
        trans.y += controller.target_velocity.y * 0.1

    # Next tick should Interact
    needs = world.get_component(yukkuri, Needs)

    behavior_system.update(world, 0.1)

    # Behavior adds InteractionRequest. Now run InteractionSystem.
    # Updated: Need HungerSystem for food
    from yukkuri_game.game.systems.hunger_system import HungerSystem

    hunger_system = HungerSystem()
    # Register HungerSystem as service because InteractionSystem expects it there
    world.services.register(hunger_system, HungerSystem)

    # InteractionSystem needs to find HungerSystem via services
    # (Previously I was calling hunger_system.update which is wrong pattern for system dependency)
    # The previous test failed because HungerSystem wasn't available to InteractionSystem.
    # In my fix I just instantiated it locally but InteractionSystem uses world.services.try_get(HungerSystem)

    # InteractionSystem runs cleanup/other interactions
    interaction_system.update(world, 0.1)

    # Check if item consumed
    assert not world.entity_exists(item)

    # Check stats updated
    # Initial 50. Nutrition 20. Should be 30.
    # Note: EmotionSystem is not running here so no decay added.
    assert needs.hunger == 30.0


def test_simulation_action_wander(
    simulation_world: tuple[World, int, int],
    systems: tuple[BehaviorSystem, EmotionSystem, MagicMock, InteractionSystem],
) -> None:
    """
    Tests the 'Wander' action.
    """
    world, yukkuri, _ = simulation_world
    behavior_system, _, mock_ai_engine, _ = systems

    mock_ai_engine.select_action.return_value = "Wander"
    # Register mock engine so UtilitySelector finds it
    world.services.register(mock_ai_engine, UtilityAIEngine)

    # BehaviorSystem
    # 1st Tick: UtilitySelector sets Wander -> Wander Seq -> Goal=Wander? (Yes) -> Wander Action
    # Wander Action initialise -> Pick random target -> Create MoveToTarget

    # Tick enough for throttling
    behavior_system.update(world, 0.2)

    ai = world.get_component(yukkuri, AIState)

    if ai.current_action == "Idle":
         behavior_system.update(world, 0.2)

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
