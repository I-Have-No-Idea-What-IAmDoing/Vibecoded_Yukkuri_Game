
import pygame
from unittest.mock import MagicMock, ANY
from src.yukkuri_game.game.systems.render_system import RenderSystem
from src.yukkuri_game.game.components import Transform, Sprite, VisualTransform
from src.yukkuri_game.game.camera import Camera
from src.yukkuri_game.engine.ecs import World
from src.yukkuri_game.engine.resource_manager import ResourceManager
from src.yukkuri_game.game.surface_cache import SurfaceCache

def test_render_system_quantizes_scale():
    pygame.init()
    screen = pygame.Surface((800, 600))
    
    # Setup World and Services
    world = World()
    rm = MagicMock(spec=ResourceManager)
    camera = Camera()
    
    world.services.register(rm, service_type=ResourceManager)
    world.services.register(camera, service_type=Camera)
    
    # Initialize RenderSystem
    render_system = RenderSystem(screen, world)
    
    # Mock SurfaceCache to spy on calls
    render_system.surface_cache = MagicMock(spec=SurfaceCache)
    render_system.surface_cache.get_surface.return_value = pygame.Surface((32, 32))
    
    # Create an entity
    entity = world.create_entity()
    world.add_component(entity, Transform(x=100, y=100, scale=1.0))
    world.add_component(entity, Sprite(image_name="test_img", width=32, height=32))
    world.add_component(entity, VisualTransform())
    
    # 1. Test Scale at Zoom 1.0
    camera.zoom = 1.0
    render_system.update(world, 1.0)
    
    # Verify call args
    try:
        render_system.surface_cache.get_surface.assert_called_with(
            "test_img", 0, 1, 32, 32, 1.0, 0.0, False, False
        )
    except AssertionError as e:
        print(f"Assertion failed for Zoom 1.0. Actual calls: {render_system.surface_cache.get_surface.call_args_list}")
        raise e
    
    render_system.surface_cache.reset_mock()

    # 2. Test Scale at Zoom 1.001 (Micro-zoom)
    camera.zoom = 1.001
    render_system.update(world, 1.0)
    
    try:
        render_system.surface_cache.get_surface.assert_called_with(
            "test_img", 0, 1, 32, 32, 1.0, 0.0, False, False
        )
    except AssertionError as e:
        print(f"Assertion failed for Zoom 1.001. Actual calls: {render_system.surface_cache.get_surface.call_args_list}")
        raise e
    
    render_system.surface_cache.reset_mock()

    # 3. Test Scale at Zoom 1.06 (Should step up)
    camera.zoom = 1.06
    render_system.update(world, 1.0)
    
    try:
        render_system.surface_cache.get_surface.assert_called_with(
            "test_img", 0, 1, 32, 32, 1.05, 0.0, False, False
        )
    except AssertionError as e:
        print(f"Assertion failed for Zoom 1.06. Actual calls: {render_system.surface_cache.get_surface.call_args_list}")
        raise e

if __name__ == "__main__":
    test_render_system_quantizes_scale()
    print("Test passed!")
