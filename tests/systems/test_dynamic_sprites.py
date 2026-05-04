from unittest.mock import MagicMock
from types import SimpleNamespace
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.systems.animation import AnimationSystem
from yukkuri_game.game.components import Sprite, Animator
from yukkuri_game.game.yukkuri_components import AIState, YukkuriStats
from yukkuri_game.engine.resource_manager import ResourceManager


class MockResourceManager:
    def __init__(self):
        # Use SimpleNamespace to simulate the msgspec struct access
        self.yukkuri_types = {"test_type": SimpleNamespace(image="base_image.png")}
        self.images = {}

    def load_image(self, name):
        return MagicMock()


class test_dynamic_sprites:
    pass

def test_dynamic_sprite_switching():
    """
    Test that the AnimationSystem updates the sprite image based on AIState.current_action
    when no Animator is present.
    """
    from test_utils import make_configured_world
    world = make_configured_world()

    # Register Mock ResourceManager
    mock_rm = MockResourceManager()
    # Correct registration: instance, then type
    world.services.register(mock_rm, ResourceManager, replace=True)

    # Create entity with Sprite, AIState, and YukkuriStats
    entity = world.create_entity()
    world.add_component(entity, Sprite(image_name="base_image.png", width=32, height=32))
    world.add_component(entity, AIState(current_action="Idle"))
    world.add_component(entity, YukkuriStats(name="Test", type_id="test_type"))

    system = AnimationSystem()
    world.add_system(system)

    # Case 1: Idle state (default) -> No change
    system.update(world, 0.1)
    sprite = world.get_component(entity, Sprite)
    assert sprite.image_name == "base_image.png"

    # Case 2: Change action to "Sleeping"
    ai_state = world.get_component(entity, AIState)
    ai_state.current_action = "Sleeping"

    system.update(world, 0.1)
    assert sprite.image_name == "base_image_sleeping.png"

    # Case 3: Change action back to "Idle"
    ai_state.current_action = "Idle"
    system.update(world, 0.1)
    assert sprite.image_name == "base_image.png"

    # Case 4: Unknown action -> Should fallback to constructed name (ResourceManager handles missing file)
    ai_state.current_action = "UnknownAction"
    system.update(world, 0.1)
    assert sprite.image_name == "base_image_unknownaction.png"


def test_animator_precedence():
    """
    Test that if an Animator is present, it takes precedence (existing logic).
    """
    from test_utils import make_configured_world
    world = make_configured_world()
    mock_rm = MockResourceManager()
    world.services.register(mock_rm, ResourceManager, replace=True)

    # Create entity with Sprite, AIState, YukkuriStats AND Animator
    entity = world.create_entity()
    world.add_component(entity, Sprite(image_name="base_image.png", width=32, height=32))
    world.add_component(entity, AIState(current_action="Sleeping"))
    world.add_component(entity, YukkuriStats(name="Test", type_id="test_type"))
    world.add_component(entity, Animator(animations={}))

    system = AnimationSystem()
    world.add_system(system)

    # Even if we update, the new logic should check for Animator presence and skip.
    # So sprite.image_name should REMAIN "base_image.png" (or whatever Animator sets it to, here nothing).

    system.update(world, 0.1)
    sprite = world.get_component(entity, Sprite)

    assert sprite.image_name == "base_image.png"
