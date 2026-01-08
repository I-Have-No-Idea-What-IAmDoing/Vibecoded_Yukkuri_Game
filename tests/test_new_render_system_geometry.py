import pygame
import sys
from unittest.mock import MagicMock

# Mock pygame_light2d before importing systems
sys.modules["pygame_light2d"] = MagicMock()
sys.modules["pygame_light2d.engine"] = MagicMock()
sys.modules["moderngl"] = MagicMock()

from src.yukkuri_game.game.systems.render_system_new import NewRenderSystem
from src.yukkuri_game.game.renderer_new.native_light_backend import NativeLightBackend
from src.yukkuri_game.game.components import Transform, Occluder, Sprite, PhysicsBody
from src.yukkuri_game.engine.ecs import World
from src.yukkuri_game.engine.resource_manager import ResourceManager
from src.yukkuri_game.game.camera import Camera


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

    # Ensure backend is NativeLightBackend (updated from Light2DBackend)
    assert isinstance(system.renderer.backend, NativeLightBackend)
    backend = system.renderer.backend

    # Add entity with Occluder
    ent = world.create_entity()
    world.add_component(ent, Transform(x=100, y=100))
    world.add_component(ent, Occluder(polygon=[(-10, -10), (10, 10), (10, -10)]))
    # Add dummy Sprite/PhysicsBody if needed by logic

    # Update frame
    system.update(world, 1.0)

    # Verify occluder was submitted to backend
    # NativeLightBackend stores occluders in self.occluders list
    # Each item is (aabb, vertices, entity_id, static)
    assert len(backend.occluders) == 1

    aabb, vertices, eid, static = backend.occluders[0]
    # Vertices should be transformed to screen space
    # Camera at (0,0) (default), scale 1. Entity at (100, 100).
    # Occluder local points + entity pos

    # Check bounds
    assert len(vertices) == 3

if __name__ == "__main__":
    test_occluder_geometry_generation()
    print("Geometry test passed!")
