
import pytest
from ..game.yukkuri_components import EmotionalState, Personality, PersonalityAxis
from ..game.systems.emotion_system import EmotionSystem
from ..config import StatDecaySettings
from ..engine.ecs import World

@pytest.fixture
def world():
    return World()

@pytest.fixture
def emotion_system():
    settings = StatDecaySettings()
    # Speed up decay for testing
    settings.stress = 10.0
    settings.happiness = 10.0
    return EmotionSystem(settings)

def test_stress_decay(world, emotion_system):
    entity = world.create_entity()
    # Initial High Stress
    world.add_component(entity, EmotionalState(happiness=0, stress=100))
    world.add_component(entity, Personality()) # Needed for trait modifiers check
    # Also need YukkuriStats for the system to process it
    from ..game.yukkuri_components import YukkuriStats
    world.add_component(entity, YukkuriStats(name="Test", type_id="test"))

    # Decay
    emotion_system.update(world, 1.0)

    state = world.get_component(entity, EmotionalState)
    assert state.stress < 100.0
    assert state.stress == 90.0 # 100 - 10*1.0

def test_happiness_decay_to_baseline(world, emotion_system):
    entity = world.create_entity()
    # Initial High Happiness
    world.add_component(entity, EmotionalState(happiness=100, stress=0))
    world.add_component(entity, Personality())
    from ..game.yukkuri_components import YukkuriStats
    world.add_component(entity, YukkuriStats(name="Test", type_id="test"))

    # Decay (towards 50)
    emotion_system.update(world, 1.0)

    state = world.get_component(entity, EmotionalState)
    assert state.happiness < 100.0
    assert state.happiness == 90.0

    # Check baseline approach from below
    state.happiness = 0.0
    emotion_system.update(world, 1.0)
    assert state.happiness > 0.0
    assert state.happiness == 10.0

def test_dominant_emotion_quadrants(world):
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
