
import pytest
from unittest.mock import MagicMock, patch
from yukkuri_game.engine.resource_manager import ResourceManager
from yukkuri_game.engine.input_manager import InputManager, InputContext
from yukkuri_game.engine.exceptions import ResourceLoadError

def test_resource_manager_raises_error_on_missing_file():
    """Test that ResourceManager raises ResourceLoadError for missing critical files."""
    rm = ResourceManager(data_dir="non_existent_dir")
    
    # Mock load_toml_model to simulate failure directly or let it fail if file not found
    # But since we are testing _load_monolithic logic which calls load_toml_model, 
    # we can mock load_toml_model to return None.
    
    with patch.object(rm, 'load_toml_model', return_value=None):
        with pytest.raises(ResourceLoadError):
            rm._load_monolithic("missing.toml", MagicMock(), "test_attr")

def test_resource_manager_raises_error_on_missing_key():
    """Test that ResourceManager raises ResourceLoadError when a specific key is missing."""
    rm = ResourceManager()
    
    # Create a dummy data object
    test_data = MagicMock()
    test_data.test_attr = {"existing_key": "value"}
    
    with patch.object(rm, 'load_toml_model', return_value=test_data):
        # Should succeed
        assert rm._load_monolithic("test.toml", MagicMock(), "test_attr", "existing_key") == "value"
        
        # Should fail
        with pytest.raises(ResourceLoadError):
            rm._load_monolithic("test.toml", MagicMock(), "test_attr", "missing_key")

def test_input_manager_validation():
    """Test that InputManager validates mappings."""
    im = InputManager()
    
    # Valid config
    valid_config = {
        "GAMEPLAY": {
            "test_action": [1, 2, 3]
        }
    }
    im.load_key_mappings(valid_config)
    assert im._key_mappings[InputContext.GAMEPLAY]["test_action"] == [1, 2, 3]

    # Invalid config (non-integer key)
    invalid_config = {
        "GAMEPLAY": {
            "test_action": ["invalid", 2]
        }
    }
    with pytest.raises(ValueError):
        im.load_key_mappings(invalid_config)
