"""
Tests for the Resource Manager.
"""

from unittest.mock import MagicMock, patch, mock_open
from yukkuri_game.engine.resource_manager import ResourceManager

from typing import Dict
import msgspec


class MockModel(msgspec.Struct):
    """Mock model for testing TOML loading."""

    key: str
    section: Dict[str, int]


def test_load_toml_success() -> None:
    """
    Tests successful loading and parsing of a TOML file.
    """
    rm = ResourceManager()
    toml_content = b'key = "value"\n[section]\nsub = 123'

    with patch("builtins.open", mock_open(read_data=toml_content)):
        data = rm.load_toml_model("test.toml", MockModel)

    assert data.key == "value"
    assert data.section["sub"] == 123


def test_load_toml_failure() -> None:
    """
    Tests graceful failure when loading a missing TOML file.
    """
    rm = ResourceManager()

    # Simulate file not found or read error
    with patch("builtins.open", side_effect=FileNotFoundError):
        data = rm.load_toml_model("nonexistent.toml", MockModel)

    assert data is None


@patch("yukkuri_game.engine.resource_manager.pygame.image.load")
@patch("yukkuri_game.engine.resource_manager.os.path.exists")
def test_load_image_success(mock_exists: MagicMock, mock_load: MagicMock) -> None:
    """
    Tests successful loading and caching of an image.
    """
    import pygame  # Ensure pygame is available
    rm = ResourceManager()
    # Mock atlas to avoid interference and force disk load
    rm.atlas = MagicMock()
    rm.atlas.get_region.return_value = None
    rm.atlas.add_image.return_value = False  # Simulate full atlas, fallback to image cache

    mock_exists.return_value = True
    
    # Use real surface to satisfy TextureAtlas.add_image -> surface.blit requirements
    real_surface = pygame.Surface((32, 32))
    mock_load.return_value.convert_alpha.return_value = real_surface

    img = rm.load_image("test.png")

    # Check if it's a surface
    assert isinstance(img, pygame.Surface)
    assert img.get_size() == (32, 32)

    # Since atlas.add_image is mocked to return False, it should be in the cache
    assert rm.images["test.png"] == real_surface

    img2 = rm.load_image("test.png")
    assert img2.get_size() == (32, 32)
    # mock_load should be called once (cached)
    mock_load.assert_called_once()


@patch("yukkuri_game.engine.resource_manager.os.path.exists")
def test_load_image_not_found(mock_exists: MagicMock) -> None:
    """
    Tests that a placeholder image is returned when the file is missing.
    """
    rm = ResourceManager()
    mock_exists.return_value = False

    # Should return a magenta placeholder
    img = rm.load_image("missing.png")

    assert img.get_size() == (32, 32)


def test_load_all_data() -> None:
    """
    Tests loading all game data (types, items, actions).
    """
    from yukkuri_game.engine.lazy_loader import LazyLoader

    rm = ResourceManager()

    # Create mock data objects that match the expected return types of load_toml_model
    mock_yukkuri_data = MagicMock()
    mock_yukkuri_data.yukkuris = {"Reimu": {}}

    mock_item_data = MagicMock()
    mock_item_data.items = {"Cookie": {}}

    mock_ai_data = MagicMock()
    mock_ai_data.actions = {"Eat": {}}

    mock_tuning_data = MagicMock()

    # We need to simulate the return values for when LazyLoaders actually trigger
    # Tuning is loaded eagerly, others are lazy.
    # Order of side_effect depends on access order.
    # 1. Tuning (Eager)
    # 2. Yukkuris (Lazy access)
    # 3. Items (Lazy access)
    # 4. Actions (Lazy access)
    
    with patch.object(
        rm,
        "load_toml_model",
        side_effect=[
            mock_tuning_data,      # Tuning (eager)
            mock_yukkuri_data,     # Yukkuris (lazy)
            mock_item_data,        # Items (lazy)
            mock_ai_data,          # Actions (lazy)
            MagicMock(),           # Skills (lazy)
            MagicMock(),           # Traits (lazy)
            MagicMock(),           # Interactions (lazy)
        ],
    ) as mock_load:
        rm.load_all_data()
        
        # Verify LazyLoaders are created
        assert isinstance(rm.yukkuri_types, LazyLoader)
        assert isinstance(rm.item_types, LazyLoader)
        assert isinstance(rm.ai_actions, LazyLoader)
        assert isinstance(rm.skills, LazyLoader)
        assert isinstance(rm.traits, LazyLoader)
        assert isinstance(rm.interactions, LazyLoader)
        assert rm.tuning == mock_tuning_data
        
        # Verify eager load happened
        assert mock_load.call_count == 1
        
        # Trigger Lazy Loading
        assert rm.yukkuri_types["Reimu"] == {}
        assert mock_load.call_count == 2
        
        assert rm.item_types["Cookie"] == {}
        assert mock_load.call_count == 3
        
        assert rm.ai_actions["Eat"] == {}
