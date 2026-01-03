from unittest.mock import MagicMock, Mock, patch

import pygame
import pytest

from yukkuri_game.engine.ecs import World
from yukkuri_game.game.camera import Camera
from yukkuri_game.game.components import (
    PhysicsBody,
    Selectable,
    Sprite,
    Transform,
    VisualTransform,
)
from yukkuri_game.game.renderer import WorldRenderer
from yukkuri_game.game.systems.render_system import RenderSystem
from yukkuri_game.game.systems.time_system import TimeSystem


@pytest.fixture
def camera():
    pygame.init()
    from yukkuri_game.config import WorldSettings

    settings = WorldSettings(width=1000, height=1000)
    return Camera(settings)


def test_coordinate_conversion(camera):
    screen_w, screen_h = 800, 600

    # Center of world (0,0) should be center of screen when camera is at (0,0)
    sx, sy = camera.world_to_screen(0, 0, screen_w, screen_h)
    assert sx == 400
    assert sy == 300

    # Reverse
    wx, wy = camera.screen_to_world(400, 300, screen_w, screen_h)
    assert wx == 0
    assert wy == 0

    # With camera offset
    camera.camera_x = 100
    camera.camera_y = 50

    # (100, 50) in world should now be center of screen
    sx, sy = camera.world_to_screen(100, 50, screen_w, screen_h)
    assert sx == 400
    assert sy == 300

    # With zoom
    camera.camera_x = 0
    camera.camera_y = 0
    camera.zoom = 2.0

    # (50, 50) world -> (50*2 + 400, 50*2 + 300) = (500, 400)
    sx, sy = camera.world_to_screen(50, 50, screen_w, screen_h)
    assert sx == 500
    assert sy == 400


def test_handle_input_zoom(camera):
    # Mock mouse wheel event
    event = MagicMock()
    event.type = pygame.MOUSEWHEEL
    event.y = 1  # Scroll up (zoom in)

    initial_zoom = camera.target_zoom
    camera.handle_input(event, 800, 600)

    assert camera.target_zoom > initial_zoom
    assert camera.target_zoom <= camera.max_zoom

    # Test max zoom
    camera.target_zoom = camera.max_zoom
    camera.handle_input(event, 800, 600)
    assert camera.target_zoom == camera.max_zoom


def test_handle_input_pan(camera):
    # Mock mouse motion event with middle click
    event = MagicMock()
    event.type = pygame.MOUSEMOTION
    event.rel = (10, 20)

    with patch("pygame.mouse.get_pressed", return_value=(0, 1, 0)):  # Middle click
        initial_cam_x = camera.camera_x
        initial_cam_y = camera.camera_y

        camera.handle_input(event, 800, 600)

        # Camera moves opposite to drag
        assert camera.camera_x == initial_cam_x - 10
        assert camera.camera_y == initial_cam_y - 20


def test_handle_input_other(camera):
    # Test other events are ignored
    event = MagicMock()
    event.type = pygame.KEYDOWN

    initial_zoom = camera.target_zoom
    initial_cam_x = camera.camera_x

    camera.handle_input(event, 800, 600)

    assert camera.target_zoom == initial_zoom
    assert camera.camera_x == initial_cam_x


def test_update_zoom_smoothing(camera):
    camera.zoom = 1.0
    camera.target_zoom = 2.0

    dt = 0.1
    camera.update(dt)

    # Zoom should approach target
    assert camera.zoom > 1.0
    assert camera.zoom < 2.0


