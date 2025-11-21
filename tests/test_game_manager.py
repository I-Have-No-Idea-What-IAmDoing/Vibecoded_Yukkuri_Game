import pytest
import os
import json
from unittest.mock import MagicMock, patch
from yukkuri_game.game.game_manager import GameManager
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.yukkuri_components import YukkuriStats, ItemStats
from yukkuri_game.game.components import Transform
from yukkuri_game.game.player_components import PlayerState
from yukkuri_game.game.entity_factory import EntityFactory

@pytest.fixture
def mock_world():
    world = MagicMock(spec=World)
    world._entities = []

    # Mock services
    world.services = MagicMock()

    # Mock get_components for PlayerState
    world.get_components.return_value = {}
    world.create_entity.return_value = 0

    return world

@pytest.fixture
def mock_factory():
    return MagicMock(spec=EntityFactory)

@pytest.fixture
def game_manager(mock_world, mock_factory, tmp_path):
    # Setup services to return mock_factory
    mock_world.services.get.return_value = mock_factory

    # Setup PlayerState
    player_state = PlayerState(save_dir=str(tmp_path))
    mock_world.get_components.return_value = {0: player_state}

    gm = GameManager(mock_world)

    # Since get_components returns a dict, but we want subsequent calls to work
    # The GameManager init might create a player if not found.
    # Here we mock it so it finds it.

    return gm

def test_initial_state(game_manager):
    assert game_manager.money == 1000
    assert game_manager.time_elapsed == 0.0
    assert os.path.exists(game_manager.save_dir)

def test_init_creates_player(mock_world, mock_factory):
    # Setup world to have no players initially
    mock_world.get_components.side_effect = [{}, {0: PlayerState()}] # First call empty, second call has it (if needed)
    mock_world.services.get.return_value = mock_factory

    gm = GameManager(mock_world)

    # Verify player entity creation
    mock_world.create_entity.assert_called()
    # Check if add_component was called with PlayerState
    # We iterate through call args to find PlayerState
    found_player_state = False
    for call in mock_world.add_component.call_args_list:
        if isinstance(call[0][1], PlayerState):
            found_player_state = True
            break
    assert found_player_state

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

    # Mock get_component
    def get_component_side_effect(e, c):
        if c == YukkuriStats:
            return stats
        return None
    mock_world.get_component.side_effect = get_component_side_effect

    # Ensure PlayerState is available
    player_state = PlayerState()
    mock_world.get_components.return_value = {0: player_state}

    initial_money = game_manager.money

    value = game_manager.sell_yukkuri(entity_id)

    assert value == 200
    assert game_manager.money == initial_money + 200
    mock_world.destroy_entity.assert_called_once_with(entity_id)

def test_sell_non_yukkuri(game_manager, mock_world):
    entity_id = 2
    mock_world.get_component.return_value = None

    # Ensure PlayerState is available
    player_state = PlayerState()
    mock_world.get_components.return_value = {0: player_state}

    initial_money = game_manager.money
    value = game_manager.sell_yukkuri(entity_id)

    assert value == 0
    assert game_manager.money == initial_money
    mock_world.destroy_entity.assert_not_called()

# The save/load tests need to be updated because now we delegate to PersistenceSystem.
# But since we are mocking everything, we can just verify GameManager calls PersistenceSystem
# OR we can integration test it by mocking PersistenceSystem behavior or file system.
# Since we are in unit tests, mocking file system is better, or just trusting PersistenceSystem tests (which we will write).
# But let's update them to work with current GameManager implementation.

# Note: GameManager instantiates PersistenceSystem locally.
# We can patch PersistenceSystem in GameManager module.

@patch('yukkuri_game.game.game_manager.PersistenceSystem')
def test_save_game(mock_persistence_cls, game_manager):
    mock_persistence_instance = mock_persistence_cls.return_value

    game_manager.save_game("test_save.json")

    mock_persistence_instance.save.assert_called_once_with("test_save.json")
    assert mock_persistence_instance.ecs_world == game_manager.world

@patch('yukkuri_game.game.game_manager.PersistenceSystem')
def test_load_game(mock_persistence_cls, game_manager):
    mock_persistence_instance = mock_persistence_cls.return_value
    mock_persistence_instance.load.return_value = True

    success = game_manager.load_game("test_save.json")

    assert success is True
    mock_persistence_instance.load.assert_called_once_with("test_save.json")
    assert mock_persistence_instance.ecs_world == game_manager.world

@patch('yukkuri_game.game.game_manager.PersistenceSystem')
def test_load_game_not_found(mock_persistence_cls, game_manager):
    mock_persistence_instance = mock_persistence_cls.return_value
    mock_persistence_instance.load.return_value = False

    success = game_manager.load_game("non_existent.json")

    assert success is False
