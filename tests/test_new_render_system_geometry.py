import pygame
import sys
from unittest.mock import MagicMock

# Mock pygame_light2d before importing systems
sys.modules["pygame_light2d"] = MagicMock()
sys.modules["pygame_light2d.engine"] = MagicMock()
sys.modules["moderngl"] = MagicMock()

from src.yukkuri_game.game.systems.render_system_new import NewRenderSystem
from src.yukkuri_game.game.renderer_new.commands import OccluderCommand
from src.yukkuri_game.game.components import Transform, Occluder
from src.yukkuri_game.engine.ecs import World
from src.yukkuri_game.engine.resource_manager import ResourceManager
from src.yukkuri_game.game.camera import Camera
from src.yukkuri_game.game.renderer_new.light2d_backend import Light2DBackend


def test_occluder_geometry_generation():
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
    lights_engine._get_layer.return_value = MagicMock()
    lights_engine.graphics = MagicMock()
    # Set _native_res to screen size for test
    lights_engine._native_res = (800, 600)

    system = NewRenderSystem(screen, world, lights_engine=lights_engine)

    # Ensure backend is Light2DBackend
    assert isinstance(system.renderer.backend, Light2DBackend)

    # Create entity
    ent = world.create_entity()
    world.add_component(ent, Transform(x=100, y=100))
    world.add_component(
        ent, Occluder(polygon=[(-10, -10), (10, -10), (10, 10), (-10, 10)])
    )

    # Mock draw_occluder to verify calls
    system.renderer.backend.draw_occluder = MagicMock()

    # Run update
    system.update(world, 1.0)

    # Verify
    assert system.renderer.backend.draw_occluder.called
    args = system.renderer.backend.draw_occluder.call_args[0][0]
    assert isinstance(args, OccluderCommand)

    # Verify vertices
    assert len(args.vertices) == 4
    # Expected screen coords:
    # Center 400,300.
    # Entity at 100,100 world.
    # Screen pos = (100-0) + 400 = 500, (100-0) + 300 = 400.
    # Box +/- 10.
    vx, vy = args.vertices[0]
    assert 485 <= vx <= 515  # Allow some float precision/rounding
    assert 385 <= vy <= 415


if __name__ == "__main__":
    test_occluder_geometry_generation()
    print("Geometry test passed!")
