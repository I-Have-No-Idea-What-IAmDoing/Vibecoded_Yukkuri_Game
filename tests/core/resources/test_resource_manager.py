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
    mock_exists.return_value = True

    # Use real surface to satisfy TextureAtlas.add_image -> surface.blit requirements
    real_surface = pygame.Surface((32, 32))
    mock_load.return_value.convert_alpha.return_value = real_surface

    img = rm.load_image("test.png")

    # The returned image should be a subsurface from the atlas, NOT the original surface
    # unless atlas packing failed. But with (32, 32) it should succeed.
    # The ResourceManager returns self.atlas.get_region(filename).
    # self.atlas.get_region returns a subsurface.

    # Check if it's a surface
    assert isinstance(img, pygame.Surface)
    assert img.get_size() == (32, 32)

    # Since we use a real surface, caching logic might store the subsurface or the original
    # if atlas packing failed.
    # With atlas packing success, `rm.images` (LRU cache) might NOT have it?
    # Let's check logic:
    # 4. Try Packing into Atlas
    # if self.atlas.add_image(filename, img):
    #    return self.atlas.get_region(filename)

    # So if packing succeeds, it is NOT added to rm.images (LRU cache).
    # But later `load_image` checks:
    # atlas_surf = self.atlas.get_region(filename)
    # if atlas_surf: return atlas_surf

    # So for caching test:
    img2 = rm.load_image("test.png")
    assert img2.get_size() == (32, 32)
    # mock_load should be called once
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
    # Checking color is tricky with mocks unless we inspect calls,
    # but the code creates a Surface and fills it.
    # Since pygame.Surface is real (we didn't mock pygame.Surface constructor), we can check it?
    # But we imported pygame in the module.
    # If we didn't mock pygame, it needs a display for convert_alpha usually, but
    # here the code does `pygame.Surface((32, 32))` which works without display.
    # But `convert_alpha` calls usually need display initialized.
    # The code: `img = pygame.image.load(full_path).convert_alpha()`
    # This line is skipped if not exists.

    # The placeholder creation:
    # surf = pygame.Surface((32, 32))
    # surf.fill((255, 0, 255))

    # This should work headless if SDL_VIDEODRIVER is dummy, but let's see.
    pass


def test_load_all_data() -> None:
    """
    Tests loading all game data (types, items, actions).
    """
    rm = ResourceManager()

    # Create mock data objects that match the expected return types of load_toml_model
    mock_yukkuri_data = MagicMock()
    mock_yukkuri_data.yukkuris = {"Reimu": {}}

    mock_item_data = MagicMock()
    mock_item_data.items = {"Cookie": {}}

    mock_ai_data = MagicMock()
    mock_ai_data.actions = {"Eat": {}}

    mock_tuning_data = MagicMock()

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

        assert rm.yukkuri_types == {"Reimu": {}}
        assert rm.item_types == {"Cookie": {}}
        assert rm.ai_actions == {"Eat": {}}
        assert rm.tuning == mock_tuning_data

        # 1 call for tuning (immediate) + 3 calls for accessed lazy loaders
        assert mock_load.call_count == 4
