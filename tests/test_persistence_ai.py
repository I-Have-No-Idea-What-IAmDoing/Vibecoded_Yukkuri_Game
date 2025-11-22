import pytest
import os
import json
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.services import EconomyService, PersistenceService, TimeService
from yukkuri_game.game.components import Transform
from yukkuri_game.game.yukkuri_components import YukkuriStats, ItemStats, AIState
from yukkuri_game.game.entity_factory import EntityFactory
from yukkuri_game.engine.resource_manager import ResourceManager
from unittest.mock import MagicMock

@pytest.fixture
def setup_world():
    world = World()

    # Mock resources
    resources = MagicMock(spec=ResourceManager)
    resources.yukkuri_types = {
        "reimu": {"image": "reimu.png", "width": 64, "height": 64, "max_health": 100}
    }
    resources.item_types = {
        "food": {"image": "food.png", "width": 32, "height": 32, "name": "Food", "cost": 10}
    }

    world.services.register(resources, ResourceManager)

    # Register services
    economy = EconomyService()
    world.services.register(economy)

    time_service = TimeService()
    world.services.register(time_service)

    factory = EntityFactory(world)
    world.services.register(factory)

    persistence = PersistenceService(world, save_dir="test_saves_ai")
    world.services.register(persistence)

    return world, persistence

def test_persistence_ai_state(setup_world):
    world, persistence = setup_world
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
    assert new_ai.current_target_id != i_id # Should not be the old ID (unless by chance they are same, but in this test setup with clears, likely different or same if deterministic, but main point is it points to valid entity)

    # Double check existence of target
    assert world.entity_exists(new_ai.current_target_id)

    assert new_ai.state_data == {"duration": 5.0}
    assert new_ai.action_progress == 2.5

    # Tuples in JSON become lists
    assert new_ai.path == [[100, 100], [150, 150], [200, 200]]

    # Cleanup
    if os.path.exists(os.path.join("test_saves_ai", save_file)):
        os.remove(os.path.join("test_saves_ai", save_file))
    if os.path.exists("test_saves_ai"):
        os.rmdir("test_saves_ai")
