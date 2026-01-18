import pytest
from unittest.mock import Mock
from yukkuri_game.engine.lazy_loader import LazyLoader

def test_lazy_loader_initializer_fallback():
    """Test that initializer is called when single item load fails."""
    mock_load = Mock(side_effect=KeyError("Not found individually"))
    mock_init = Mock()
    
    loader = LazyLoader(mock_load, initializer=mock_init)
    
    # Pre-populate cache via initializer side-effect mechanism simulation
    def init_side_effect():
        loader._cache["bulk_item"] = "bulk_value"
    
    mock_init.side_effect = init_side_effect
    
    # Access key that requires initialization
    val = loader["bulk_item"]
    
    assert val == "bulk_value"
    mock_load.assert_called_with("bulk_item")
    mock_init.assert_called_once()

def test_lazy_loader_value_error_handling():
    """Test that ValueError during load triggers initialization attempt."""
    mock_load = Mock(side_effect=ValueError("Corrupt data"))
    mock_init = Mock()
    
    loader = LazyLoader(mock_load, initializer=mock_init)
    
    # If init also fails to provide the key, it raises KeyError
    with pytest.raises(KeyError):
        _ = loader["corrupt_item"]
        
    mock_load.assert_called_with("corrupt_item")
    mock_init.assert_called_once()

def test_lazy_loader_unexpected_exception():
    """Test that unexpected exceptions propagate."""
    mock_load = Mock(side_effect=RuntimeError("Spectacular failure"))
    
    loader = LazyLoader(mock_load)
    
    with pytest.raises(RuntimeError, match="Spectacular failure"):
        _ = loader["boom"]