def test_render_system_update():
    screen = MagicMock()
    screen.get_size.return_value = (800, 600)
    # Mock screen rect for culling check
    screen_rect = MagicMock()
    screen.get_rect.return_value = screen_rect
    # Make colliderect return True so we draw

    camera = Camera()
    rm = MagicMock()

    # Mock image
    img = MagicMock()
    img.get_rect.return_value = MagicMock()
    # Simulate colliderect
    img.get_rect.return_value.colliderect.return_value = True
    img.get_size.return_value = (32, 32)

    rm.load_image.return_value = img

    # RenderSystem takes screen and world, fetches camera and rm from world services
    world = MagicMock()
    # Mock services.get behavior for multiple types
    from yukkuri_game.engine.resource_manager import ResourceManager

    def get_service(service_type):
        if service_type == Camera:
            return camera
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

    # Mock get_components_tuple for efficient rendering
    world.get_components_tuple.side_effect = [
        # First call is for (Transform, Sprite, VisualTransform)
        [(ent, (transform, sprite, visual_transform))],
        # Second call (if any) is for (Transform, FloatingText) - return empty
        [],
    ]

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
    world.try_get_component.side_effect = get_component_side_effect

    with patch("pygame.draw.line"), patch("pygame.draw.rect"):
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

    camera = Camera()
    # Zoom in to trigger scaling code
    camera.zoom = 2.0

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
    with patch("pygame.transform.scale", return_value=scaled_img) as mock_scale:
        rm.load_image.return_value = img

        world = MagicMock()
        from yukkuri_game.engine.resource_manager import ResourceManager

        def get_service(service_type):
            if service_type == Camera:
                return camera
            if service_type == ResourceManager:
                return rm
            return None

        world.services.get.side_effect = get_service

        rs = RenderSystem(screen, world)

        ent = 1
        world.get_entities_with.return_value = [ent]

        transform = Transform(
            x=0, y=0, scale=1.0
        )  # Scale 1.0 * Zoom 2.0 = 2.0 effective scale
        sprite = Sprite(image_name="test.png", width=32, height=32)
        selectable = Selectable(selected=True)
        phys_body = PhysicsBody(body=MagicMock(), shape=MagicMock())
        visual_transform = VisualTransform()

        # Mock get_components_tuple for efficient rendering
        world.get_components_tuple.side_effect = [
            # First call is for (Transform, Sprite, VisualTransform)
            [(ent, (transform, sprite, visual_transform))],
            # Second call (if any) is for (Transform, FloatingText) - return empty
            [],
        ]

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
        world.try_get_component.side_effect = get_component_side_effect

        with patch("pygame.draw.line"), patch("pygame.draw.rect") as mock_rect:
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

    camera = Camera()
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
        if service_type == Camera:
            return camera
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

    # Mock get_components_tuple for efficient rendering
    world.get_components_tuple.side_effect = [
        # First call is for (Transform, Sprite, VisualTransform)
        [(ent, (transform, sprite, visual_transform))],
        # Second call (if any) is for (Transform, FloatingText) - return empty
        [],
    ]

    world.get_component.side_effect = (
        lambda e, c: transform
        if c == Transform
        else (
            sprite
            if c == Sprite
            else (
                phys_body
                if c == PhysicsBody
                else (visual_transform if c == VisualTransform else None)
            )
        )
    )
    world.try_get_component.side_effect = world.get_component.side_effect

    with patch("pygame.draw.line"), patch("pygame.draw.rect"):
        rs.update(world, 0.016)

        # Should not blit if culled
        screen.blit.assert_not_called()


def test_render_system_update_invalid_size():
    screen = MagicMock()
    screen.get_size.return_value = (800, 600)
    camera = Camera()
    camera.zoom = 0.001  # Very small zoom

    rm = MagicMock()
    img = MagicMock()
    img.get_size.return_value = (32, 32)
    rm.load_image.return_value = img

    world = MagicMock()
    from yukkuri_game.engine.resource_manager import ResourceManager

    def get_service(service_type):
        if service_type == Camera:
            return camera
        if service_type == ResourceManager:
            return rm
        return None

    world.services.get.side_effect = get_service

    rs = RenderSystem(screen, world)

    ent = 1
    world.get_entities_with.return_value = [ent]

    transform = Transform(x=0, y=0, scale=0.1)  # Resulting size will be ~0
    sprite = Sprite(image_name="test.png", width=32, height=32)
    phys_body = PhysicsBody(body=MagicMock(), shape=MagicMock())
    visual_transform = VisualTransform()

    # Mock get_components_tuple for efficient rendering
    world.get_components_tuple.side_effect = [
        # First call is for (Transform, Sprite, VisualTransform)
        [(ent, (transform, sprite, visual_transform))],
        # Second call (if any) is for (Transform, FloatingText) - return empty
        [],
    ]

    world.get_component.side_effect = (
        lambda e, c: transform
        if c == Transform
        else (
            sprite
            if c == Sprite
            else (
                phys_body
                if c == PhysicsBody
                else (visual_transform if c == VisualTransform else None)
            )
        )
    )
    world.try_get_component.side_effect = world.get_component.side_effect

    with patch("pygame.draw.line"), patch("pygame.draw.rect"):
        rs.update(world, 0.016)

        # Should not blit if size <= 0
        screen.blit.assert_not_called()


