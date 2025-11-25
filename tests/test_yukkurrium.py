import pytest
import pygame
from unittest.mock import MagicMock, patch
from yukkuri_game.game.yukkurrium import Yukkurrium, RenderSystem, TimeSystem
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.components import Transform, Sprite, Selectable, PhysicsBody, VisualTransform

@pytest.fixture
def yukkurrium():
    pygame.init()
    from yukkuri_game.config import WorldSettings
    settings = WorldSettings(width=1000, height=1000)
    return Yukkurrium(settings)

def test_coordinate_conversion(yukkurrium):
    screen_w, screen_h = 800, 600

    # Center of world (0,0) should be center of screen when camera is at (0,0)
    sx, sy = yukkurrium.world_to_screen(0, 0, screen_w, screen_h)
    assert sx == 400
    assert sy == 300

    # Reverse
    wx, wy = yukkurrium.screen_to_world(400, 300, screen_w, screen_h)
    assert wx == 0
    assert wy == 0

    # With camera offset
    yukkurrium.camera_x = 100
    yukkurrium.camera_y = 50

    # (100, 50) in world should now be center of screen
    sx, sy = yukkurrium.world_to_screen(100, 50, screen_w, screen_h)
    assert sx == 400
    assert sy == 300

    # With zoom
    yukkurrium.camera_x = 0
    yukkurrium.camera_y = 0
    yukkurrium.zoom = 2.0

    # (50, 50) world -> (50*2 + 400, 50*2 + 300) = (500, 400)
    sx, sy = yukkurrium.world_to_screen(50, 50, screen_w, screen_h)
    assert sx == 500
    assert sy == 400

def test_handle_input_zoom(yukkurrium):
    # Mock mouse wheel event
    event = MagicMock()
    event.type = pygame.MOUSEWHEEL
    event.y = 1 # Scroll up (zoom in)

    initial_zoom = yukkurrium.target_zoom
    yukkurrium.handle_input(event, 800, 600)

    assert yukkurrium.target_zoom > initial_zoom
    assert yukkurrium.target_zoom <= yukkurrium.max_zoom

    # Test max zoom
    yukkurrium.target_zoom = yukkurrium.max_zoom
    yukkurrium.handle_input(event, 800, 600)
    assert yukkurrium.target_zoom == yukkurrium.max_zoom

def test_handle_input_pan(yukkurrium):
    # Mock mouse motion event with middle click
    event = MagicMock()
    event.type = pygame.MOUSEMOTION
    event.rel = (10, 20)

    with patch('pygame.mouse.get_pressed', return_value=(0, 1, 0)): # Middle click
        initial_cam_x = yukkurrium.camera_x
        initial_cam_y = yukkurrium.camera_y

        yukkurrium.handle_input(event, 800, 600)

        # Camera moves opposite to drag
        assert yukkurrium.camera_x == initial_cam_x - 10
        assert yukkurrium.camera_y == initial_cam_y - 20

def test_handle_input_other(yukkurrium):
    # Test other events are ignored
    event = MagicMock()
    event.type = pygame.KEYDOWN

    initial_zoom = yukkurrium.target_zoom
    initial_cam_x = yukkurrium.camera_x

    yukkurrium.handle_input(event, 800, 600)

    assert yukkurrium.target_zoom == initial_zoom
    assert yukkurrium.camera_x == initial_cam_x

def test_update_zoom_smoothing(yukkurrium):
    yukkurrium.zoom = 1.0
    yukkurrium.target_zoom = 2.0

    dt = 0.1
    yukkurrium.update(dt)

    # Zoom should approach target
    assert yukkurrium.zoom > 1.0
    assert yukkurrium.zoom < 2.0

