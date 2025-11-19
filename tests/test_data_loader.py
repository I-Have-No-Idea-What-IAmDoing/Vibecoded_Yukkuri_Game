"""
Tests for the data loader and schema validation.
"""

import json
import pytest
from pathlib import Path

from game.core.data.loader import load_game_data


@pytest.fixture
def temp_data_dir(tmp_path: Path) -> Path:
    """Creates a temporary data directory for testing."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "yukkuris").mkdir()
    (data_dir / "items").mkdir()
    (data_dir / "behaviors").mkdir()
    (data_dir / "localization").mkdir()
    return data_dir


def test_load_game_data_success(temp_data_dir: Path):
    """
    Tests that the data loader can successfully load valid game data.
    """
    # Create sample data files
    (temp_data_dir / "yukkuris" / "akari.json").write_text(json.dumps({
        "id": "akari", "display_name_key": "yukkuri.akari",
        "base_needs": {"hunger": 0.2}, "personality": {}, "ai_profile": "default"
    }))
    (temp_data_dir / "items" / "bed.json").write_text(json.dumps({
        "id": "bed", "display_name_key": "item.bed",
        "size": {"w": 2, "h": 1}, "tags": [], "effects": {}
    }))
    (temp_data_dir / "behaviors" / "default.json").write_text(json.dumps({
        "actions": []
    }))
    (temp_data_dir / "localization" / "en.json").write_text(json.dumps({
        "yukkuri.akari": "Akari"
    }))

    game_data = load_game_data(temp_data_dir)

    assert "akari" in game_data.yukkuris
    assert "bed" in game_data.items
    assert "default" in game_data.behaviors
    assert "yukkuri.akari" in game_data.localization
    assert game_data.localization["yukkuri.akari"] == "Akari"


def test_load_game_data_validation_error(temp_data_dir: Path):
    """
    Tests that the data loader raises a ValueError for malformed data.
    """
    # Create a yukkuri file with a missing required key
    (temp_data_dir / "yukkuris" / "malformed.json").write_text(json.dumps({
        "id": "malformed",
        # "display_name_key" is missing
        "base_needs": {},
        "personality": {},
        "ai_profile": "default"
    }))

    with pytest.raises(ValueError, match="Missing required key at display_name_key"):
        load_game_data(temp_data_dir)
