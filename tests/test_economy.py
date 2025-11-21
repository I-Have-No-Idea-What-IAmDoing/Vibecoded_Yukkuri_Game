import pytest
from unittest.mock import MagicMock
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.player_components import PlayerState
from yukkuri_game.game.game_manager import GameManager

@pytest.fixture
def world():
    return World()

@pytest.fixture
def game_manager(world):
    # We need to import EntityFactory to register it as type
    from yukkuri_game.game.entity_factory import EntityFactory
    # Register the Mock instance, explicitly using EntityFactory as the key
    world.services.register(MagicMock(), service_type=EntityFactory)

    return GameManager(world)

def test_money_property_access(game_manager, world):
    # Check initial money
    assert game_manager.money == 1000

    # Modify money via property
    game_manager.money += 500
    assert game_manager.money == 1500

    # Verify change in component
    player_entities = world.get_components(PlayerState)
    assert len(player_entities) == 1
    state = list(player_entities.values())[0]
    assert state.money == 1500

def test_money_direct_component_modification(game_manager, world):
    # Get component directly
    player_entities = world.get_components(PlayerState)
    state = list(player_entities.values())[0]

    # Modify component
    state.money = 200

    # Verify GameManager sees it
    assert game_manager.money == 200

def test_time_property_access(game_manager, world):
    assert game_manager.time_elapsed == 0.0

    game_manager.time_elapsed = 60.0

    player_entities = world.get_components(PlayerState)
    state = list(player_entities.values())[0]
    assert state.time_elapsed == 60.0

def test_multiple_game_managers_share_state(world):
    # Since state is in ECS, multiple managers (if they existed) would see same state
    from yukkuri_game.game.entity_factory import EntityFactory
    world.services.register(MagicMock(), service_type=EntityFactory)

    gm1 = GameManager(world)
    gm2 = GameManager(world)

    gm1.money = 500
    assert gm2.money == 500
