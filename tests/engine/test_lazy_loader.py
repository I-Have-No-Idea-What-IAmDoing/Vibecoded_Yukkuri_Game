import pytest
import sys
import os

# Ensure src is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from yukkuri_game.engine.lazy_loader import LazyLoader

def test_lazy_loader_access():
    loaded_keys = []
    
    def mock_loader(key):
        loaded_keys.append(key)
        if key == "exists":
            return "value"
        return None

    loader = LazyLoader(mock_loader, keys={"exists", "will_load"})
    
    # Should not have loaded yet
    assert len(loaded_keys) == 0
    
    # Access existing key
    val = loader["exists"]
    assert val == "value"
    assert "exists" in loaded_keys
    
    # Access cached key (should not call loader again)
    val2 = loader["exists"]
    assert len(loaded_keys) == 1
    
    # Access missing key
    with pytest.raises(KeyError):
        _ = loader["missing"]
    
    # Access key that loader fails to return
    with pytest.raises(KeyError):
        _ = loader["will_load"]

def test_lazy_loader_setitem():
    loader = LazyLoader(lambda k: None)
    loader["new"] = "data"
    
    assert loader["new"] == "data"
    assert "new" in loader
