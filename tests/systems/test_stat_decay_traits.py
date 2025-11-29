
import pytest
from unittest.mock import MagicMock
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.yukkuri_components import YukkuriStats, Personality
from yukkuri_game.game.systems.emotion_system import EmotionSystem
from yukkuri_game.config import StatDecaySettings
from yukkuri_game.game.trait_service import TraitService

@pytest.fixture
def decay_settings():
    settings = StatDecaySettings()
    settings.hunger = 1.0
    settings.happiness = 1.0
    settings.energy = 1.0
    settings.social = 1.0
    settings.cleanliness = 1.0
    return settings

@pytest.fixture
def mock_trait_service():
    service = MagicMock(spec=TraitService)
    # Default behavior: unknown trait returns None
    service.get_trait.return_value = None
    return service

def test_stat_decay_with_trait_modifier(decay_settings, mock_trait_service):
    world = World()
    # Explicitly register as TraitService type because mock has type MagicMock
    world.services.register(mock_trait_service, service_type=TraitService)

    system = EmotionSystem(decay_settings)

    # Setup trait data
    # GLUTTON: hunger_decay = 1.5
    glutton_data = {
        "stat_modifiers": {
            "hunger_decay": 1.5
        }
    }
    mock_trait_service.get_trait.side_effect = lambda t: glutton_data if t == "GLUTTON" else None

    # Create entity
    entity = world.create_entity()
    stats = YukkuriStats(name="Glutton", type_id="test", hunger=0.0)
    # Add Personality with GLUTTON trait
    world.add_component(entity, stats)
    world.add_component(entity, Personality(traits={"GLUTTON"}))

    # Update for 1 second
    system.update(world, 1.0)

    # Expected: Base (1.0) * Modifier (1.5) * dt (1.0) = 1.5
    assert stats.hunger == 1.5

def test_stat_decay_without_trait_modifier(decay_settings, mock_trait_service):
    world = World()
    world.services.register(mock_trait_service, service_type=TraitService)

    system = EmotionSystem(decay_settings)

    # Create entity
    entity = world.create_entity()
    stats = YukkuriStats(name="Normal", type_id="test", hunger=0.0)
    # Add Personality with NO traits
    world.add_component(entity, stats)
    world.add_component(entity, Personality(traits=set()))

    # Update for 1 second
    system.update(world, 1.0)

    # Expected: Base (1.0) * Modifier (1.0) * dt (1.0) = 1.0
    assert stats.hunger == 1.0

def test_stat_decay_multiple_modifiers(decay_settings, mock_trait_service):
    world = World()
    world.services.register(mock_trait_service, service_type=TraitService)

    system = EmotionSystem(decay_settings)

    # Setup trait data
    # GLUTTON: hunger_decay = 1.5
    # FAST_HUNGER: hunger_decay = 2.0
    def get_trait(t):
        if t == "GLUTTON":
            return {"stat_modifiers": {"hunger_decay": 1.5}}
        if t == "FAST_HUNGER":
            return {"stat_modifiers": {"hunger_decay": 2.0}}
        return None

    mock_trait_service.get_trait.side_effect = get_trait

    # Create entity
    entity = world.create_entity()
    stats = YukkuriStats(name="SuperHungry", type_id="test", hunger=0.0)
    # Add Personality with both traits
    world.add_component(entity, stats)
    world.add_component(entity, Personality(traits={"GLUTTON", "FAST_HUNGER"}))

    # Update for 1 second
    system.update(world, 1.0)

    # Expected: Base (1.0) * Mod1 (1.5) * Mod2 (2.0) * dt (1.0) = 3.0
    assert stats.hunger == 3.0
