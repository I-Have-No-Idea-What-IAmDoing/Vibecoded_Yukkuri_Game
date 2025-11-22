import pytest
from unittest.mock import MagicMock, patch
from src.yukkuri_game.engine.ecs import World
from src.yukkuri_game.game.systems.poop_system import PoopSystem
from src.yukkuri_game.game.yukkuri_components import YukkuriStats, Poop, AIState
from src.yukkuri_game.game.components import Transform
from src.yukkuri_game.game.entity_factory import EntityFactory

def test_poop_system_spawning():
    world = World()
    system = PoopSystem()

    # Mock EntityFactory
    factory = MagicMock(spec=EntityFactory)
    world.services.register(factory)
    # Ensure try_get returns our mock
    world.services.try_get = MagicMock(return_value=factory)

    # Create a Yukkuri entity
    entity = world.create_entity()
    stats = YukkuriStats(name="Test", type_id="reimu")
    transform = Transform(x=100, y=100)
    ai = AIState()

    world.add_component(entity, stats)
    world.add_component(entity, transform)
    world.add_component(entity, ai)

    # Force spawn by mocking random.random to return 0.0
    with patch('random.random', return_value=0.0):
        system.spawn_chance_per_second = 0.1 # Set > 0

        # Run update
        system.update(world, 1.0)

    # Verify create_poop was called
    assert factory.create_poop.called

    # Check cleanliness reduction after pooping
    assert stats.cleanliness < 100.0 # Default starts at 100

def test_poop_system_low_cleanliness_spawning():
    world = World()
    system = PoopSystem()

    factory = MagicMock(spec=EntityFactory)
    world.services.register(factory)
    # Ensure try_get returns our mock
    world.services.try_get = MagicMock(return_value=factory)

    entity = world.create_entity()
    stats = YukkuriStats(name="Test", type_id="reimu")
    stats.cleanliness = 5.0 # Very low
    transform = Transform(x=100, y=100)
    ai = AIState()

    world.add_component(entity, stats)
    world.add_component(entity, transform)
    world.add_component(entity, ai)

    # We want to test the low cleanliness branch.
    # The code checks: if random.random() < (self.spawn_chance_per_second * 5) * dt:

    # We can't easily distinguish which check triggered it without precise control or reading internal state
    # But we can verify that with very low chance, normal won't trigger but low clean might.

    system.spawn_chance_per_second = 0.001
    # 0.001 * 1.0 = 0.001 normal chance
    # 0.001 * 5 * 1.0 = 0.005 boosted chance

    # If we patch random to return 0.003, normal fails (0.003 > 0.001), boosted passes (0.003 < 0.005)

    with patch('random.random', return_value=0.003):
        system.update(world, 1.0)

    assert factory.create_poop.called

def test_poop_smell_effect():
    world = World()
    system = PoopSystem()

    # Create Poop Entity
    poop_ent = world.create_entity()
    world.add_component(poop_ent, Poop())
    world.add_component(poop_ent, Transform(x=100, y=100))

    # Create Yukkuri Entity nearby
    yukkuri_ent = world.create_entity()
    stats = YukkuriStats(name="Test", type_id="reimu", cleanliness=100.0)
    world.add_component(yukkuri_ent, stats)
    world.add_component(yukkuri_ent, Transform(x=110, y=110)) # Dist ~14

    system.update(world, 1.0)

    # Cleanliness should decrease
    # smell_strength = 5.0 * dt(1.0) = 5.0
    assert stats.cleanliness == 95.0

    # Run again
    system.update(world, 1.0)
    assert stats.cleanliness == 90.0

def test_poop_smell_range():
    world = World()
    system = PoopSystem()

    # Poop far away
    poop_ent = world.create_entity()
    world.add_component(poop_ent, Poop())
    world.add_component(poop_ent, Transform(x=0, y=0))

    yukkuri_ent = world.create_entity()
    stats = YukkuriStats(name="Test", type_id="reimu", cleanliness=100.0)
    world.add_component(yukkuri_ent, stats)
    world.add_component(yukkuri_ent, Transform(x=500, y=500)) # Dist > 200

    system.update(world, 1.0)

    assert stats.cleanliness == 100.0
