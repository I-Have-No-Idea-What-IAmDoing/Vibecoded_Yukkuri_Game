import pytest
import os
import json
from unittest.mock import MagicMock, patch
from yukkuri_game.game.game_manager import GameManager
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.yukkuri_components import YukkuriStats, ItemStats
from yukkuri_game.game.components import Transform
from yukkuri_game.game.services import EconomyService, PersistenceService, TimeService
from yukkuri_game.game.entity_factory import EntityFactory

@pytest.fixture
def mock_world():
    world = MagicMock(spec=World)
    world._entities = []

    # Mock services
    world.services = MagicMock()

    # Economy Service Mock
    economy_service = MagicMock(spec=EconomyService)
    economy_service.get_money.return_value = 1000

    return world

@pytest.fixture
def game_manager(mock_world):
    # We need to set up try_get/get for the constructor
    mock_world.services.get.side_effect = lambda service_type: \
        MagicMock(spec=EntityFactory) if service_type == EntityFactory else \
        MagicMock(spec=EconomyService) if service_type == EconomyService else None

    gm = GameManager(mock_world)
    return gm

def test_initial_state(game_manager, mock_world):
    # Money comes from EconomyService
    # We need to configure the mock to return 1000 when asked
    mock_economy = MagicMock(spec=EconomyService)
    mock_economy.get_money.return_value = 1000

    mock_time = MagicMock(spec=TimeService)
    mock_time.time_elapsed = 0.0

    def service_get_mock(t):
        if t == EconomyService: return mock_economy
        return MagicMock()

    def service_try_get_mock(t):
        if t == TimeService: return mock_time
        return MagicMock()

    mock_world.services.get.side_effect = service_get_mock
    mock_world.services.try_get.side_effect = service_try_get_mock

    assert game_manager.money == 1000
    assert game_manager.time_elapsed == 0.0

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
    mock_world.get_component.side_effect = lambda e, c: stats if c == YukkuriStats else None

    mock_economy = MagicMock(spec=EconomyService)
    mock_economy.get_money.return_value = 1000

    # Update mock_world.services.get to return our mock economy
    mock_world.services.get.side_effect = lambda t: mock_economy if t == EconomyService else MagicMock()

    value = game_manager.sell_yukkuri(entity_id)

    assert value == 200
    mock_economy.add_money.assert_called_once_with(200)
    mock_world.destroy_entity.assert_called_once_with(entity_id)

def test_sell_non_yukkuri(game_manager, mock_world):
    entity_id = 2
    mock_world.get_component.return_value = None

    mock_economy = MagicMock(spec=EconomyService)
    mock_world.services.get.side_effect = lambda t: mock_economy if t == EconomyService else MagicMock()

    value = game_manager.sell_yukkuri(entity_id)

    assert value == 0
    mock_economy.add_money.assert_not_called()
    mock_world.destroy_entity.assert_not_called()

def test_save_game_delegation(game_manager, mock_world):
    persistence = MagicMock(spec=PersistenceService)

    # Update try_get to return our persistence mock
    mock_world.services.try_get.side_effect = lambda t: persistence if t == PersistenceService else None

    game_manager.save_game("test.json")

    persistence.save_game.assert_called_once_with("test.json")

def test_load_game_delegation(game_manager, mock_world):
    persistence = MagicMock(spec=PersistenceService)
    persistence.load_game.return_value = True

    mock_world.services.try_get.side_effect = lambda t: persistence if t == PersistenceService else None

    result = game_manager.load_game("test.json")

    assert result is True
    persistence.load_game.assert_called_once_with("test.json")
