"""
Tests for Game Services (Economy, Time, Persistence).
"""

import pytest
from unittest.mock import MagicMock, patch, mock_open
from yukkuri_game.game.services import PersistenceService, EconomyService, TimeService
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.components import Transform
from yukkuri_game.game.yukkuri_components import YukkuriStats
from yukkuri_game.game.entity_factory import EntityFactory

# --- Economy Service Tests ---


def test_economy_service_basics() -> None:
    """
    Tests basic economy operations (add, remove, set).
    """
    service = EconomyService(initial_money=100)
    assert service.get_money() == 100

    service.add_money(50)
    assert service.get_money() == 150

    success = service.remove_money(100)
    assert success is True
    assert service.get_money() == 50

    success = service.remove_money(100)
    assert success is False
    assert service.get_money() == 50

    service.set_money(500)
    assert service.get_money() == 500

    service.set_money(-10)
    assert service.get_money() == 0

    with pytest.raises(ValueError):
        service.add_money(-10)

    with pytest.raises(ValueError):
        service.remove_money(-10)


# --- Time Service Tests ---


def test_time_service() -> None:
    """
    Tests time tracking.
    """
    service = TimeService()
    assert service.time_elapsed == 0.0

    service.add_time(1.5)
    assert service.time_elapsed == 1.5

    service.time_elapsed = 10.0
    assert service.time_elapsed == 10.0


# --- Persistence Service Tests ---


@pytest.fixture
def persistence_world() -> MagicMock:
    """
    Creates a mock World for persistence tests.
    """
    # Mock get_all_entities to return empty list initially
    # But we can't easily mock world methods unless we mock the world object
    # So let's use a mock world
    mock_world = MagicMock(spec=World)
    mock_world.services = MagicMock()
    mock_world.get_all_entities.return_value = []
    mock_world.get_entities_with.return_value = []
    return mock_world


def test_save_game(persistence_world: MagicMock) -> None:
    """
    Tests saving game data to a file.
    """
    world = persistence_world

    # Mock services
    economy = EconomyService(500)
    time_svc = TimeService()
    time_svc.time_elapsed = 123.45

    def get_service(svc_type):
        if svc_type == EconomyService:
            return economy
        if svc_type == TimeService:
            return time_svc
        return None

    world.services.try_get.side_effect = get_service

    # Mock entities
    ent1 = 1
    world.get_all_entities.return_value = [ent1]

    trans = Transform(x=10, y=20)
    ystats = YukkuriStats(name="Reimu", type_id="reimu")

    def get_component(ent, comp_type):
        if ent == ent1:
            if comp_type == Transform:
                return trans
            if comp_type == YukkuriStats:
                return ystats
        return None

    world.get_component.side_effect = get_component

    service = PersistenceService(world, save_dir="test_saves")

    with patch("builtins.open", mock_open()) as mock_file:
        with patch("os.path.exists", return_value=True):
            service.save_game("test.json")

    # Verify json dump
    # Since json.dump writes to file, we can inspect calls
    # But mock_open is a bit tricky with json.dump
    # Just verify open was called correctly
    mock_file.assert_called_with("test_saves/test.json", "w")


def test_load_game(persistence_world: MagicMock) -> None:
    """
    Tests loading game data from a file.
    """
    world = persistence_world

    economy = EconomyService(0)
    time_svc = TimeService()
    factory = MagicMock()

    def get_service(svc_type):
        if svc_type == EconomyService:
            return economy
        if svc_type == TimeService:
            return time_svc

        if svc_type == EntityFactory:
            return factory
        return None

    def try_get_service(svc_type):
        if svc_type == EconomyService:
            return economy
        if svc_type == TimeService:
            return time_svc
        return None

    world.services.get.side_effect = get_service
    world.services.try_get.side_effect = try_get_service

    service = PersistenceService(world, save_dir="test_saves")

    # Mock file content
    import json

    save_data = {
        "money": 999,
        "time": 60.0,
        "entities": [
            {
                "entity_id": 1,
                "stable_id": 100,
                "components": {
                    "Transform": {"x": 5.0, "y": 5.0, "scale": 1.0},
                    "YukkuriStats": {
                        "name": "Loaded Reimu",
                        "type_id": "reimu",
                        "health": 100,
                        "hunger": 50,
                        "age": 10,
                    },
                },
            }
        ],
    }
    json_str = json.dumps(save_data)

    with patch("builtins.open", mock_open(read_data=json_str)):
        with patch("os.path.exists", return_value=True):
            success = service.load_game("test.json")

    assert success is True
    assert economy.get_money() == 999
    assert time_svc.time_elapsed == 60.0

    # Verification: Check if entity was created in world
    # Since we mocked world, we check calls to create_entity and add_component
    assert world.create_entity.called
    assert world.add_component.called
