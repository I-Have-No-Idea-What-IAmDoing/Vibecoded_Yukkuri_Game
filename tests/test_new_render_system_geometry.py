import pygame
import sys
from unittest.mock import MagicMock

# Mock pygame_light2d before importing systems
sys.modules["pygame_light2d"] = MagicMock()
sys.modules["pygame_light2d.engine"] = MagicMock()
sys.modules["moderngl"] = MagicMock()  # noqa: E402

from src.yukkuri_game.game.systems.render_system import RenderSystem  # noqa: E402
from src.yukkuri_game.game.renderer.opengl_backend import OpenGLBackend  # noqa: E402
from src.yukkuri_game.game.components import Transform, Occluder  # noqa: E402
from src.yukkuri_game.engine.ecs import World  # noqa: E402
from src.yukkuri_game.engine.resource_manager import ResourceManager  # noqa: E402
from src.yukkuri_game.game.camera import Camera  # noqa: E402


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

    system = RenderSystem(screen, world, lights_engine=lights_engine)

    # Mock Hull constructor to store vertices
    def mock_hull_init(vertices):
        m = MagicMock()
        m.vertices = vertices
        return m

    import pygame_light2d

    pygame_light2d.Hull.side_effect = mock_hull_init

    # Ensure backend is OpenGLBackend
    assert isinstance(system.renderer.backend, OpenGLBackend)
    backend = system.renderer.backend

    # Add entity with Occluder
    ent = world.create_entity()
    world.add_component(ent, Transform(x=100, y=100))
    world.add_component(ent, Occluder(polygon=[(-10, -10), (10, 10), (10, -10)]))
    # Add dummy Sprite/PhysicsBody if needed by logic

    # Update frame
    system.update(world, 1.0)

    # Verify occluder was submitted to backend
    # OpenGLBackend stores hulls in active_hulls
    assert len(backend.active_hulls) == 1

    hull = backend.active_hulls[ent]
    vertices = hull.vertices
    # Vertices should be transformed to screen space
    # Camera at (0,0) (default), scale 1. Entity at (100, 100).
    # Occluder local points + entity pos

    # Check bounds
    assert len(vertices) == 3


if __name__ == "__main__":
    test_occluder_geometry_generation()
    print("Geometry test passed!")
