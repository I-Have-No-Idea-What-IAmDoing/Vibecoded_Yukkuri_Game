import pytest
import os
import json
from unittest.mock import MagicMock
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.systems.persistence_system import PersistenceSystem
from yukkuri_game.game.player_components import PlayerState
from yukkuri_game.game.components import Transform
from yukkuri_game.game.yukkuri_components import YukkuriStats, ItemStats
from yukkuri_game.game.entity_factory import EntityFactory

@pytest.fixture
def world():
    w = World()
    # Register mocks for services used in load
    # Explicitly using EntityFactory type as key
    w.services.register(MagicMock(), service_type=EntityFactory)
    return w

@pytest.fixture
def persistence_system(world):
    sys = PersistenceSystem()
    world.add_system(sys)
    return sys

def test_save_player_state(world, persistence_system, tmp_path):
    # Setup player
    player = world.create_entity()
    save_dir = str(tmp_path)
    world.add_component(player, PlayerState(money=500, time_elapsed=123.45, save_dir=save_dir))

    # Save
    persistence_system.save("save_player.json")

    # Verify file
    path = os.path.join(save_dir, "save_player.json")
    assert os.path.exists(path)

    with open(path, "r") as f:
        data = json.load(f)

    assert data["player"]["money"] == 500
    assert data["player"]["time"] == 123.45
    assert data["player"]["save_dir"] == save_dir

def test_save_entities(world, persistence_system, tmp_path):
    # Setup save dir via player (needed for save location)
    player = world.create_entity()
    save_dir = str(tmp_path)
    world.add_component(player, PlayerState(save_dir=save_dir))

    # Setup Yukkuri
    y1 = world.create_entity()
    world.add_component(y1, Transform(x=10, y=20))
    world.add_component(y1, YukkuriStats(name="TestY", type_id="reimu", health=50))

    # Setup Item
    i1 = world.create_entity()
    world.add_component(i1, Transform(x=30, y=40))
    world.add_component(i1, ItemStats(name="Cookie", type_id="cookie", cost=10))

    # Save
    persistence_system.save("save_entities.json")

    # Verify
    path = os.path.join(save_dir, "save_entities.json")
    with open(path, "r") as f:
        data = json.load(f)

    assert len(data["entities"]) == 2

    # Check content
    y_data = next((e for e in data["entities"] if "yukkuri" in e), None)
    assert y_data
    assert y_data["transform"]["x"] == 10.0
    assert y_data["yukkuri"]["name"] == "TestY"

    i_data = next((e for e in data["entities"] if "item" in e), None)
    assert i_data
    assert i_data["transform"]["x"] == 30.0
    assert i_data["item"]["type_id"] == "cookie"

def test_load_game(world, persistence_system, tmp_path):
    # Create a save file
    save_dir = str(tmp_path)
    data = {
        "player": {"money": 999, "time": 10.0, "save_dir": save_dir},
        "entities": [
            {
                "transform": {"x": 100, "y": 100},
                "yukkuri": {
                    "type_id": "reimu",
                    "name": "LoadedY",
                    "health": 100,
                    "hunger": 0,
                    "happiness": 50,
                    "badges": 0,
                    "age": 0
                }
            }
        ]
    }

    path = os.path.join(save_dir, "load_test.json")
    with open(path, "w") as f:
        json.dump(data, f)

    # Setup player state so system knows where to look (or we can rely on default if we didn't randomize dir)
    # System looks in PlayerState first.
    player = world.create_entity()
    world.add_component(player, PlayerState(save_dir=save_dir))

    # Mock factory
    factory = world.services.get(EntityFactory)
    factory.create_yukkuri.return_value = 10 # Fake ID

    def create_yukkuri_side_effect(tid, x, y):
        e = world.create_entity()
        world.add_component(e, Transform(x, y))
        world.add_component(e, YukkuriStats(tid, tid)) # Default stats
        return e

    factory.create_yukkuri.side_effect = create_yukkuri_side_effect

    # Run load
    assert persistence_system.load("load_test.json")

    # Check Player State updated
    p_state = world.get_component(player, PlayerState)
    assert p_state.money == 999
    assert p_state.time_elapsed == 10.0

    # Find the non-player entity
    entities = world.get_components(YukkuriStats)
    assert len(entities) == 1
    eid = list(entities.keys())[0]

    stats = world.get_component(eid, YukkuriStats)
    assert stats.name == "LoadedY"

    trans = world.get_component(eid, Transform)
    assert trans.x == 100.0

def test_load_no_file(world, persistence_system, tmp_path):
    player = world.create_entity()
    world.add_component(player, PlayerState(save_dir=str(tmp_path)))

    assert not persistence_system.load("missing.json")
