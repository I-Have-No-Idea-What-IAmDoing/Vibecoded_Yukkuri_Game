import json
from pathlib import Path
from typing import List, Dict, Any, Optional

class DataLoader:
    def __init__(self, data_path: str = "content/data") -> None:
        self.data_path: Path = Path(data_path)
        self.agent_archetypes: List[Dict[str, Any]] = self._load_json("agent_archetypes.json")
        self.item_definitions: List[Dict[str, Any]] = self._load_json("item_definitions.json")
        self.action_templates: List[Dict[str, Any]] = self._load_json("action_templates.json")
        self.dialogue_lines: List[Dict[str, Any]] = self._load_json("dialogue_lines.json")
        self.room: Dict[str, Any] = self._load_json("room.json")

    def _load_json(self, filename: str) -> Any:
        with open(self.data_path / filename, "r") as f:
            return json.load(f)

    def get_agent_archetype(self, archetype_id: str) -> Optional[Dict[str, Any]]:
        for archetype in self.agent_archetypes:
            if archetype["id"] == archetype_id:
                return archetype
        return None

    def get_item_definition(self, item_id: str) -> Optional[Dict[str, Any]]:
        for item in self.item_definitions:
            if item["id"] == item_id:
                return item
        return None

    def get_action_template(self, action_name: str) -> Optional[Dict[str, Any]]:
        for action in self.action_templates:
            if action["name"] == action_name:
                return action
        return None
