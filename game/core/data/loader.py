"""
Data loader for the Yukkuri Raising Game.

This module is responsible for loading all game data from the JSON files
in the `/data` directory. It validates the data against the defined schemas
and provides a simple interface to access the game content.
"""

import json
from pathlib import Path
from typing import Dict, Type

from game.core.data.schemas import YukkuriSchema, ItemSchema, BehaviorSchema


class GameData:
    """A container for all loaded game data."""
    def __init__(self):
        self.yukkuris: Dict[str, YukkuriSchema] = {}
        self.items: Dict[str, ItemSchema] = {}
        self.behaviors: Dict[str, BehaviorSchema] = {}
        self.localization: Dict[str, str] = {}


from typing import get_args, get_origin
import_types = ["Dict", "List", "Type"]


def _validate_schema(data: Dict, schema: Type[Dict], path: str = "") -> bool:
    """
    A simple schema validator based on TypedDict annotations.
    This is a basic implementation and does not handle nested types well.
    A more robust solution would use a library like jsonschema.
    """
    # Check for __annotations__ directly on the schema
    if not hasattr(schema, '__annotations__'):
        return True # Not a TypedDict, so we can't validate it further

    required_keys = getattr(schema, '__required_keys__', set(schema.__annotations__.keys()))

    for key, expected_type in schema.__annotations__.items():
        if key in required_keys and key not in data:
            raise ValueError(f"Missing required key at {path}{key}")

        if key not in data:
            continue # Skip validation for optional keys that are not present

        origin = get_origin(expected_type)
        args = get_args(expected_type)

        if origin is list and args:
            if not isinstance(data[key], list):
                raise TypeError(f"Expected a list for {path}{key}")
            for i, item in enumerate(data[key]):
                _validate_schema(item, args[0], path=f"{path}{key}[{i}].")

    return True


def load_game_data(data_dir: Path) -> GameData:
    """
    Loads all game data from the specified data directory.
    """
    game_data = GameData()

    # Load Yukkuris
    yukkuri_dir = data_dir / "yukkuris"
    for path in yukkuri_dir.glob("*.json"):
        with open(path, "r") as f:
            data = json.load(f)
            _validate_schema(data, YukkuriSchema)
            game_data.yukkuris[data["id"]] = data

    # Load Items
    item_dir = data_dir / "items"
    for path in item_dir.glob("*.json"):
        with open(path, "r") as f:
            data = json.load(f)
            _validate_schema(data, ItemSchema)
            game_data.items[data["id"]] = data

    # Load Behaviors
    behavior_dir = data_dir / "behaviors"
    for path in behavior_dir.glob("*.json"):
        with open(path, "r") as f:
            data = json.load(f)
            # Behaviors don't have an ID in the file, so we use the filename
            behavior_id = path.stem
            _validate_schema(data, BehaviorSchema)
            game_data.behaviors[behavior_id] = data

    # Load Localization
    localization_dir = data_dir / "localization"
    for path in localization_dir.glob("*.json"):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            game_data.localization.update(data)

    return game_data
