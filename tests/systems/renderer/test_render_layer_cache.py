"""
Unit tests for RenderSystem layer caching.
"""

import pytest
import pygame
from unittest.mock import MagicMock

from yukkuri_game.game.systems.render_system import RenderSystem
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

        render_system = RenderSystem(screen, world)

        assert render_system._background_cache is None
        assert render_system._background_cache_valid is False
        assert render_system._last_camera_state is None

    def test_cache_built_on_first_update(self, pygame_init, mock_world):
        """Cache should be built on first update call."""
        world, camera = mock_world
        screen = pygame.Surface((800, 600))

        render_system = RenderSystem(screen, world)
        render_system.update(world, dt=0.016)

        assert render_system._background_cache is not None
        assert render_system._background_cache_valid is True
        assert render_system._last_camera_state is not None

    def test_cache_not_rebuilt_when_camera_static(self, pygame_init, mock_world):
        """Cache should NOT be rebuilt if camera hasn't moved."""
        world, camera = mock_world
        screen = pygame.Surface((800, 600))

        render_system = RenderSystem(screen, world)

        # First update builds cache
        render_system.update(world, dt=0.016)
        first_cache = render_system._background_cache

        # Second update should reuse cache
        render_system.update(world, dt=0.016)
        second_cache = render_system._background_cache

        # Same object reference means cache was NOT rebuilt
        assert first_cache is second_cache

    def test_cache_rebuilt_when_camera_moves(self, pygame_init, mock_world):
        """Cache should be rebuilt when camera position changes significantly."""
        world, camera = mock_world
        screen = pygame.Surface((800, 600))

        render_system = RenderSystem(screen, world)

        # First update builds cache
        render_system.update(world, dt=0.016)
        initial_state = render_system._last_camera_state

        # Move camera significantly (more than cache margin of 200)
        camera.camera_x = 300.0
        camera.camera_y = 300.0

        # Update should detect change and invalidate
        render_system.update(world, dt=0.016)
        new_state = render_system._last_camera_state

        # States should be different
        assert initial_state != new_state
        assert render_system._background_cache_valid is True  # Rebuilt

    def test_cache_not_rebuilt_for_small_movement(self, pygame_init, mock_world):
        """Cache should NOT be rebuilt for movements within the margin."""
        world, camera = mock_world
        screen = pygame.Surface((800, 600))

        render_system = RenderSystem(screen, world)

        # First update
        render_system.update(world, dt=0.016)
        initial_state = render_system._last_camera_state

        # Move camera by 100 pixels (within 200px margin)
        camera.camera_x = 100.0
        camera.camera_y = 100.0

        # Update should NOT invalidate
        render_system.update(world, dt=0.016)
        new_state = render_system._last_camera_state

        # State should be the same
        assert initial_state == new_state

    def test_cache_rebuilt_when_zoom_changes(self, pygame_init, mock_world):
        """Cache should be rebuilt when zoom level changes."""
        world, camera = mock_world
        screen = pygame.Surface((800, 600))

        render_system = RenderSystem(screen, world)

        # First update builds cache
        render_system.update(world, dt=0.016)
        initial_state = render_system._last_camera_state

        # Change zoom
        camera.zoom = 1.5

        # Update should detect change
        render_system.update(world, dt=0.016)
        new_state = render_system._last_camera_state

        # Zoom is part of state, so states should differ
        assert initial_state != new_state

    def test_cache_not_rebuilt_for_subpixel_movement(self, pygame_init, mock_world):
        """Cache should NOT be rebuilt for sub-pixel camera movements."""
        world, camera = mock_world
        screen = pygame.Surface((800, 600))

        render_system = RenderSystem(screen, world)

        # First update
        render_system.update(world, dt=0.016)
        initial_state = render_system._last_camera_state

        # Move camera by less than 1 pixel (sub-pixel)
        camera.camera_x = 0.5
        camera.camera_y = 0.3

        # Update should NOT invalidate (int() rounds down to 0)
        render_system.update(world, dt=0.016)
        new_state = render_system._last_camera_state

        # State should be the same (both round to 0)
        assert initial_state == new_state


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
