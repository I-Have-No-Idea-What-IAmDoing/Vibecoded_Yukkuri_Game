import pytest
from unittest.mock import MagicMock, patch, mock_open
import os
import msgspec
from src.yukkuri_game.engine.resource_manager import ResourceManager
from src.yukkuri_game.engine.data_models import YukkuriData, ItemData, AIData

class SimpleModel(msgspec.Struct):
    key: str
    section: dict

def test_load_toml_model_success():
    rm = ResourceManager()
    toml_content = b'key = "value"\n[section]\nsub = 123'

    with patch("builtins.open", mock_open(read_data=toml_content)):
        data = rm.load_toml_model("test.toml", SimpleModel)

    assert data is not None
    assert data.key == "value"
    assert data.section["sub"] == 123

def test_load_toml_model_failure():
    rm = ResourceManager()

    # Simulate file not found or read error
    with patch("builtins.open", side_effect=FileNotFoundError):
        data = rm.load_toml_model("nonexistent.toml", SimpleModel)

    assert data is None

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

def test_load_all_data():
    rm = ResourceManager()

    mock_yukkuri = MagicMock(spec=YukkuriData)
    mock_yukkuri.yukkuris = {"Reimu": {}}

    mock_items = MagicMock(spec=ItemData)
    mock_items.items = {"Cookie": {}}

    mock_ai = MagicMock(spec=AIData)
    mock_ai.actions = {"Eat": {}}

    with patch.object(rm, 'load_toml_model', side_effect=[mock_yukkuri, mock_items, mock_ai]) as mock_load:
        rm.load_all_data()

        assert rm.yukkuri_types == {"Reimu": {}}
        assert rm.item_types == {"Cookie": {}}
        assert rm.ai_actions == {"Eat": {}}

        assert mock_load.call_count == 3
