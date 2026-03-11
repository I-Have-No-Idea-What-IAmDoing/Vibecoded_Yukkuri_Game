"""
Tests for Economy and Persistence services.
"""

import pytest
import os
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.services import EconomyService, PersistenceService, TimeService
from yukkuri_game.game.components import Transform
from yukkuri_game.game.yukkuri_components import YukkuriStats, Needs, ItemStats
from yukkuri_game.game.entity_factory import EntityFactory
from yukkuri_game.engine.resource_manager import ResourceManager
from yukkuri_game.game.components_persistence import StableIDComponent, Persistable
from unittest.mock import MagicMock


@pytest.fixture
def world() -> World:
    """
    Creates a new ECS World.
    """
    return World()


@pytest.fixture
def economy_service() -> EconomyService:
    """
    Creates a new EconomyService.
    """
    return EconomyService()


def test_economy_initial_state(economy_service: EconomyService) -> None:
    """
    Tests initial money value.
    """
    assert economy_service.money == 1000


def test_economy_add_money(economy_service: EconomyService) -> None:
    """
    Tests adding money.
    """
    economy_service.add_money(500)
    assert economy_service.money == 1500


def test_economy_remove_money(economy_service: EconomyService) -> None:
    """
    Tests removing money.
    """
    assert economy_service.remove_money(500) is True
    assert economy_service.money == 500

    assert economy_service.remove_money(1000) is False
    assert economy_service.money == 500


def test_economy_set_money(economy_service: EconomyService) -> None:
    """
    Tests setting money directly.
    """
    economy_service.set_money(2000)
    assert economy_service.money == 2000

    economy_service.set_money(-100)
    assert economy_service.money == 0


@pytest.fixture
def setup_world(world: World) -> tuple[World, PersistenceService]:
    """
    Sets up a world with all necessary services for persistence testing.
    """
    # Mock resources
    resources = MagicMock(spec=ResourceManager)
    # Mock the attributes accessed by EntityFactory
    resources.yukkuri_types = {
        "reimu": {"image": "reimu.png", "width": 64, "height": 64, "max_health": 100}
    }
    resources.item_types = {
        "food": {
            "image": "food.png",
            "width": 32,
            "height": 32,
            "name": "Food",
            "cost": 10,
        }
    }

    # Mock tuning
    mock_tuning = MagicMock()
    mock_tuning.visuals.movement.bob_height = 10.0
    mock_tuning.visuals.movement.bob_speed = 5.0
    resources.tuning = mock_tuning

    world.services.register(resources, ResourceManager)

    # Register services
    economy = EconomyService()
    world.services.register(economy)

    time_service = TimeService()
    world.services.register(time_service)

    factory = EntityFactory(world)
    world.services.register(factory)

    persistence = PersistenceService(world, save_dir="test_saves")
    world.services.register(persistence)

    return world, persistence


def test_persistence_round_trip(setup_world: tuple[World, PersistenceService]) -> None:
    """
    Tests saving and loading game state, verifying economy, time, and entities are restored.
    """
    world, persistence = setup_world
    economy = world.services.get(EconomyService)
    time_service = world.services.get(TimeService)
    factory = world.services.get(EntityFactory)

    # Set up initial state
    economy.set_money(1234)
    time_service.time_elapsed = 123.45

    y_id = factory.create_yukkuri("reimu", 100, 200)
    # Set specific stats
    stats = world.get_component(y_id, YukkuriStats)
    stats.name = "TestReimu"
    # Note: Happiness is now in EmotionalState, but stats might still have a property or we check components
    # The previous test accessed stats.happiness which might be removed.
    # Let's assume stats.happiness was moved or kept for compatibility.
    # If removed, we should check EmotionalState.
    # Given we just documented components, we know YukkuriStats doesn't have happiness directly
    # but the persistence service saves "happiness" from EmotionalState.
    # The factory creates EmotionalState.
    from yukkuri_game.game.yukkuri_components import EmotionalState

    emo = world.get_component(y_id, EmotionalState)
    if emo:
        emo.happiness = 99.0

    i_id = factory.create_item("food", 300, 400)

    # Add an entity without Transform to test "get_all_entities"
    broken_id = world.create_entity()
    # Just add YukkuriStats and Needs
    world.add_component(broken_id, YukkuriStats(type_id="reimu", name="Broken"))
    world.add_component(broken_id, Needs(max_health=100, health=100))
    world.add_component(broken_id, StableIDComponent(id=world.get_next_stable_id()))
    world.add_component(broken_id, Persistable())

    # Save
    save_file = "test_save.json"
    persistence.save_game(save_file)

    # Modify state (to verify load overwrites/restores)
    economy.set_money(0)
    time_service.time_elapsed = 0.0
    world.destroy_entity(y_id)
    world.destroy_entity(i_id)
    world.destroy_entity(broken_id)

    assert economy.money == 0
    assert time_service.time_elapsed == 0.0
    assert not world.entity_exists(y_id)

    # Load
    persistence.load_game(save_file)

    # Verify
    assert economy.money == 1234
    assert time_service.time_elapsed == 123.45

    # Check entities
    # IDs might change, so check content
    entities = world.get_entities_with(YukkuriStats)
    # We expect 2 entities: the normal one and the "broken" one
    assert len(entities) == 2

    names = [world.get_component(e, YukkuriStats).name for e in entities]
    assert "TestReimu" in names
    assert "Broken" in names

    # Find the one with transform
    reimu_entity = next(
        e for e in entities if world.get_component(e, YukkuriStats).name == "TestReimu"
    )

    trans = world.get_component(reimu_entity, Transform)
    assert trans.x == 100
    assert trans.y == 200

    items = world.get_entities_with(ItemStats)
    assert len(items) == 1
    new_i_id = items[0]
    new_item_trans = world.get_component(new_i_id, Transform)
    assert new_item_trans.x == 300
    assert new_item_trans.y == 400

    # Cleanup
    if os.path.exists(os.path.join("test_saves", save_file)):
        os.remove(os.path.join("test_saves", save_file))
    if os.path.exists("test_saves"):
        os.rmdir("test_saves")
