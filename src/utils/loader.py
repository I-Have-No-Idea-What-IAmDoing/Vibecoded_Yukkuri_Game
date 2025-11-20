import tomllib
import os
from typing import Any, Dict

class Loader:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.configs: Dict[str, Any] = {}
        self.yukkuri_types: Dict[str, Any] = {}
        self.items: Dict[str, Any] = {}
        self.ai_actions: Dict[str, Any] = {}

    def load_all(self):
        self.configs = self._load_toml("config.toml")
        self.yukkuri_types = self._load_toml("yukkuri_types.toml").get("yukkuri", {})
        self.items = self._load_toml("items.toml").get("item", {})
        self.ai_actions = self._load_toml("ai_actions.toml").get("action", {})

        print(f"Loaded {len(self.yukkuri_types)} yukkuri types.")
        print(f"Loaded {len(self.items)} items.")
        print(f"Loaded {len(self.ai_actions)} AI actions.")

    def _load_toml(self, filename: str) -> Dict[str, Any]:
        filepath = os.path.join(self.data_dir, filename)
        try:
            with open(filepath, "rb") as f:
                return tomllib.load(f)
        except FileNotFoundError:
            print(f"Error: File {filename} not found in {self.data_dir}")
            return {}
        except tomllib.TOMLDecodeError as e:
            print(f"Error parsing {filename}: {e}")
            return {}

# Global loader instance
game_data = Loader()
