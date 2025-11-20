import pytest
from unittest.mock import MagicMock
from src.yukkuri_game.game.entity_factory import EntityFactory
from src.yukkuri_game.engine.ecs import World
from src.yukkuri_game.game.components import Transform, Sprite, Selectable
from src.yukkuri_game.game.yukkuri_components import YukkuriStats, AIState, ItemStats

@pytest.fixture
def entity_factory():
    world = World()
    rm = MagicMock()

    rm.yukkuri_types = {
        "reimu": {
            "image": "reimu.png",
            "width": 64,
            "height": 64,
            "max_health": 150
        }
    }

    rm.item_types = {
        "cookie": {
            "name": "Sweet Cookie",
            "image": "cookie.png",
            "width": 32,
            "height": 32,
            "cost": 10,
            "nutrition": 20,
            "fun": 5,
            "comfort": 0,
            "is_portable": True
        }
    }

    return EntityFactory(world, rm)

def test_create_yukkuri(entity_factory):
    factory = entity_factory
    entity_id = factory.create_yukkuri("reimu", 100, 200)

    world = factory.world
    assert entity_id in world._entities

    # Check Transform
    transform = world.get_component(entity_id, Transform)
    assert transform is not None
    assert transform.x == 100
    assert transform.y == 200

    # Check Sprite
    sprite = world.get_component(entity_id, Sprite)
    assert sprite.image_name == "reimu.png"
    assert sprite.width == 64
    assert sprite.height == 64

    # Check Selectable
    assert world.has_component(entity_id, Selectable)

    # Check Stats
    stats = world.get_component(entity_id, YukkuriStats)
    assert stats.type_id == "reimu"
    assert stats.max_health == 150
    assert stats.health == 150

    # Check AI
    assert world.has_component(entity_id, AIState)

def test_create_yukkuri_unknown(entity_factory):
    factory = entity_factory
    with pytest.raises(ValueError, match="Unknown yukkuri type"):
        factory.create_yukkuri("marisa", 0, 0)

def test_create_item(entity_factory):
    factory = entity_factory
    entity_id = factory.create_item("cookie", 50, 50)

    world = factory.world

    # Check Transform
    transform = world.get_component(entity_id, Transform)
    assert transform.x == 50
    assert transform.y == 50

    # Check Sprite
    sprite = world.get_component(entity_id, Sprite)
    assert sprite.image_name == "cookie.png"

    # Check Stats
    stats = world.get_component(entity_id, ItemStats)
    assert stats.name == "Sweet Cookie"
    assert stats.nutrition == 20
    assert stats.is_portable is True

def test_create_item_unknown(entity_factory):
    factory = entity_factory
    with pytest.raises(ValueError, match="Unknown item type"):
        factory.create_item("cake", 0, 0)
