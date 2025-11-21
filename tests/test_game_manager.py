import pytest
import os
import json
from unittest.mock import MagicMock, patch
from yukkuri_game.game.game_manager import GameManager
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.yukkuri_components import YukkuriStats, ItemStats
from yukkuri_game.game.components import Transform

@pytest.fixture
def mock_world():
    world = MagicMock(spec=World)
    world._entities = []
    return world

@pytest.fixture
def mock_factory():
    return MagicMock()

@pytest.fixture
def game_manager(mock_world, mock_factory, tmp_path):
    gm = GameManager(mock_world, mock_factory)
    gm.save_dir = str(tmp_path)
    return gm

def test_initial_state(game_manager):
    assert game_manager.money == 1000
    assert game_manager.time_elapsed == 0.0
    assert os.path.exists(game_manager.save_dir)

def test_init_creates_save_dir(mock_world, mock_factory, tmp_path):
    save_dir = tmp_path / "new_saves"
    assert not save_dir.exists()

    gm = GameManager(mock_world, mock_factory)
    gm.save_dir = str(save_dir)

    # We need to trigger the init logic again or manually simulate it
    # Since __init__ is already called, we can check if we can force it
    # But easier is to just subclass or just test the logic if it was extracted.
    # However, the logic is in __init__.
    # Let's just instantiate GameManager with a path that doesn't exist?
    # But GameManager hardcodes "saves" in __init__ before we can change it.
    # We can patch os.path.exists and os.makedirs.

    with patch("os.path.exists", return_value=False), \
         patch("os.makedirs") as mock_makedirs:
        GameManager(mock_world, mock_factory)
        mock_makedirs.assert_called_with("saves")

def test_calculate_quality_score(game_manager):
    stats = YukkuriStats(type_id="test", name="TestYukkuri")
    stats.happiness = 50
    stats.badges = 1
    stats.health = 100
    stats.max_health = 100
    stats.age = 600 # 10 minutes

    # Base: 100
    # Happiness: 50 * 2 = 100
    # Badges: 1 * 500 = 500
    # Health penalty: 0
    # Age bonus: (600 / 60) * 10 = 100
    # Total: 800

    score = game_manager.calculate_quality_score(stats)
    assert score == 800
    assert stats.quality_score == 800

    # Test health penalty
    stats.health = 50
    # Penalty: (100 - 50) * 2 = 100
    # Total: 700
    score = game_manager.calculate_quality_score(stats)
    assert score == 700

def test_sell_yukkuri(game_manager, mock_world):
    entity_id = 1
    stats = YukkuriStats(type_id="test", name="TestYukkuri")
    # Default happiness is 50.0
    # Base: 100, Happiness: 50*2 = 100, Total = 200
    mock_world.get_component.side_effect = lambda e, c: stats if c == YukkuriStats else None

    initial_money = game_manager.money

    value = game_manager.sell_yukkuri(entity_id)

    assert value == 200
    assert game_manager.money == initial_money + 200
    mock_world.destroy_entity.assert_called_once_with(entity_id)

def test_sell_non_yukkuri(game_manager, mock_world):
    entity_id = 2
    mock_world.get_component.return_value = None

    initial_money = game_manager.money
    value = game_manager.sell_yukkuri(entity_id)

    assert value == 0
    assert game_manager.money == initial_money
    mock_world.destroy_entity.assert_not_called()

def test_save_game(game_manager, mock_world):
    game_manager.money = 5000
    game_manager.time_elapsed = 120.0

    # Setup an entity
    entity_id = 1
    mock_world._entities = [entity_id]

    transform = Transform(x=10.0, y=20.0)
    stats = YukkuriStats(type_id="test", name="SaveTest")
    stats.health = 80.0

    def get_component_side_effect(e, c):
        if c == Transform:
            return transform
        if c == YukkuriStats:
            return stats
        return None

    mock_world.get_component.side_effect = get_component_side_effect

    game_manager.save_game("test_save.json")

    save_file = os.path.join(game_manager.save_dir, "test_save.json")
    assert os.path.exists(save_file)

    with open(save_file, "r") as f:
        data = json.load(f)

    assert data["money"] == 5000
    assert data["time"] == 120.0
    assert len(data["entities"]) == 1

    ent_data = data["entities"][0]
    assert ent_data["transform"]["x"] == 10.0
    assert ent_data["transform"]["y"] == 20.0
    assert ent_data["yukkuri"]["name"] == "SaveTest"
    assert ent_data["yukkuri"]["health"] == 80.0

def test_save_game_item(game_manager, mock_world):
    # Setup an item entity
    entity_id = 2
    mock_world._entities = [entity_id]

    transform = Transform(x=5.0, y=5.0)
    item_stats = ItemStats(type_id="food", name="Cookie", cost=10)

    def get_component_side_effect(e, c):
        if c == Transform:
            return transform
        if c == ItemStats:
            return item_stats
        return None

    mock_world.get_component.side_effect = get_component_side_effect

    game_manager.save_game("test_save_item.json")

    save_file = os.path.join(game_manager.save_dir, "test_save_item.json")

    with open(save_file, "r") as f:
        data = json.load(f)

    ent_data = data["entities"][0]
    assert ent_data["item"]["type_id"] == "food"

def test_load_game(game_manager, mock_world, mock_factory):
    save_data = {
        "money": 2000,
        "time": 300.0,
        "entities": [
            {
                "transform": {"x": 100.0, "y": 200.0},
                "yukkuri": {
                    "type_id": "reimu",
                    "name": "LoadedReimu",
                    "health": 90.0,
                    "hunger": 50.0,
                    "happiness": 80.0,
                    "badges": 1,
                    "age": 60.0
                }
            },
            {
                "transform": {"x": 50.0, "y": 50.0},
                "item": {
                    "type_id": "cookie"
                }
            }
        ]
    }

    save_file = os.path.join(game_manager.save_dir, "load_test.json")
    with open(save_file, "w") as f:
        json.dump(save_data, f)

    # Mock existing entities to be cleared
    mock_world._entities = [99, 100]

    # Mock factory creation
    mock_factory.create_yukkuri.return_value = 1
    mock_factory.create_item.return_value = 2

    # Mock get_component for stats update
    stats = YukkuriStats(type_id="reimu", name="Default")
    mock_world.get_component.return_value = stats

    success = game_manager.load_game("load_test.json")

    assert success is True
    assert game_manager.money == 2000
    assert game_manager.time_elapsed == 300.0

    # Check if existing entities were destroyed
    assert mock_world.destroy_entity.call_count == 2

    # Check if factory was called correctly
    mock_factory.create_yukkuri.assert_called_once_with("reimu", 100.0, 200.0)
    mock_factory.create_item.assert_called_once_with("cookie", 50.0, 50.0)

    # Check if stats were updated
    assert stats.name == "LoadedReimu"
    assert stats.health == 90.0

def test_load_game_not_found(game_manager):
    success = game_manager.load_game("non_existent.json")
    assert success is False
