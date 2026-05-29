"""
Tests for the Resource Manager.

This module validates the functionality of the `ResourceManager`, ensuring robust handling
of TOML data files, image assets, and fallback mechanisms like lazy loading and caching.
"""

from unittest.mock import MagicMock, patch, mock_open
from typing import Dict
import msgspec
from yukkuri_game.engine.resource_manager import ResourceManager


class MockModel(msgspec.Struct):
    """
    Mock data model for testing TOML parsing.
    """

    key: str
    section: Dict[str, int]


def test_load_toml_success() -> None:
    """
    Verifies that a TOML file is correctly read and parsed into a model.

    Setup:
        - Mocks the built-in `open` function with valid TOML byte content.

    Assertions:
        - The `ResourceManager.load_toml_model` method returns a `MockModel` instance.
        - The parsed attributes (`key`, `section`) match the expected values.
    """
    rm = ResourceManager()
    toml_content = b'key = "value"\n[section]\nsub = 123'

    with patch("builtins.open", mock_open(read_data=toml_content)):
        data = rm.load_toml_model("test.toml", MockModel)

    assert data.key == "value"
    assert data.section["sub"] == 123


def test_load_toml_failure() -> None:
    """
    Verifies graceful handling of missing or inaccessible TOML files.

    Setup:
        - Mocks the built-in `open` function to raise `FileNotFoundError`.

    Assertions:
        - The `ResourceManager.load_toml_model` method returns `None` instead of raising an exception.
    """
    rm = ResourceManager()

    with patch("builtins.open", side_effect=FileNotFoundError):
        data = rm.load_toml_model("nonexistent.toml", MockModel)

    assert data is None


@patch("yukkuri_game.engine.resource_manager.pygame.image.load")
@patch("yukkuri_game.engine.resource_manager.os.path.exists")
def test_load_image_success(mock_exists: MagicMock, mock_load: MagicMock) -> None:
    """
    Verifies that an image is successfully loaded from disk when not cached.

    Setup:
        - Mocks `os.path.exists` to return True.
        - Mocks `pygame.image.load` to return a dummy surface.
        - Mocks `TextureAtlas` to report a full atlas, forcing a cache fallback.

    Assertions:
        - The returned object is a `pygame.Surface`.
        - The image is added to the `rm.images` cache.
        - A second call for the same image hits the cache (no second load).
    """
    import pygame  # Ensure pygame is available for typing
    rm = ResourceManager()
    
    # Force disk load path: mocked atlas refuses to accept new image
    rm.atlas = MagicMock()
    rm.atlas.get_region.return_value = None
    rm.atlas.add_image.return_value = False

    mock_exists.return_value = True
    
    # Create valid surface for atlas compatibility checks
    real_surface = pygame.Surface((32, 32))
    mock_load.return_value.convert_alpha.return_value = real_surface

    img = rm.load_image("test.png")

    assert isinstance(img, pygame.Surface)
    assert img.get_size() == (32, 32)
    assert rm.images["test.png"] == real_surface

    # Verify Caching behavior
    img2 = rm.load_image("test.png")
    assert img2.get_size() == (32, 32)
    mock_load.assert_called_once()


@patch("yukkuri_game.engine.resource_manager.os.path.exists")
def test_load_image_not_found(mock_exists: MagicMock) -> None:
    """
    Verifies that a placeholder image is returned when the target file is missing.

    Setup:
        - Mocks `os.path.exists` to return False.

    Assertions:
        - The method returns a valid `pygame.Surface` (placeholder).
        - The returned surface has the expected dimensions (32x32).
    """
    rm = ResourceManager()
    mock_exists.return_value = False

    img = rm.load_image("missing.png")

    assert img.get_size() == (32, 32)


@patch("yukkuri_game.engine.resource_manager.pygame.image.load")
@patch("yukkuri_game.engine.resource_manager.os.path.exists")
def test_load_image_fallback(
    mock_exists: MagicMock, mock_load: MagicMock
) -> None:
    """
    Verifies fallback to base image when action-specific sprite is missing.

    Setup:
        - Mocks os.path.exists to return False for action-specific filename,
          but True for the base filename.
        - Mocks pygame.image.load to return a 64x64 dummy surface.

    Assertions:
        - Returns a valid pygame.Surface of 64x64.
        - Both filenames cache the same surface.
    """
    import pygame
    rm = ResourceManager()

    # Force disk load path: mocked atlas refuses to accept new image
    rm.atlas = MagicMock()
    rm.atlas.get_region.return_value = None
    rm.atlas.add_image.return_value = False

    def side_effect(path: str) -> bool:
        if "reimu_wander.png" in path:
            return False
        if "reimu.png" in path:
            return True
        return False

    mock_exists.side_effect = side_effect

    real_surface = pygame.Surface((64, 64))
    mock_load.return_value.convert_alpha.return_value = real_surface

    img = rm.load_image("reimu_wander.png")

    assert img == real_surface
    assert rm.images["reimu_wander.png"] == real_surface
    called_path = mock_load.call_args[0][0]
    assert "reimu.png" in called_path


def test_load_all_data() -> None:
    """
    Verifies the initialization and monolithic loading behavior of LazyLoaders.

    This test checks the 'lazy' nature of data loading:
    1.  Verifies eager loading of `tuning` data.
    2.  Verifies `LazyLoader` initialization for other resources.
    3.  Triggers a lazy load and ensures the underlying `_load_monolithic` is called.
    
    Setup:
        - Mocks `load_toml_model` to return specific distinct mock objects for each call.
    """
    from yukkuri_game.engine.lazy_loader import LazyLoader

    rm = ResourceManager()

    # Define mock data structures for expected returns
    mock_yukkuri_data = MagicMock()
    mock_yukkuri_data.yukkuris = {"Reimu": {}}

    mock_item_data = MagicMock()
    mock_item_data.items = {"Cookie": {}}

    mock_ai_data = MagicMock()
    mock_ai_data.actions = {"Eat": {}}

    mock_tuning_data = MagicMock()

    # Sequence of returns:
    # 1. Tuning (Eager)
    # 2. Yukkuris (Triggered by lazy access)
    # 3. Items (Triggered by lazy access)
    # 4. Actions (Triggered by lazy access)
    # 5-7. Remaining LazyLoaders (Skills, Traits, Interactions)
    
    with patch.object(
        rm,
        "load_toml_model",
        side_effect=[
            mock_tuning_data,
            mock_yukkuri_data,
            mock_item_data,
            mock_ai_data,
            MagicMock(),
            MagicMock(),
            MagicMock(),
        ],
    ) as mock_load:
        rm.load_all_data()
        
        # Assertion 1: Verify correct type initialization
        assert isinstance(rm.yukkuri_types, LazyLoader)
        assert isinstance(rm.item_types, LazyLoader)
        assert isinstance(rm.ai_actions, LazyLoader)
        assert isinstance(rm.skills, LazyLoader)
        assert isinstance(rm.traits, LazyLoader)
        assert isinstance(rm.interactions, LazyLoader)
        assert rm.tuning == mock_tuning_data
        
        # Assertion 2: Verify Eager Load (only Tuning)
        assert mock_load.call_count == 1
        
        # Assertion 3: Verify Lazy Loading Trigger
        # Accessing "Reimu" triggers the second call to load_toml_model
        assert rm.yukkuri_types["Reimu"] == {}
        assert mock_load.call_count == 2
        
        assert rm.item_types["Cookie"] == {}
        assert mock_load.call_count == 3
        
        assert rm.ai_actions["Eat"] == {}
