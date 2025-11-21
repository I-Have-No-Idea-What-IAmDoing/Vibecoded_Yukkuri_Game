import pytest
from yukkuri_game.game.systems.stat_decay import StatDecaySystem
from yukkuri_game.game.yukkuri_components import YukkuriStats
from yukkuri_game.config import StatDecaySettings
from yukkuri_game.engine.ecs import World

def test_stat_decay_integration():
    """Test that StatDecaySystem uses the configured rates."""
    # Create a custom config
    custom_settings = StatDecaySettings(
        hunger=10.0,
        happiness=1.0,
        energy=2.0,
        cleanliness=5.0,
        age=0.5
    )

    system = StatDecaySystem(settings=custom_settings)
    world = World()

    # Create an entity with YukkuriStats
    entity = world.create_entity()
    stats = YukkuriStats(name="Test", type_id="test")
    # Initialize stats
    stats.hunger = 0.0
    stats.happiness = 100.0
    stats.energy = 100.0
    stats.cleanliness = 100.0
    stats.age = 0.0

    world.add_component(entity, stats)

    # Run the system for 1 second
    dt = 1.0
    system.update(world, dt)

    # Check that stats decayed according to custom settings
    # hunger += 10.0 * dt
    assert stats.hunger == pytest.approx(10.0)

    # happiness -= 1.0 * dt
    assert stats.happiness == pytest.approx(99.0)

    # energy -= 2.0 * dt
    assert stats.energy == pytest.approx(98.0)

    # cleanliness -= 5.0 * dt
    assert stats.cleanliness == pytest.approx(95.0)

    # age += 0.5 * dt
    assert stats.age == pytest.approx(0.5)

def test_stat_decay_integration_default():
    """Test that StatDecaySystem uses default rates if no settings provided."""
    system = StatDecaySystem() # Default settings
    world = World()

    entity = world.create_entity()
    stats = YukkuriStats(name="Test", type_id="test")
    stats.hunger = 0.0
    stats.happiness = 100.0

    world.add_component(entity, stats)

    dt = 1.0
    system.update(world, dt)

    # hunger += 2.0 * dt (default)
    assert stats.hunger == pytest.approx(2.0)
    # happiness -= 0.5 * dt (default)
    assert stats.happiness == pytest.approx(99.5)
