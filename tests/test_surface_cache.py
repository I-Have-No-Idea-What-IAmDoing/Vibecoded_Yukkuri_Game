
import pytest
import pygame
from unittest.mock import MagicMock, patch
from yukkuri_game.game.surface_cache import SurfaceCache
from yukkuri_game.engine.resource_manager import ResourceManager

@pytest.fixture
def mock_resource_manager():
    rm = MagicMock(spec=ResourceManager)
    # Create a dummy surface
    surface = pygame.Surface((100, 100))
    rm.load_image.return_value = surface
    return rm

def test_surface_cache_get_surface_creates_new_surface(mock_resource_manager):
    cache = SurfaceCache(mock_resource_manager)

    # Parameters
    image_name = "test.png"
    frame_index = 0
    frame_count = 1
    sprite_width = 100
    sprite_height = 100
    scale = 1.0
    rotation = 0.0
    flip_x = False
    flip_y = False

    surface = cache.get_surface(
        image_name, frame_index, frame_count, sprite_width, sprite_height,
        scale, rotation, flip_x, flip_y
    )

    assert surface is not None
    assert isinstance(surface, pygame.Surface)
    assert len(cache._cache) == 1

def test_surface_cache_returns_cached_surface(mock_resource_manager):
    cache = SurfaceCache(mock_resource_manager)

    # First call
    surface1 = cache.get_surface(
        "test.png", 0, 1, 100, 100, 1.0, 0.0, False, False
    )

    # Second call with same parameters
    surface2 = cache.get_surface(
        "test.png", 0, 1, 100, 100, 1.0, 0.0, False, False
    )

    assert surface1 is surface2
    assert len(cache._cache) == 1
    # load_image should be called at least once (implementation detail: it is called inside _create_surface)
    mock_resource_manager.load_image.assert_called_once()

def test_surface_cache_eviction(mock_resource_manager):
    max_size = 2
    cache = SurfaceCache(mock_resource_manager, max_size=max_size)

    # Add 1
    cache.get_surface("1.png", 0, 1, 100, 100, 1.0, 0.0, False, False)
    assert len(cache._cache) == 1

    # Add 2
    cache.get_surface("2.png", 0, 1, 100, 100, 1.0, 0.0, False, False)
    assert len(cache._cache) == 2

    # Add 3 (should evict 1)
    cache.get_surface("3.png", 0, 1, 100, 100, 1.0, 0.0, False, False)
    assert len(cache._cache) == 2

    # Check that 1 is gone
    key1 = ("1.png", 0, 100, 100, 1.0, 0.0, False, False)
    assert key1 not in cache._cache

    # Check that 2 and 3 are present
    key2 = ("2.png", 0, 100, 100, 1.0, 0.0, False, False)
    key3 = ("3.png", 0, 100, 100, 1.0, 0.0, False, False)
    assert key2 in cache._cache
    assert key3 in cache._cache

def test_surface_cache_lru_behavior(mock_resource_manager):
    max_size = 2
    cache = SurfaceCache(mock_resource_manager, max_size=max_size)

    # Add 1
    cache.get_surface("1.png", 0, 1, 100, 100, 1.0, 0.0, False, False)
    # Add 2
    cache.get_surface("2.png", 0, 1, 100, 100, 1.0, 0.0, False, False)

    # Access 1 (make it recently used)
    cache.get_surface("1.png", 0, 1, 100, 100, 1.0, 0.0, False, False)

    # Add 3 (should evict 2, because 1 was just used)
    cache.get_surface("3.png", 0, 1, 100, 100, 1.0, 0.0, False, False)

    key1 = ("1.png", 0, 100, 100, 1.0, 0.0, False, False)
    key2 = ("2.png", 0, 100, 100, 1.0, 0.0, False, False)
    key3 = ("3.png", 0, 100, 100, 1.0, 0.0, False, False)

    assert key2 not in cache._cache
    assert key1 in cache._cache
    assert key3 in cache._cache
