import pytest
from unittest.mock import MagicMock
from src.yukkuri_game.game.game_manager import GameManager
from src.yukkuri_game.engine.ecs import World
from src.yukkuri_game.game.services import EconomyService, TimeService, PersistenceService
from src.yukkuri_game.game.yukkuri_components import YukkuriStats
from src.yukkuri_game.game.entity_factory import EntityFactory

@pytest.fixture
def game_manager_world():
    world = World()

    # Setup services
    economy = EconomyService(1000)
    time_svc = TimeService()
    persistence = MagicMock(spec=PersistenceService)
    factory = MagicMock(spec=EntityFactory)

    # Use a real service locator or mock it properly?
    # World has real services locator.
    # Register services manually if needed, but World usually has empty services.
    # World doesn't expose register directly on self.services (it's ServiceLocator).

    # register(instance, service_type=Type)
    world.services.register(economy, EconomyService)
    world.services.register(time_svc, TimeService)
    world.services.register(persistence, PersistenceService)
    # EntityFactory class itself is used as key in GameManager, not the instance.
    # But ServiceLocator.register takes Type[T] and T.
    # GameManager does: self.factory = world.services.get(EntityFactory)
    # So we must register with EntityFactory type.
    # The method signature for register is: register(self, instance: Any, service_type: Optional[Type[Any]] = None, replace: bool = False)
    # But in the test code above, I am calling: world.services.register(EntityFactory, factory)
    # which maps to register(instance=EntityFactory, service_type=factory)
    # This is WRONG. EntityFactory is the type (key), factory is the instance.
    # It should be: world.services.register(factory, EntityFactory)

    world.services.register(factory, EntityFactory)

    return world, economy, time_svc, persistence, factory

def test_game_manager_properties(game_manager_world):
    world, economy, time_svc, _, _ = game_manager_world
    gm = GameManager(world)

    # Test money property delegation
    assert gm.money == 1000
    gm.money = 2000
    assert gm.money == 2000
    assert economy.get_money() == 2000

    # Test time_elapsed property delegation
    assert gm.time_elapsed == 0.0
    gm.time_elapsed = 10.0
    assert gm.time_elapsed == 10.0
    assert time_svc.time_elapsed == 10.0

def test_game_manager_sell_yukkuri(game_manager_world):
    world, economy, _, _, _ = game_manager_world
    gm = GameManager(world)

    # Create mock yukkuri
    yukkuri = world.create_entity()
    stats = YukkuriStats(
        name="TestYukkuri",
        type_id="test",
        happiness=80,
        badges=1,
        health=100,
        max_health=100,
        age=120 # 2 minutes
    )
    world.add_component(yukkuri, stats)

    initial_money = economy.get_money()

    # Calculate expected value
    # Base 100
    # Happiness 80 * 2 = 160
    # Badges 1 * 500 = 500
    # Health penalty 0
    # Age bonus 2 * 10 = 20
    # Total = 100 + 160 + 500 + 20 = 780
    expected_value = 780

    value = gm.sell_yukkuri(yukkuri)

    assert value == expected_value
    assert economy.get_money() == initial_money + expected_value

    # Entity should be destroyed
    assert not world.entity_exists(yukkuri)

def test_game_manager_sell_invalid_entity(game_manager_world):
    world, economy, _, _, _ = game_manager_world
    gm = GameManager(world)

    # Entity without stats
    item = world.create_entity()

    initial_money = economy.get_money()
    value = gm.sell_yukkuri(item)

    assert value == 0
    assert economy.get_money() == initial_money
    # Entity remains (sell_yukkuri checks for stats before destroying? No, it checks stats then proceeds)
    # If stats missing, it returns 0 and does NOT destroy.
    assert world.entity_exists(item)

def test_game_manager_save_load_delegation(game_manager_world):
    world, _, _, persistence, _ = game_manager_world
    gm = GameManager(world)

    gm.save_game("mysave.json")
    persistence.save_game.assert_called_with("mysave.json")

    gm.load_game("mysave.json")
    persistence.load_game.assert_called_with("mysave.json")
