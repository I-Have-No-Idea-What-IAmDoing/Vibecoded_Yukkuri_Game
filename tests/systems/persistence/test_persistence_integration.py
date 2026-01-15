"""
Integration tests for Persistence Service.
Merges previous test_persistence_ai.py and test_persistence_economy.py (persistence parts).
"""

import pytest
import os
from unittest.mock import MagicMock
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.services import EconomyService, PersistenceService, TimeService
from yukkuri_game.game.components import Transform
from yukkuri_game.game.yukkuri_components import YukkuriStats, ItemStats, AIState, Needs
from yukkuri_game.game.entity_factory import EntityFactory
from yukkuri_game.engine.resource_manager import ResourceManager
from yukkuri_game.game.components_persistence import StableIDComponent, Persistable

@pytest.fixture
def setup_persistence_world():
    world = World()

    # Mock resources
    resources = MagicMock(spec=ResourceManager)
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

    save_dir = "test_saves_integration"
    persistence = PersistenceService(world, save_dir=save_dir)
    world.services.register(persistence)

    yield world, persistence

    # Cleanup
    if os.path.exists(save_dir):
        import shutil
        shutil.rmtree(save_dir, ignore_errors=True)

def test_persistence_ai_state(setup_persistence_world):
    world, persistence = setup_persistence_world
    factory = world.services.get(EntityFactory)

    # 1. Setup: Create Yukkuri, Create Item
    y_id = factory.create_yukkuri("reimu", 100, 100)
    i_id = factory.create_item("food", 200, 200)

    # 2. Set AI State
    ai = world.get_component(y_id, AIState)
    assert ai is not None
    ai.current_action = "Eating"
    ai.current_target_id = i_id
    ai.state_data = {"duration": 5.0}
    ai.action_progress = 2.5
    ai.path = [(100, 100), (150, 150), (200, 200)]

    # 3. Save
    save_file = "test_ai_save.json"
    persistence.save_game(save_file)

    # 4. Clear World (Simulate new session)
    world.destroy_entity(y_id)
    world.destroy_entity(i_id)
    assert not world.entity_exists(y_id)
    assert not world.entity_exists(i_id)

    # 5. Load
    persistence.load_game(save_file)

    # 6. Verify
    entities = world.get_entities_with(YukkuriStats)
    assert len(entities) == 1
    new_y_id = entities[0]

    items = world.get_entities_with(ItemStats)
    assert len(items) == 1
    new_i_id = items[0]

    # Check AI State restoration
    new_ai = world.get_component(new_y_id, AIState)
    assert new_ai is not None
    assert new_ai.current_action == "Eating"

    # The new target ID should match the new ID of the item
    assert new_ai.current_target_id == new_i_id
    
    # Tuples in JSON become lists
    assert new_ai.path == [[100, 100], [150, 150], [200, 200]]


def test_persistence_round_trip(setup_persistence_world):
    world, persistence = setup_persistence_world
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
    
    # Check for EmotionalState if it exists and set happiness
    try:
        from yukkuri_game.game.yukkuri_components import EmotionalState
        emo = world.get_component(y_id, EmotionalState)
        if emo:
            emo.happiness = 99.0
    except ImportError:
        pass

    i_id = factory.create_item("food", 300, 400)

    # Add an entity without Transform to test "get_all_entities"
    broken_id = world.create_entity()
    world.add_component(broken_id, YukkuriStats(type_id="reimu", name="Broken"))
    world.add_component(broken_id, Needs(max_health=100, health=100))
    world.add_component(broken_id, StableIDComponent(id=world.get_next_stable_id()))
    world.add_component(broken_id, Persistable())

    # Save
    save_file = "test_economy_round_trip.json"
    persistence.save_game(save_file)

    # Modify state
    economy.set_money(0)
    time_service.time_elapsed = 0.0
    world.destroy_entity(y_id)
    world.destroy_entity(i_id)
    world.destroy_entity(broken_id)

    # Load
    persistence.load_game(save_file)

    # Verify
    assert economy.get_money() == 1234
    assert time_service.time_elapsed == 123.45

    # Check entities
    entities = world.get_entities_with(YukkuriStats)
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
