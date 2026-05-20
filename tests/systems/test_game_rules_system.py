"""
Tests for the GameRulesSystem.
"""

import pytest
from test_utils import make_configured_world
from unittest.mock import MagicMock
from yukkuri_game.game.systems.game_rules_system import GameRulesSystem
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.services import EconomyService
from yukkuri_game.engine.services.time_service import TimeService
from yukkuri_game.game.save_manager import SaveManager
from yukkuri_game.game.components import YukkuriStats, Needs, EmotionalState
from yukkuri_game.game.entity_factory import EntityFactory
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.engine.audio import AudioManager


@pytest.fixture
def game_rules_world():
    """
    Sets up a world with mocked services for GameRulesSystem testing.
    """
    world = World()

    # Setup services
    economy = EconomyService(1000)
    time_svc = TimeService()
    persistence = MagicMock(spec=SaveManager)
    factory = MagicMock(spec=EntityFactory)
    event_bus = EventBus()  # Use real EventBus to check subscriptions if needed, or mock if we check published events.
    # The system subscribes in __init__.

    audio = MagicMock(spec=AudioManager)

    # register(instance, service_type=Type)
    world.services.register(economy, EconomyService)
    world.services.register(time_svc, TimeService)
    world.services.register(persistence, SaveManager)
    world.services.register(factory, EntityFactory)
    world.services.register(event_bus, EventBus)
    world.services.register(audio, AudioManager)

    return world, economy, time_svc, persistence, factory, event_bus


def test_game_rules_sell_yukkuri(game_rules_world) -> None:
    """
    Tests the sell_yukkuri logic: value calculation, money addition, and entity destruction.
    """
    world, economy, _, _, _, event_bus = game_rules_world

    system = GameRulesSystem()
    world.add_system(system)

    # Create mock yukkuri
    yukkuri = world.create_entity()
    stats = YukkuriStats(
        name="TestYukkuri",
        type_id="test",
        badges=1,
        age=120,  # 2 minutes
    )
    needs = Needs(health=100, max_health=100)
    emotional = EmotionalState(happiness=80.0)
    world.add_component(yukkuri, stats)
    world.add_component(yukkuri, needs)
    world.add_component(yukkuri, emotional)

    initial_money = economy.money

    # Calculate expected value
    # Base 100
    # Happiness (80 + 100) = 180
    # Badges 1 * 500 = 500
    # Health penalty 0
    # Age bonus 2 * 10 = 20
    # Total = 100 + 180 + 500 + 20 = 800
    expected_value = 800

    value = system.sell_yukkuri(yukkuri)
    world.commands.apply_all()

    assert value == expected_value
    assert economy.money == initial_money + expected_value

    # Entity should be destroyed
    assert not world.entity_exists(yukkuri)


def test_game_rules_sell_invalid_entity(game_rules_world) -> None:
    """
    Tests that selling an entity without stats does nothing.
    """
    world, economy, _, _, _, event_bus = game_rules_world

    system = GameRulesSystem()
    world.add_system(system)

    # Entity without stats
    item = world.create_entity()

    initial_money = economy.money
    value = system.sell_yukkuri(item)

    assert value == 0
    assert economy.money == initial_money
    # Entity remains (sell_yukkuri checks for stats before destroying)
    # If stats missing, it returns 0 and does NOT destroy.
    assert world.entity_exists(item)

