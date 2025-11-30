import pytest
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.systems.emotion_system import EmotionSystem
from yukkuri_game.game.yukkuri_components import YukkuriStats, EmotionalState
from yukkuri_game.config import StatDecaySettings

def test_stat_decay_integration():
    """Test that EmotionSystem uses the configured rates."""
    # Create a custom config
    custom_settings = StatDecaySettings(
        hunger=10.0,
        happiness=1.0,
        energy=2.0,
        cleanliness=5.0,
        age=0.5
    )

    system = EmotionSystem(settings=custom_settings)
    world = World()

    # Create an entity with YukkuriStats
    entity = world.create_entity()
    stats = YukkuriStats(name="Test", type_id="test")
    # Initialize stats
    stats.hunger = 0.0
    stats.energy = 100.0
    stats.cleanliness = 100.0
    stats.age = 0.0

    emotional = EmotionalState()
    emotional.happiness = 100.0

    world.add_component(entity, stats)
    world.add_component(entity, emotional)

    # Run the system for 1 second
    dt = 1.0
    system.update(world, dt)

    # Check that stats decayed according to custom settings
    # hunger += 10.0 * dt
    assert stats.hunger == pytest.approx(10.0)

    # happiness -= 1.0 * dt
    assert emotional.happiness == pytest.approx(99.0)

def test_stat_decay_integration_default():
    """Test that EmotionSystem uses default rates if no settings provided."""
    system = EmotionSystem(settings=StatDecaySettings()) # Default settings
    world = World()

    entity = world.create_entity()
    stats = YukkuriStats(name="Test", type_id="test")
    stats.hunger = 0.0

    emotional = EmotionalState()
    emotional.happiness = 100.0

    world.add_component(entity, stats)
    world.add_component(entity, emotional)

    dt = 1.0
    system.update(world, dt)

    # hunger += 2.0 * dt (default)
    assert stats.hunger == pytest.approx(2.0)
    # happiness -= 0.5 * dt (default)
    assert emotional.happiness == pytest.approx(99.5)
