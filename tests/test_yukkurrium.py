import pytest
from unittest.mock import MagicMock, patch
import pygame
from yukkuri_game.game.yukkurrium import Yukkurrium, RenderSystem, TimeSystem
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.components import Transform, Sprite, Selectable
from yukkuri_game.engine.resource_manager import ResourceManager

@pytest.fixture
def mock_world():
    world = MagicMock(spec=World)
    world.services = MagicMock()
    return world

def test_yukkurrium_init():
    y = Yukkurrium(1000, 800)
    assert y.width == 1000
    assert y.height == 800
    assert y.zoom == 1.0
    assert y.camera_x == 0.0
    assert y.camera_y == 0.0

def test_coordinate_conversion():
    y = Yukkurrium(2000, 2000)
    # Center screen is (400, 300) for 800x600
    # Center world is (0, 0)

    # With default camera (0,0) and zoom 1
    sx, sy = y.world_to_screen(0, 0, 800, 600)
    assert sx == 400
    assert sy == 300

    wx, wy = y.screen_to_world(400, 300, 800, 600)
    assert wx == 0
    assert wy == 0

    # Test Pan
    y.camera_x = 100
    sx, sy = y.world_to_screen(100, 0, 800, 600)
    # World (100, 0) should now be at center (400, 300)
    assert sx == 400
    assert sy == 300

    # Test Zoom
    y.camera_x = 0
    y.zoom = 2.0
    # World 0,0 is center. World 10,0.
    # Distance 10 world units = 20 screen units
    sx, sy = y.world_to_screen(10, 0, 800, 600)
    assert sx == 420

def test_input_handling():
    y = Yukkurrium()

    # Test Zoom
    event = MagicMock()
    event.type = pygame.MOUSEWHEEL
    event.y = 1 # Scroll up

    initial_target = y.target_zoom
    y.handle_input(event, 800, 600)
    assert y.target_zoom > initial_target

    # Test Pan (needs mouse state mock)
    event = MagicMock()
    event.type = pygame.MOUSEMOTION
    event.rel = (-10, -10) # Dragged left-up

    with patch('pygame.mouse.get_pressed', return_value=(0, 1, 0)): # Middle click
        y.handle_input(event, 800, 600)
        # Camera should move right-down (opposite to drag) to show "left-up" content?
        # Dragging mouse left (-x) moves the world view right (+x)?
        # Code: camera_x -= dx / zoom
        # dx = -10 -> camera_x -= -10 -> camera_x += 10.
        # So camera moves to +10.
        assert y.camera_x > 0
        assert y.camera_y > 0

def test_update_smooth_zoom():
    y = Yukkurrium()
    y.zoom = 1.0
    y.target_zoom = 2.0

    y.update(0.1)

    # Should approach target
    assert y.zoom > 1.0
    assert y.zoom < 2.0

def test_render_system_update(mock_world):
    # Use Mock for screen
    screen = MagicMock()
    screen.get_size.return_value = (800, 600)
    # Ensure screen.get_rect returns a rect that collides
    screen.get_rect.return_value.colliderect.return_value = True

    yukkurrium = Yukkurrium()
    rm = MagicMock()

    # Setup services
    mock_world.services.get.side_effect = lambda service_type: yukkurrium if service_type == Yukkurrium else (rm if service_type == ResourceManager else MagicMock())

    # Mock image (Surface)
    img = MagicMock() # Can be mock if we patch blit/transform
    img.get_rect.return_value = MagicMock()
    img.get_rect.return_value.colliderect.return_value = True

    rm.load_image.return_value = img

    rs = RenderSystem(screen, mock_world)

    # Setup entities
    mock_world.get_entities_with.return_value = [1]

    trans = Transform(x=0, y=0)
    sprite = Sprite(image_name="test.png", width=32, height=32)

    def get_component_side_effect(ent, comp_type):
        if comp_type == Transform:
            return trans
        if comp_type == Sprite:
            return sprite
        return None

    mock_world.get_component.side_effect = get_component_side_effect

    # Patch pygame functions to avoid type checking real surface
    with patch('pygame.draw.line'), patch('pygame.draw.rect'), patch('pygame.transform.scale', return_value=img):
         rs.update(mock_world, 0.016)

         screen.blit.assert_called()

