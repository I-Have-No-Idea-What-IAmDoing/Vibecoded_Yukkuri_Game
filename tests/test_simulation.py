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

    # Initial stats
    stats = world.get_component(yukkuri, YukkuriStats)
    initial_hunger = stats.hunger
    initial_cleanliness = stats.cleanliness

    dt = 1.0
    ai_system.update(world, dt)

    # Hunger increases, Cleanliness decreases
    assert stats.hunger > initial_hunger
    assert stats.cleanliness < initial_cleanliness

def test_simulation_action_eat(simulation_world, ai_system):
    world, yukkuri, item = simulation_world

    # Force AI to choose Eat
    ai_system.ai_engine.select_action.return_value = "Eat"

    # Update to trigger decision (interval is 1.0)
    ai_system.update(world, 1.1)

    ai = world.get_component(yukkuri, AIState)
    assert ai.current_action == "Eat"

    # In new system, target is set by FindFood which runs inside the BT.
    # BT structure: Eat Seq -> Goal=Eat? -> Eat Exec -> (Target Exists? -> Move -> Interact) OR Find Food
    # 1st Tick: Goal=Eat (True). Target Exists? (False). Find Food (Success, sets target).
    # So after 1.1s update, target should be set.
    assert ai.current_target_id == item

    # Note: py_trees might require multiple ticks to traverse and execute sequences properly,
    # especially if nodes return RUNNING.

    # Tick 2: Move closer. Dist 100 -> 20 (Speed 100 * 0.8)
    ai_system.update(world, 0.8)

    # Tick 3: Move closer. Dist 20 -> 0 (Speed 100 * 0.3 = 30 > 20)
    # MoveToTarget should return SUCCESS.
    # Interact might run in same tick or next.
    ai_system.update(world, 0.3)

    # Tick 4-10: Allow interaction to complete.
    # Interact checks distance <= 30. Current dist should be 0.
    for _ in range(10):
        ai_system.update(world, 0.1)

    # Item should be consumed (destroyed)
    assert item not in world._entities

    # Stats should be updated
    stats = world.get_component(yukkuri, YukkuriStats)
    # Started at 50 + decay (from first update) - 20 (from eat)
    # Decay is 2.0 * 1.1 = 2.2. Hunger ~ 52.2
    # After eat: 52.2 - 20 = 32.2
    assert stats.hunger < 40 # Loose check

def test_simulation_action_wander(simulation_world, ai_system):
    world, yukkuri, _ = simulation_world

    ai_system.ai_engine.select_action.return_value = "Wander"

    # Trigger decision
    ai_system.update(world, 1.1)

    ai = world.get_component(yukkuri, AIState)
    assert ai.current_action == "Wander"
    assert ai.state_data is not None
    assert "target_x" in ai.state_data

    # Move
    trans = world.get_component(yukkuri, Transform)
    initial_x, initial_y = trans.x, trans.y

    ai_system.update(world, 0.1)

    # Should have moved (unless target was 0,0 which is unlikely with random)
    assert trans.x != initial_x or trans.y != initial_y

def test_find_nearest_item(simulation_world, ai_system):
    world, yukkuri, item1 = simulation_world

    # Add another item further away
    item2 = world.create_entity()
    world.add_component(item2, Transform(x=100, y=0))
    world.add_component(item2, ItemStats(name="Cookie2", type_id="cookie", cost=10, nutrition=20))

    items = [item1, item2]
    trans = world.get_component(yukkuri, Transform)

    nearest = ai_system.find_nearest_item(trans, items, world, "nutrition")
    assert nearest == item1

    # Test filter (item without nutrition)
    world.get_component(item1, ItemStats).nutrition = 0
    nearest = ai_system.find_nearest_item(trans, items, world, "nutrition")
    assert nearest == item2
