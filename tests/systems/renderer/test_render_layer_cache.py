"""
Unit tests for RenderSystem layer caching.
"""

import pytest
import pygame
from unittest.mock import MagicMock

from yukkuri_game.game.systems.rendering.system import RenderingSystem
from yukkuri_game.game.systems.rendering.passes.background_pass import BackgroundPass
from yukkuri_game.game.camera import Camera
from yukkuri_game.engine.resource_manager import ResourceManager


@pytest.fixture
def pygame_init():
    """Initialize pygame for tests."""
    pygame.init()
    yield
    pygame.quit()


@pytest.fixture
def mock_world():
    """Create a mock World with required services."""
    # Don't use spec=World because we need to mock services dynamically
    world = MagicMock()

    # Mock ResourceManager
    rm = MagicMock()
    rm.get_image.return_value = pygame.Surface((32, 32))

    # Mock Camera
    camera = Camera()
    camera.camera_x = 0.0
    camera.camera_y = 0.0
    camera.zoom = 1.0

    # Configure services - use a dict-based lookup for both get and try_get
    services_map = {
        ResourceManager: rm,
        Camera: camera,
    }
    world.services.get.side_effect = lambda t: services_map.get(t)
    world.services.try_get.return_value = None
    world.get_components_tuple.return_value = []

    return world, camera


class TestLayerCaching:
    """Tests for background layer caching in RenderSystem."""

    def test_cache_initialized_as_invalid(self, pygame_init, mock_world):
        """Cache should start as invalid."""
        world, camera = mock_world
        screen = pygame.Surface((800, 600))

        render_system = RenderingSystem(screen, world)
        bg_pass = render_system.pipeline.get_pass(BackgroundPass)

        assert bg_pass._background_cache is None
        assert bg_pass._background_cache_valid is False
        assert bg_pass._last_camera_state is None

    def test_cache_built_on_first_update(self, pygame_init, mock_world):
        """Cache should be built on first update call."""
        world, camera = mock_world
        screen = pygame.Surface((800, 600))

        render_system = RenderingSystem(screen, world)
        render_system.render(world, alpha=1.0)
        bg_pass = render_system.pipeline.get_pass(BackgroundPass)

        assert bg_pass._background_cache is not None
        assert bg_pass._background_cache_valid is True
        assert bg_pass._last_camera_state is not None

    def test_cache_not_rebuilt_when_camera_static(self, pygame_init, mock_world):
        """Cache should NOT be rebuilt if camera hasn't moved."""
        world, camera = mock_world
        screen = pygame.Surface((800, 600))

        render_system = RenderingSystem(screen, world)
        bg_pass = render_system.pipeline.get_pass(BackgroundPass)

        # First update builds cache
        render_system.render(world, alpha=1.0)
        first_cache = bg_pass._background_cache

        # Second update should reuse cache
        render_system.render(world, alpha=1.0)
        second_cache = bg_pass._background_cache

        # Same object reference means cache was NOT rebuilt
        assert first_cache is second_cache

    def test_cache_rebuilt_when_camera_moves(self, pygame_init, mock_world):
        """Cache should be rebuilt when camera position changes significantly."""
        world, camera = mock_world
        screen = pygame.Surface((800, 600))

        render_system = RenderingSystem(screen, world)
        bg_pass = render_system.pipeline.get_pass(BackgroundPass)

        # First update builds cache
        render_system.render(world, alpha=1.0)
        initial_state = bg_pass._last_camera_state

        # Move camera significantly (more than cache margin of 200)
        camera.prev_camera_x = camera.camera_x
        camera.prev_camera_y = camera.camera_y
        camera.camera_x = 300.0
        camera.camera_y = 300.0

        # Update should detect change and invalidate
        render_system.render(world, alpha=1.0)
        new_state = bg_pass._last_camera_state

        # States should be different
        assert initial_state != new_state
        assert bg_pass._background_cache_valid is True  # Rebuilt

    def test_cache_not_rebuilt_for_small_movement(self, pygame_init, mock_world):
        """Cache should NOT be rebuilt for movements within the margin."""
        world, camera = mock_world
        screen = pygame.Surface((800, 600))

        render_system = RenderingSystem(screen, world)
        bg_pass = render_system.pipeline.get_pass(BackgroundPass)

        # First update
        render_system.render(world, alpha=1.0)
        initial_state = bg_pass._last_camera_state

        # Move camera by 100 pixels (within 200px margin)
        camera.prev_camera_x = camera.camera_x
        camera.prev_camera_y = camera.camera_y
        camera.camera_x = 100.0
        camera.camera_y = 100.0

        # Update should NOT invalidate
        render_system.render(world, alpha=1.0)
        new_state = bg_pass._last_camera_state

        # State should be the same
        assert initial_state == new_state

    def test_cache_rebuilt_when_zoom_changes(self, pygame_init, mock_world):
        """Cache should be invalidated during zoom transitions.

        During active zoom (zoom != target_zoom), the cache is bypassed
        and the grid is drawn directly. Once zoom stabilizes, the
        cache is rebuilt at the new zoom level.
        """
        world, camera = mock_world
        screen = pygame.Surface((800, 600))

        render_system = RenderingSystem(screen, world)
        bg_pass = render_system.pipeline.get_pass(BackgroundPass)

        # First update builds cache
        render_system.render(world, alpha=1.0)
        assert bg_pass._background_cache_valid is True

        # Simulate zoom change (zoom != target_zoom triggers bypass)
        camera.prev_zoom = camera.zoom
        camera.zoom = 1.5
        camera.target_zoom = 2.0  # Different from zoom -> active transition

        # Update should bypass cache and mark it invalid
        render_system.render(world, alpha=1.0)
        assert bg_pass._background_cache_valid is False

        # Now stabilize zoom (zoom == target_zoom)
        camera.prev_zoom = camera.zoom
        camera.zoom = 2.0
        camera.target_zoom = 2.0
        render_system.render(world, alpha=1.0)

        # Cache should be rebuilt at new zoom
        assert bg_pass._background_cache_valid is True
        new_state = bg_pass._last_camera_state
        assert new_state is not None
        assert new_state[2] == 2.0  # zoom component

    def test_cache_not_rebuilt_for_subpixel_movement(self, pygame_init, mock_world):
        """Cache should NOT be rebuilt for sub-pixel camera movements."""
        world, camera = mock_world
        screen = pygame.Surface((800, 600))

        render_system = RenderingSystem(screen, world)
        bg_pass = render_system.pipeline.get_pass(BackgroundPass)

        # First update
        render_system.render(world, alpha=1.0)
        initial_state = bg_pass._last_camera_state

        # Move camera by less than 1 pixel (sub-pixel)
        camera.prev_camera_x = camera.camera_x
        camera.prev_camera_y = camera.camera_y
        camera.camera_x = 0.5
        camera.camera_y = 0.3

        # Update should NOT invalidate (int() rounds down to 0)
        render_system.render(world, alpha=1.0)
        new_state = bg_pass._last_camera_state

        # State should be the same (both round to 0)
        assert initial_state == new_state


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
