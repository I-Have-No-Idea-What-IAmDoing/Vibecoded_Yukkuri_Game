import json
from typing import Dict, Any

class Config:
    def __init__(self, filepath: str = "settings.json"):
        with open(filepath, 'r') as f:
            self.settings: Dict[str, Any] = json.load(f)

    def get(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)
