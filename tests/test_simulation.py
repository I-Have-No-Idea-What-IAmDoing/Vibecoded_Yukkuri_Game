import pytest
from unittest.mock import MagicMock
from src.yukkuri_game.engine.ecs import World
from src.yukkuri_game.game.components import Transform
from src.yukkuri_game.game.yukkuri_components import YukkuriStats, AIState, ItemStats
from src.yukkuri_game.game.systems.simulation import YukkuriAISystem
from src.yukkuri_game.game.ai.utility import Action

@pytest.fixture
def simulation_world():
    world = World()

    # Create Yukkuri
    yukkuri = world.create_entity()
    world.add_component(yukkuri, Transform(x=0, y=0))
    world.add_component(yukkuri, YukkuriStats(name="Test", type_id="test", hunger=50))
    world.add_component(yukkuri, AIState())

    # Create Item
    item = world.create_entity()
    world.add_component(item, Transform(x=100, y=0)) # Move item further away to prevent instant consumption
    world.add_component(item, ItemStats(name="Cookie", type_id="cookie", cost=10, nutrition=20))

    return world, yukkuri, item

@pytest.fixture
def ai_system():
    mock_ai_engine = MagicMock()
    # Default behavior: return "Idle"
    mock_ai_engine.select_action.return_value = "Idle"
    mock_ai_engine.actions = {
        "Idle": Action("Idle", [], 1.0, {"type": "idle"}),
        "Eat": Action("Eat", [], 1.0, {
            "type": "interact_item",
            "target_stat": "nutrition",
            "consume": True,
            "stat_changes": {"hunger": -20}
        }),
        "Wander": Action("Wander", [], 1.0, {"type": "move_random"})
    }

    return YukkuriAISystem(mock_ai_engine, 1000, 1000)

def test_simulation_update_decay(simulation_world, ai_system):
    world, yukkuri, _ = simulation_world
    # Need to set world manually for processor if not added via add_processor
    ai_system.world = world

    # Initial stats
    stats = world.component_for_entity(yukkuri, YukkuriStats)
    initial_hunger = stats.hunger
    initial_cleanliness = stats.cleanliness

    dt = 1.0
    ai_system.process(dt)

    # Hunger increases, Cleanliness decreases
    assert stats.hunger > initial_hunger
    assert stats.cleanliness < initial_cleanliness

def test_simulation_action_eat(simulation_world, ai_system):
    world, yukkuri, item = simulation_world
    ai_system.world = world

    # Force AI to choose Eat
    ai_system.ai_engine.select_action.return_value = "Eat"

    # Update to trigger decision (interval is 1.0)
    ai_system.process(1.1)

    ai = world.component_for_entity(yukkuri, AIState)
    assert ai.current_action == "Eat"
    assert ai.current_target_id == item

    # Update again to move/interact
    # Distance is 100. Speed is 100 * dt.
    # Need enough time to reach. 1.0s is enough (moves 100).
    # But we also need 1 more frame to interact (as logic is move -> check dist).
    # If dist < 20, interact.

    # Move closer
    ai_system.process(0.8) # Move 80 units. Pos ~ 80. Dist 20.

    # Interact range is < 20.
    # If exactly 20, might not interact.

    ai_system.process(0.3) # Move more. Should be close enough.

    # Need one more update to trigger interaction logic because interaction check happens before movement
    # Note: Movement logic consumes remaining speed if waypoint reached, so it might take more frames/time.
    ai_system.process(0.5)

    # One final update to trigger the interaction now that we are close enough
    ai_system.process(0.1)

    # Item should be consumed (destroyed)
    assert not world.entity_exists(item)

    # Stats should be updated
    stats = world.component_for_entity(yukkuri, YukkuriStats)
    # Started at 50 + decay (from first update) - 20 (from eat)
    # Decay is 2.0 * 1.1 = 2.2. Hunger ~ 52.2
    # After eat: 52.2 - 20 = 32.2
    assert stats.hunger < 40 # Loose check

def test_simulation_action_wander(simulation_world, ai_system):
    world, yukkuri, _ = simulation_world
    ai_system.world = world

    ai_system.ai_engine.select_action.return_value = "Wander"

    # Trigger decision
    ai_system.process(1.1)

    ai = world.component_for_entity(yukkuri, AIState)
    assert ai.current_action == "Wander"
    assert ai.state_data is not None
    assert "target_x" in ai.state_data

    # Move
    trans = world.component_for_entity(yukkuri, Transform)
    initial_x, initial_y = trans.x, trans.y

    ai_system.process(0.1)

    # Should have moved (unless target was 0,0 which is unlikely with random)
    assert trans.x != initial_x or trans.y != initial_y

def test_find_nearest_item(simulation_world, ai_system):
    world, yukkuri, item1 = simulation_world
    ai_system.world = world

    # Add another item further away
    item2 = world.create_entity()
    world.add_component(item2, Transform(x=100, y=0))
    world.add_component(item2, ItemStats(name="Cookie2", type_id="cookie", cost=10, nutrition=20))

    items = [item1, item2]
    trans = world.component_for_entity(yukkuri, Transform)

    # find_nearest_item signature changed to (trans, items, stat_check)
    nearest = ai_system.find_nearest_item(trans, items, "nutrition")
    assert nearest == item1

    # Test filter (item without nutrition)
    world.component_for_entity(item1, ItemStats).nutrition = 0
    nearest = ai_system.find_nearest_item(trans, items, "nutrition")
    assert nearest == item2
