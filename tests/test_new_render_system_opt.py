import pygame
import sys
from unittest.mock import MagicMock

# Mock pygame_light2d before importing systems
sys.modules["pygame_light2d"] = MagicMock()
sys.modules["pygame_light2d.engine"] = MagicMock()
sys.modules["moderngl"] = MagicMock()
sys.modules["pygame_light2d"].Hull.side_effect = lambda *args, **kwargs: MagicMock()

from src.yukkuri_game.game.systems.render_system_new import NewRenderSystem
from src.yukkuri_game.game.components import Transform, Occluder
from src.yukkuri_game.engine.ecs import World
from src.yukkuri_game.engine.resource_manager import ResourceManager
from src.yukkuri_game.game.camera import Camera


def test_occluder_optimization():
    pygame.init()
    screen = pygame.Surface((800, 600))
    world = World()

    # Mock services
    rm = MagicMock(spec=ResourceManager)
    world.services.register(rm, ResourceManager)
    camera = Camera()
    world.services.register(camera, Camera)

    # Mock LightingEngine
    lights_engine = MagicMock()
    lights_engine.hulls = []  # List
    lights_engine._native_res = (800, 600)

    system = NewRenderSystem(screen, world, lights_engine=lights_engine)
    backend = system.renderer.backend

    # Add entity with Occluder
    ent = world.create_entity()
    world.add_component(ent, Transform(x=100, y=100))
    world.add_component(ent, Occluder(polygon=[(-10, -10), (10, 10), (10, -10)]))

    # Update frame 1
    system.update(world, 1.0)

    # Verify hull created in active_hulls
    assert ent in backend.active_hulls
    hull = backend.active_hulls[ent]

    # Verify engine.hulls list contains the hull (end_frame logic)
    # The slice assignment backend.engine.hulls[:] = ... modifies the list in place.
    # MagicMock list behavior might not be exact for slice assignment unless we check.
    # But since I mocked lights_engine.hulls = [], it is a real list.
    assert hull in lights_engine.hulls

    # Update frame 2 (same entity)
    # Mock hull creation to see if it's replaced (optimization: we recreate hull obj every frame currently)
    # But wait, backend.active_hulls should be updated.

    prev_hull = hull
    system.update(world, 1.0)

    new_hull = backend.active_hulls[ent]
    assert new_hull is not prev_hull  # Current logic recreates it
    assert new_hull in lights_engine.hulls
    assert prev_hull not in lights_engine.hulls  # Should be replaced

    # Remove entity
    world.destroy_entity(ent)

    # Update frame 3
    system.update(world, 1.0)

    # Verify removed
    assert ent not in backend.active_hulls
    assert len(lights_engine.hulls) == 0


if __name__ == "__main__":
    test_occluder_optimization()
    print("Optimization test passed!")
