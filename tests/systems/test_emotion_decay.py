"""
Tests for the Emotion Decay system.
"""

import pytest
from test_utils import make_configured_world
from yukkuri_game.game.components import (
    EmotionalState,
    Personality,
    Needs,
)
from yukkuri_game.game.systems.emotion_system import EmotionSystem
from yukkuri_game.config import StatDecaySettings
from yukkuri_game.engine.ecs import World


@pytest.fixture  # type: ignore[misc]
def world() -> World:
    """
    Creates a new ECS World for testing.

    Returns:
        World: A new ECS World instance.
    """
    settings = StatDecaySettings()
    settings.stress = 10.0
    settings.happiness = 10.0
    world = make_configured_world(stat_decay_settings=settings)
    from yukkuri_game.engine.services.time_service import TimeService
    world.services.get(TimeService).scale = 1.0
    return world


@pytest.fixture  # type: ignore[misc]
def emotion_system(world: World) -> EmotionSystem:
    """
    Creates an EmotionSystem with accelerated decay rates for testing.

    Returns:
        EmotionSystem: The configured EmotionSystem.
    """
    system = EmotionSystem()
    world.add_system(system)
    return system


def test_stress_decay(world: World, emotion_system: EmotionSystem) -> None:
    """
    Tests that stress decays over time.

    Args:
        world (World): The ECS World fixture.
        emotion_system (EmotionSystem): The EmotionSystem fixture.
    """
    entity = world.create_entity()
    # Initial High Stress
    world.add_component(entity, EmotionalState(happiness=0, stress=100))
    world.add_component(entity, Personality())  # Needed for trait modifiers check
    # Also need YukkuriStats and Needs for the system to process it
    from yukkuri_game.game.components import YukkuriStats

    world.add_component(entity, YukkuriStats(name="Test", type_id="test"))
    world.add_component(entity, Needs())

    # Decay
    emotion_system.update(world, 1.0)

    state = world.get_component(entity, EmotionalState)
    assert state is not None
    assert state.stress < 100.0
    assert state.stress == 90.0  # 100 - 10*1.0


def test_happiness_decay_to_baseline(
    world: World, emotion_system: EmotionSystem
) -> None:
    """
    Tests that happiness decays towards the baseline (0).

    Args:
        world (World): The ECS World fixture.
        emotion_system (EmotionSystem): The EmotionSystem fixture.
    """
    entity = world.create_entity()
    # Initial High Happiness
    world.add_component(entity, EmotionalState(happiness=100, stress=0))
    world.add_component(entity, Personality())
    from yukkuri_game.game.components import YukkuriStats

    world.add_component(entity, YukkuriStats(name="Test", type_id="test"))
    world.add_component(entity, Needs())

    # Decay (towards 0 - Neutral)
    emotion_system.update(world, 1.0)

    state = world.get_component(entity, EmotionalState)
    assert state is not None
    assert state.happiness < 100.0
    assert state.happiness == 90.0

    # Check baseline approach from below
    state.happiness = -100.0
    emotion_system.update(world, 1.0)
    assert state.happiness > -100.0
    assert state.happiness == -90.0


def test_dominant_emotion_quadrants(world: World) -> None:
    """
    Tests the categorization of dominant emotions based on happiness and stress.

    Args:
        world (World): The ECS World fixture (unused but kept for consistency).
    """
    state = EmotionalState()

    # 1. Content/Relaxed (High Hap, Low Stress)
    state.happiness = 50
    state.stress = 0
    assert state.get_dominant_emotion() == "Content/Relaxed"

    # 2. Excited/Manic (High Hap, High Stress)
    state.happiness = 50
    state.stress = 80
    assert state.get_dominant_emotion() == "Excited/Manic"

    # 3. Depressed/Sulking (Low Hap, Low Stress)
    state.happiness = -50
    state.stress = 0
    assert state.get_dominant_emotion() == "Depressed/Sulking"

    # 4. Terror/Rage (Low Hap, High Stress) - BRAVERY DEPENDENT
    state.happiness = -50
    state.stress = 80

    # Default (Bravery 0 -> Terror)
    assert state.get_dominant_emotion(bravery=0) == "Terror"
    # Coward (Bravery -50 -> Terror)
    assert state.get_dominant_emotion(bravery=-50) == "Terror"
    # Brave (Bravery 50 -> Rage)
    assert state.get_dominant_emotion(bravery=50) == "Rage"
