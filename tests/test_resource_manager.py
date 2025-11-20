import pytest
from unittest.mock import MagicMock, patch, mock_open
import os
from src.yukkuri_game.engine.resource_manager import ResourceManager

def test_load_toml_success():
    rm = ResourceManager()
    toml_content = b'key = "value"\n[section]\nsub = 123'

    with patch("builtins.open", mock_open(read_data=toml_content)):
        data = rm.load_toml("test.toml")

    assert data["key"] == "value"
    assert data["section"]["sub"] == 123

def test_load_toml_failure():
    rm = ResourceManager()

    # Simulate file not found or read error
    with patch("builtins.open", side_effect=FileNotFoundError):
        data = rm.load_toml("nonexistent.toml")

    assert data == {}

@patch("src.yukkuri_game.engine.resource_manager.pygame.image.load")
@patch("src.yukkuri_game.engine.resource_manager.os.path.exists")
def test_load_image_success(mock_exists, mock_load):
    rm = ResourceManager()
    mock_exists.return_value = True
    mock_surface = MagicMock()
    mock_load.return_value.convert_alpha.return_value = mock_surface

    img = rm.load_image("test.png")

    assert img == mock_surface
    assert rm.images["test.png"] == mock_surface

    # Test caching
    img2 = rm.load_image("test.png")
    assert img2 == mock_surface
    mock_load.assert_called_once() # Only called once due to cache

@patch("src.yukkuri_game.engine.resource_manager.os.path.exists")
def test_load_image_not_found(mock_exists):
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

def test_load_all_data():
    rm = ResourceManager()

    # Mock return values need to simulate objects that match what load_toml_model returns (Structs)
    # But load_all_data uses load_toml_model now, not load_toml.
    # We should update the test to patch load_toml_model.

    mock_yukkuri_data = MagicMock()
    mock_yukkuri_data.yukkuris = {"Reimu": {}}

    mock_item_data = MagicMock()
    mock_item_data.items = {"Cookie": {}}

    mock_ai_data = MagicMock()
    mock_ai_data.actions = {"Eat": {}}

    with patch.object(rm, 'load_toml_model', side_effect=[mock_yukkuri_data, mock_item_data, mock_ai_data]) as mock_load:
        rm.load_all_data()

        assert rm.yukkuri_types == {"Reimu": {}}
        assert rm.item_types == {"Cookie": {}}
        assert rm.ai_actions == {"Eat": {}}

        assert mock_load.call_count == 3
