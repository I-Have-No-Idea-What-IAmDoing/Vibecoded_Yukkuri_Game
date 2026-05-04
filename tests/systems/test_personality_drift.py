"""
Tests for Personality Drift mechanics.
"""

import pytest
from test_utils import make_configured_world
from yukkuri_game.game.yukkuri_components import Personality, PersonalityAxis
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
    return make_configured_world()


@pytest.fixture  # type: ignore[misc]
def emotion_system(world: World) -> EmotionSystem:
    """
    Creates an EmotionSystem for testing.

    Returns:
        EmotionSystem: A new EmotionSystem instance.
    """
    system = EmotionSystem()
    world.add_system(system)
    return system


def test_personality_drift(world: World, emotion_system: EmotionSystem) -> None:
    """
    Tests that personality traits drift back to their base values over time.

    Args:
        world (World): The ECS World fixture.
        emotion_system (EmotionSystem): The EmotionSystem fixture.
    """
    entity = world.create_entity()

    # Setup Personality with Drift
    # Base: 0
    # Current: 50
    base = PersonalityAxis(kindness=0, energy=0, bravery=0, greed=0)
    current = PersonalityAxis(kindness=50, energy=50, bravery=50, greed=50)

    p = Personality(axis=current, base_axis=base)
    world.add_component(entity, p)

    # Also need YukkuriStats for the system to process it
    from yukkuri_game.game.yukkuri_components import YukkuriStats

    world.add_component(entity, YukkuriStats(name="Test", type_id="test"))

    # Update for enough time to trigger drift
    # Drift rate is ~0.1 per sec probability.
    # To force drift we can call _drift_personality directly or simulate long time.
    # Let's call internal method to verify logic deterministicly if possible,
    # but since it uses random, we might need to mock random or loop many times.

    # Directly test _drift_personality with mocked random
    import random

    # Store original random state? No, just seed.
    random.seed(42)

    # We loop many times to ensure drift happens
    initial_kindness = p.axis.kindness

    # Simulate 100 seconds
    for _ in range(100):
        emotion_system._drift_personality(p, 1.0)

    # Should have drifted towards 0
    assert p.axis.kindness < initial_kindness
    assert p.axis.kindness >= 0  # Should not overshoot base