def test_render_system_update():
    screen = MagicMock()
    screen.get_size.return_value = (800, 600)
    # Mock screen rect for culling check
    screen_rect = MagicMock()
    screen.get_rect.return_value = screen_rect
    # Make colliderect return True so we draw

    yukkurrium = Yukkurrium()
    rm = MagicMock()

    # Mock image
    img = MagicMock()
    img.get_rect.return_value = MagicMock()
    # Simulate colliderect
    img.get_rect.return_value.colliderect.return_value = True
    img.get_size.return_value = (32, 32)

    rm.load_image.return_value = img

    # RenderSystem takes screen and world, fetches yukkurrium and rm from world services
    world = MagicMock()
    # Mock services.get behavior for multiple types
    from yukkuri_game.engine.resource_manager import ResourceManager

    def get_service(service_type):
        if service_type == Yukkurrium:
            return yukkurrium
        if service_type == ResourceManager:
            return rm
        return None

    world.services.get.side_effect = get_service

    rs = RenderSystem(screen, world)

    # Setup entity
    ent = 1
    world.get_entities_with.return_value = [ent]

    transform = Transform(x=0, y=0)
    sprite = Sprite(image_name="test.png", width=32, height=32)
    phys_body = PhysicsBody(body=MagicMock(), shape=MagicMock())
    visual_transform = VisualTransform()

    def get_component_side_effect(e, c):
        if c == Transform:
            return transform
        if c == Sprite:
            return sprite
        if c == Selectable:
            return None
        if c == PhysicsBody:
            return phys_body
        if c == VisualTransform:
            return visual_transform
        return None

    world.get_component.side_effect = get_component_side_effect

    with patch('pygame.draw.line'), patch('pygame.draw.rect'):
        rs.update(world, 0.016)

        # Verify grid drawing (lines)
        assert pygame.draw.line.called

    # Verify image loading and blitting
    rm.load_image.assert_called_with("test.png")
    screen.blit.assert_called()

def test_render_system_update_scaling_and_culling():
    screen = MagicMock()
    screen.get_size.return_value = (800, 600)
    screen_rect = MagicMock()
    screen.get_rect.return_value = screen_rect

    yukkurrium = Yukkurrium()
    # Zoom in to trigger scaling code
    yukkurrium.zoom = 2.0

    rm = MagicMock()
    img = MagicMock()
    # Mock scaling
    scaled_img = MagicMock()

    # Culling: rect.colliderect(screen.get_rect()) -> False means culled
    # We want to test:
    # 1. Scaling (when scale != 1.0)
    # 2. Culling (when colliderect returns False)
    # 3. Selection highlight

    # Set up image rect
    rect = MagicMock()
    # Let's say it collides
    rect.colliderect.return_value = True
    scaled_img.get_rect.return_value = rect
    img.get_size.return_value = (32, 32)
    scaled_img.get_size.return_value = (64, 64)

    # Mock pygame.transform.scale
    with patch('pygame.transform.scale', return_value=scaled_img) as mock_scale:
        rm.load_image.return_value = img

        world = MagicMock()
        from yukkuri_game.engine.resource_manager import ResourceManager

        def get_service(service_type):
            if service_type == Yukkurrium:
                return yukkurrium
            if service_type == ResourceManager:
                return rm
            return None

        world.services.get.side_effect = get_service

        rs = RenderSystem(screen, world)

        ent = 1
        world.get_entities_with.return_value = [ent]

        transform = Transform(x=0, y=0, scale=1.0) # Scale 1.0 * Zoom 2.0 = 2.0 effective scale
        sprite = Sprite(image_name="test.png", width=32, height=32)
        selectable = Selectable(selected=True)
        phys_body = PhysicsBody(body=MagicMock(), shape=MagicMock())
        visual_transform = VisualTransform()

        def get_component_side_effect(e, c):
            if c == Transform:
                return transform
            if c == Sprite:
                return sprite
            if c == Selectable:
                return selectable
            if c == PhysicsBody:
                return phys_body
            if c == VisualTransform:
                return visual_transform
            return None

        world.get_component.side_effect = get_component_side_effect

        with patch('pygame.draw.line'), patch('pygame.draw.rect') as mock_rect:
            rs.update(world, 0.016)

            # Verify scaling
            mock_scale.assert_called()

            # Verify selection highlight
            mock_rect.assert_called()