def test_render_system_update_scaling_and_culling(mock_world):
    screen = MagicMock()
    screen.get_size.return_value = (800, 600)
    screen.get_rect.return_value.colliderect.return_value = True

    yukkurrium = Yukkurrium()
    # Zoom in to trigger scaling code
    yukkurrium.zoom = 2.0

    rm = MagicMock()
    img = MagicMock()
    img.get_rect.return_value = MagicMock()
    img.get_rect.return_value.colliderect.return_value = True

    # Setup services
    mock_world.services.get.side_effect = lambda service_type: yukkurrium if service_type == Yukkurrium else (rm if service_type == ResourceManager else MagicMock())

    rm.load_image.return_value = img

    rs = RenderSystem(screen, mock_world)

    mock_world.get_entities_with.return_value = [1]
    trans = Transform(x=0, y=0) # Scale 1.0
    sprite = Sprite("test.png", 32, 32)
    selectable = Selectable(selected=True)

    def get_component_side_effect(ent, comp_type):
        if comp_type == Transform:
            return trans
        if comp_type == Sprite:
            return sprite
        if comp_type == Selectable:
            return selectable
        return None
    mock_world.get_component.side_effect = get_component_side_effect

    with patch('pygame.draw.line'), patch('pygame.draw.rect'), patch('pygame.transform.scale', return_value=img) as mock_scale:
        rs.update(mock_world, 0.016)

        # Verify scaling
        # Zoom is 2.0, trans.scale is 1.0 -> total scale 2.0
        # width 32 * 2 = 64
        mock_scale.assert_called_with(img, (64, 64))

        # Verify blit
        screen.blit.assert_called_with(img, img.get_rect(center=(400,300)))

def test_render_system_update_culling(mock_world):
    screen = MagicMock()
    screen.get_size.return_value = (800, 600)

    yukkurrium = Yukkurrium()
    rm = MagicMock()
    img = MagicMock()
    rect = MagicMock()
    # Not colliding -> Culled
    rect.colliderect.return_value = False
    img.get_rect.return_value = rect
    rm.load_image.return_value = img

    mock_world.services.get.side_effect = lambda service_type: yukkurrium if service_type == Yukkurrium else (rm if service_type == ResourceManager else MagicMock())

    rs = RenderSystem(screen, mock_world)

    mock_world.get_entities_with.return_value = [1]
    trans = Transform(10000, 10000)
    sprite = Sprite("t", 32, 32)
    mock_world.get_component.side_effect = lambda e, c: trans if c==Transform else sprite

    with patch('pygame.draw.line'), patch('pygame.draw.rect'):
        rs.update(mock_world, 0.016)

        screen.blit.assert_not_called()

def test_render_system_update_invalid_size(mock_world):
    screen = MagicMock()
    screen.get_size.return_value = (800, 600)
    yukkurrium = Yukkurrium()
    yukkurrium.zoom = 0.001 # Very small zoom

    rm = MagicMock()
    img = MagicMock()
    rm.load_image.return_value = img

    mock_world.services.get.side_effect = lambda service_type: yukkurrium if service_type == Yukkurrium else (rm if service_type == ResourceManager else MagicMock())

    rs = RenderSystem(screen, mock_world)

    mock_world.get_entities_with.return_value = [1]
    mock_world.get_component.side_effect = lambda e, c: Transform(0,0) if c==Transform else Sprite("t",32,32)

    with patch('pygame.draw.line'), patch('pygame.draw.rect'):
        rs.update(mock_world, 0.016)

        screen.blit.assert_not_called()

def test_render_system_missing_components(mock_world):
    screen = MagicMock()
    screen.get_size.return_value = (800, 600)
    yukkurrium = Yukkurrium()
    rm = MagicMock()

    mock_world.services.get.side_effect = lambda service_type: yukkurrium if service_type == Yukkurrium else (rm if service_type == ResourceManager else MagicMock())

    rs = RenderSystem(screen, mock_world)

    mock_world.get_entities_with.return_value = [1]

    # To avoid crash in sort, we provide Transform but skip Sprite
    trans = Transform(x=0, y=0)

    def get_component_side_effect(ent, comp_type):
        if comp_type == Transform:
            return trans
        return None # No Sprite

    mock_world.get_component.side_effect = get_component_side_effect

    with patch('pygame.draw.line'), patch('pygame.draw.rect'):
        rs.update(mock_world, 0.016)

        screen.blit.assert_not_called()

def test_time_system():
    ts = TimeSystem()
    assert ts.total_time == 0.0

    ts.update(MagicMock(), 1.0)
    assert ts.total_time == 1.0

    ts.game_speed = 2.0
    ts.update(MagicMock(), 1.0)
    assert ts.total_time == 3.0
