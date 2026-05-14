"""
Tests for Game Services (Economy, Time, Persistence).
"""

import pytest
from unittest.mock import MagicMock, patch
from yukkuri_game.game.services import EconomyService, TimeService
from yukkuri_game.game.save_manager import SaveManager
from yukkuri_game.engine.ecs import World

# --- Economy Service Tests ---


def test_economy_service_basics() -> None:
    """
    Tests basic economy operations (add, remove, set).
    """
    service = EconomyService(initial_money=100)
    assert service.money == 100

    service.add_money(50)
    assert service.money == 150

    success = service.remove_money(100)
    assert success is True
    assert service.money == 50

    success = service.remove_money(100)
    assert success is False
    assert service.money == 50

    service.set_money(500)
    assert service.money == 500

    service.set_money(-10)
    assert service.money == 0

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

    service.time_elapsed = 1.5
    assert service.time_elapsed == 1.5

    service.time_elapsed = 10.0
    assert service.time_elapsed == 10.0


# --- Save Manager Tests ---


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


def test_save_game(persistence_world: MagicMock, tmp_path) -> None:
    """
    Tests that save_game writes money/time to the .global.json sidecar
    and delegates entity serialization to WorldSerializer.
    """
    world = persistence_world

    economy = EconomyService(500)
    time_svc = TimeService()
    time_svc.time_elapsed = 123.45

    def get_service(svc_type):
        if svc_type == EconomyService:
            return economy
        if svc_type == TimeService:
            return time_svc
        return None

    world.services.get.side_effect = get_service

    service = SaveManager(world, [])

    mock_serializer = MagicMock()
    service.serializer = mock_serializer
    
    save_path = str(tmp_path / "test")
    service.save_game(save_path)

    import json
    global_file = tmp_path / "test.global.json"
    assert global_file.exists()
    data = json.loads(global_file.read_text())
    assert data["money"] == 500
    assert data["time"] == 123.45
    mock_serializer.save_to_file.assert_called_once()


def test_load_game(persistence_world: MagicMock, tmp_path) -> None:
    """
    Tests loading game data restores economy/time and delegates entity
    loading to WorldSerializer.
    """
    import json

    world = persistence_world

    economy = EconomyService(0)
    time_svc = TimeService()

    def get_service(svc_type):
        if svc_type == EconomyService:
            return economy
        if svc_type == TimeService:
            return time_svc
        return None

    world.services.get.side_effect = get_service
    world.services.try_get.return_value = None # mock other services returning None

    service = SaveManager(world, [])

    # Write the two stub files
    global_file = tmp_path / "test.global.json"
    level_file = tmp_path / "test.level.msgpack"
    global_file.write_text(json.dumps({"money": 999, "time": 60.0}))
    level_file.write_bytes(b"")  # real content handled by mock serializer

    mock_serializer = MagicMock()
    service.serializer = mock_serializer
    
    save_path = str(tmp_path / "test")
    service.load_game(save_path)

    assert economy.money == 999
    assert time_svc.time_elapsed == 60.0
    mock_serializer.load_from_file.assert_called_once()
