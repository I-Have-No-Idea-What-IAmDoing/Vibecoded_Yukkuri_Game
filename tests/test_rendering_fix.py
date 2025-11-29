
import pytest
import pygame
from unittest.mock import Mock, patch, MagicMock
from yukkuri_game.game.yukkurrium import WorldRenderer
from yukkuri_game.game.components import Sprite, Transform, VisualTransform, PhysicsBody
from yukkuri_game.engine.ecs import World

@pytest.fixture
def mock_screen():
    m = MagicMock(spec=pygame.Surface)
    m.get_size.return_value = (800, 600)
    m.get_rect.return_value = pygame.Rect(0, 0, 800, 600)
    return m

@pytest.fixture
def mock_yukkurrium():
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

def test_single_frame_large_image_scaling(mock_screen, mock_yukkurrium, mock_rm):
    """
    Test that a single frame sprite with a larger source image is scaled, not cropped.
    We verify this by ensuring pygame.transform.scale is called.
    """
    renderer = WorldRenderer(mock_screen, mock_yukkurrium, mock_rm)
    world = World()

    ent = world.create_entity()
    world.add_component(ent, Transform(x=100, y=100))
    # Sprite definition says 32x32, but loaded image is 128x128
    world.add_component(ent, Sprite(image_name="test.png", width=32, height=32, frame_count=1))
    world.add_component(ent, VisualTransform())
    world.add_component(ent, PhysicsBody(body=Mock(), shape=Mock()))

    # Mock pygame.draw functions to avoid type checks
    with patch('pygame.draw.line'), \
         patch('pygame.draw.ellipse'), \
         patch('pygame.draw.rect'), \
         patch('pygame.transform.scale') as mock_scale:

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

def test_single_frame_matching_image_no_scaling(mock_screen, mock_yukkurrium, mock_rm):
    """
    Test that a single frame sprite with matching source image size is NOT scaled.
    """
    renderer = WorldRenderer(mock_screen, mock_yukkurrium, mock_rm)
    world = World()

    ent = world.create_entity()
    world.add_component(ent, Transform(x=100, y=100))

    # Matching size: 128x128 sprite, 128x128 image
    world.add_component(ent, Sprite(image_name="test.png", width=128, height=128, frame_count=1))
    world.add_component(ent, VisualTransform())
    world.add_component(ent, PhysicsBody(body=Mock(), shape=Mock()))

    with patch('pygame.draw.line'), \
         patch('pygame.draw.ellipse'), \
         patch('pygame.draw.rect'), \
         patch('pygame.transform.scale') as mock_scale:

        renderer.render(world)

        # Verify that pygame.transform.scale was NOT called
        assert not mock_scale.called, "pygame.transform.scale should not be called for matching dimensions"
