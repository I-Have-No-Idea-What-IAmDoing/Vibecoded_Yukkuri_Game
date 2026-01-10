
import pymunk
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.systems.render_system import RenderSystem
from yukkuri_game.game.services import TimeService
from yukkuri_game.game.camera import Camera
from yukkuri_game.game.renderer.renderer import Renderer
from yukkuri_game.game.renderer.commands import ShadowCommand
from yukkuri_game.game.components import (
    Transform,
    Sprite,
    VisualTransform,
)
from unittest.mock import MagicMock

from unittest.mock import MagicMock, patch

@patch('yukkuri_game.game.systems.render_system.PygameBackend')
def test_render_system_shadow_offset(mock_backend_cls):
    """
    Test that the shadow position is offset by half the sprite height.
    """
    # Setup mocks
    screen = MagicMock()
    screen.get_size.return_value = (800, 600)
    
    world = World()
    
    # Needs ResourceManager and Camera services
    # Register mocked ResourceManager
    from yukkuri_game.engine.resource_manager import ResourceManager
    rm = MagicMock()
    world.services.register(rm, ResourceManager)

    # Mock WorldSettings
    settings = MagicMock()
    settings.width = 800
    settings.height = 600
    camera = Camera(settings)
    world.services.register(camera, Camera)
    
    # Create RenderSystem
    # This will use the mocked PygameBackend
    render_system = RenderSystem(screen, world)
    
    # Mock Renderer to capture commands
    # (RenderSystem creates a real Renderer with the mock backend, but we can replace it or inspect it)
    # We want to check what is submitted to the renderer.
    render_system.renderer = MagicMock()
    
    # Create Entity
    entity = world.create_entity()
    
    transform = Transform(x=100, y=100)
    sprite = Sprite(image_name="test", width=64, height=64)
    visual = VisualTransform() # shadow_pos is (0,0)
    
    world.add_component(entity, transform)
    world.add_component(entity, sprite)
    world.add_component(entity, visual)
    
    # Initialize camera matrices
    camera.update_matrices(800, 600)
    
    # Run process_entity logic
    # We can call _process_entity directly to avoid setup overhead
    render_system._process_entity(world, entity, 1.0, 800, 600)
    
    # Check submitted commands
    assert render_system.renderer.submit.called
    
    # Find ShadowCommand
    shadow_cmd = None
    for call in render_system.renderer.submit.call_args_list:
        cmd = call[0][0]
        if isinstance(cmd, ShadowCommand):
            shadow_cmd = cmd
            break
            
    assert shadow_cmd is not None
    
    # Verify Position
    # Entity at 100, 100.
    # Sprite height 64. Scale 1.
    # Offset = 64 * 1 * 0.5 = 32.
    # Expected World Y = 100 + 32 = 132.
    # Screen Y should be calculated via camera.
    
    expected_x, expected_y = camera.world_to_screen_fast(100, 132)
    
    assert shadow_cmd.position[0] == expected_x
    assert shadow_cmd.position[1] == expected_y