def test_render_system_update_culling():
    screen = MagicMock()
    screen.get_size.return_value = (800, 600)
    screen_rect = MagicMock()
    screen.get_rect.return_value = screen_rect

    yukkurrium = Yukkurrium()
    rm = MagicMock()
    img = MagicMock()
    rect = MagicMock()
    # Not colliding -> Culled
    rect.colliderect.return_value = False

    # img.subsurface() returns a mock, we need that mock's get_rect to return our rect
    subsurface = MagicMock()
    subsurface.get_rect.return_value = rect
    img.subsurface.return_value = subsurface
    # Also if no subsurface is done (optimization), it uses img directly
    img.get_rect.return_value = rect
    img.get_size.return_value = (32, 32)
    subsurface.get_size.return_value = (32, 32)

    rm.load_image.return_value = img

    world = MagicMock()
    from yukkuri_game.engine.resource_manager import ResourceManager

    def get_service(service_type):
        if service_type == Yukkurrium:
            return yukkurrium
        if service_type == ResourceManager:
            return rm
        return None

    world.services.get.side_effect = get_service

    rs = RenderSystem(screen, world)

    ent = 1
    world.get_entities_with.return_value = [ent]

    transform = Transform(x=10000, y=10000)
    sprite = Sprite(image_name="test.png", width=32, height=32)
    phys_body = PhysicsBody(body=MagicMock(), shape=MagicMock())
    visual_transform = VisualTransform()

    world.get_component.side_effect = lambda e, c: transform if c == Transform else (sprite if c == Sprite else (phys_body if c == PhysicsBody else (visual_transform if c == VisualTransform else None)))

    with patch('pygame.draw.line'), patch('pygame.draw.rect'):
        rs.update(world, 0.016)

        # Should not blit if culled
        screen.blit.assert_not_called()

def test_render_system_update_invalid_size():
    screen = MagicMock()
    screen.get_size.return_value = (800, 600)
    yukkurrium = Yukkurrium()
    yukkurrium.zoom = 0.001 # Very small zoom

    rm = MagicMock()
    img = MagicMock()
    img.get_size.return_value = (32, 32)
    rm.load_image.return_value = img

    world = MagicMock()
    from yukkuri_game.engine.resource_manager import ResourceManager

    def get_service(service_type):
        if service_type == Yukkurrium:
            return yukkurrium
        if service_type == ResourceManager:
            return rm
        return None

    world.services.get.side_effect = get_service

    rs = RenderSystem(screen, world)

    ent = 1
    world.get_entities_with.return_value = [ent]

    transform = Transform(x=0, y=0, scale=0.1) # Resulting size will be ~0
    sprite = Sprite(image_name="test.png", width=32, height=32)
    phys_body = PhysicsBody(body=MagicMock(), shape=MagicMock())
    visual_transform = VisualTransform()

    world.get_component.side_effect = lambda e, c: transform if c == Transform else (sprite if c == Sprite else (phys_body if c == PhysicsBody else (visual_transform if c == VisualTransform else None)))

    with patch('pygame.draw.line'), patch('pygame.draw.rect'):
        rs.update(world, 0.016)

        # Should not blit if size <= 0
        screen.blit.assert_not_called()

def test_render_system_missing_components():
    screen = MagicMock()
    screen.get_size.return_value = (800, 600)
    yukkurrium = Yukkurrium()
    rm = MagicMock()

    world = MagicMock()
    from yukkuri_game.engine.resource_manager import ResourceManager

    def get_service(service_type):
        if service_type == Yukkurrium:
            return yukkurrium
        if service_type == ResourceManager:
            return rm
        return None

    world.services.get.side_effect = get_service

    rs = RenderSystem(screen, world)

    # Entity is in the list but somehow get_component returns None (race condition or error)
    ent = 1
    world.get_entities_with.return_value = [ent]

    # get_component needs to return valid Transform for sort, but None for the loop check
    transform = Transform(x=0, y=0)

    def get_component_side_effect(e, c):
        # The sort calls get_component(e, Transform)
        # The loop also calls get_component(e, Transform) and get_component(e, Sprite)
        # We want the sort to succeed, but the loop check to fail.
        if c == Transform:
            return transform
        if c == Sprite:
            return None
        if c == PhysicsBody:
            return PhysicsBody(body=MagicMock(), shape=MagicMock())
        if c == VisualTransform:
            return VisualTransform()
        return None

    world.get_component.side_effect = get_component_side_effect

    with patch('pygame.draw.line'), patch('pygame.draw.rect'):
        rs.update(world, 0.016)

        # Should continue and not crash or do anything
        rm.load_image.assert_not_called()

def test_time_system():
    ts = TimeSystem()
    world = MagicMock()

    assert ts.total_time == 0.0

    ts.update(world, 1.0)
    assert ts.total_time == 1.0

    ts.game_speed = 2.0
    ts.update(world, 1.0)
    assert ts.total_time == 3.0
