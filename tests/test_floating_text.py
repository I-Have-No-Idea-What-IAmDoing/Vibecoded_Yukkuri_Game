import pytest
from src.yukkuri_game.engine.ecs import World
from src.yukkuri_game.game.components import Transform, FloatingText
from src.yukkuri_game.game.systems.floating_text_system import FloatingTextSystem

def test_floating_text_creation():
    world = World()
    entity = world.create_entity()
    world.add_component(entity, Transform(x=100, y=100))
    world.add_component(entity, FloatingText(text="Test", lifetime=1.0))

    assert world.has_component(entity, FloatingText)
    text_comp = world.get_component(entity, FloatingText)
    assert text_comp.text == "Test"
    assert text_comp.age == 0.0

def test_floating_text_update():
    world = World()
    system = FloatingTextSystem()

    entity = world.create_entity()
    world.add_component(entity, Transform(x=100, y=100))
    world.add_component(entity, FloatingText(text="Test", lifetime=1.0, velocity_y=-10.0))

    # Update 0.5 seconds
    system.update(world, 0.5)

    transform = world.get_component(entity, Transform)
    text_comp = world.get_component(entity, FloatingText)

    assert text_comp.age == 0.5
    assert transform.y == 95.0 # 100 + (-10 * 0.5)

def test_floating_text_expiration():
    world = World()
    system = FloatingTextSystem()

    entity = world.create_entity()
    world.add_component(entity, Transform(x=100, y=100))
    world.add_component(entity, FloatingText(text="Test", lifetime=1.0))

    # Update 1.1 seconds
    system.update(world, 1.1)

    # Entity should be destroyed
    # Note: esper destroys entities immediately or deferred?
    # Standard esper usually does immediately if called via delete_entity,
    # but here we use world.destroy_entity which wraps esper.

    # Let's check if entity exists.
    # Esper doesn't have a simple "entity_exists" check that is robust if IDs are reused,
    # but checking component existence should raise KeyError or return None.

    # Our World wrapper returns None if component missing, not KeyError
    assert world.get_component(entity, FloatingText) is None