def test_render_system_missing_components():
    screen = MagicMock()
    screen.get_size.return_value = (800, 600)
    camera = Camera()
    rm = MagicMock()

    world = MagicMock()
    from yukkuri_game.engine.resource_manager import ResourceManager

    def get_service(service_type):
        if service_type == Camera:
            return camera
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

    with patch("pygame.draw.line"), patch("pygame.draw.rect"):
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


@pytest.fixture
def mock_screen():
    m = MagicMock(spec=pygame.Surface)
    m.get_size.return_value = (800, 600)
    m.get_rect.return_value = pygame.Rect(0, 0, 800, 600)
    return m


@pytest.fixture
def mock_camera():
    m = Mock()
    m.world_to_screen.side_effect = lambda wx, wy, sw, sh: (wx, wy)
    m.screen_to_world.side_effect = lambda sx, sy, sw, sh: (sx, sy)
    m.zoom = 1.0
    return m


@pytest.fixture
def mock_rm():
    m = Mock()
    # Return a 128x128 white surface
    s = pygame.Surface((128, 128))
    s.fill((255, 255, 255))
    m.load_image.return_value = s
    return m


def test_single_frame_large_image_scaling(mock_screen, mock_camera, mock_rm):
    """
    Test that a single frame sprite with a larger source image is scaled, not cropped.
    We verify this by ensuring pygame.transform.scale is called.
    """
    renderer = WorldRenderer(mock_screen, mock_camera, mock_rm)
    world = World()

    ent = world.create_entity()
    world.add_component(ent, Transform(x=100, y=100))
    # Sprite definition says 32x32, but loaded image is 128x128
    world.add_component(
        ent, Sprite(image_name="test.png", width=32, height=32, frame_count=1)
    )
    world.add_component(ent, VisualTransform())
    world.add_component(ent, PhysicsBody(body=Mock(), shape=Mock()))

    # Mock pygame.draw functions to avoid type checks
    with (
        patch("pygame.draw.line"),
        patch("pygame.draw.ellipse"),
        patch("pygame.draw.rect"),
        patch("pygame.transform.scale") as mock_scale,
    ):
        # mock_scale needs to return a surface or something with get_rect
        mock_scaled_surf = MagicMock(spec=pygame.Surface)
        mock_scaled_surf.get_rect.return_value = pygame.Rect(0, 0, 32, 32)
        mock_scale.return_value = mock_scaled_surf

        renderer.render(world)

        # Verify that pygame.transform.scale was called with the correct arguments
        # args[0] is the source image (our 128x128 mock)
        # args[1] is the target size (32, 32)

        assert mock_scale.called, "pygame.transform.scale was not called"

        # Check arguments of the first call
        args, _ = mock_scale.call_args
        assert args[1] == (32, 32), f"Expected scale to (32, 32), got {args[1]}"

        # Ensure blit happened with the result of scale
        found_sprite = False
        for call_args in mock_screen.blit.call_args_list:
            surface = call_args[0][0]
            if surface is mock_scaled_surf:
                found_sprite = True
                break

        assert found_sprite, "The scaled surface was not blitted to the screen"


def test_single_frame_matching_image_no_scaling(mock_screen, mock_camera, mock_rm):
    """
    Test that a single frame sprite with matching source image size is NOT scaled.
    """
    renderer = WorldRenderer(mock_screen, mock_camera, mock_rm)
    world = World()

    ent = world.create_entity()
    world.add_component(ent, Transform(x=100, y=100))

    # Matching size: 128x128 sprite, 128x128 image
    world.add_component(
        ent, Sprite(image_name="test.png", width=128, height=128, frame_count=1)
    )
    world.add_component(ent, VisualTransform())
    world.add_component(ent, PhysicsBody(body=Mock(), shape=Mock()))

    with (
        patch("pygame.draw.line"),
        patch("pygame.draw.ellipse"),
        patch("pygame.draw.rect"),
        patch("pygame.transform.scale") as mock_scale,
    ):
        renderer.render(world)

        # Verify that pygame.transform.scale was NOT called
        assert not mock_scale.called, (
            "pygame.transform.scale should not be called for matching dimensions"
        )
