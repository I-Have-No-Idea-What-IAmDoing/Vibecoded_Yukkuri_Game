import random
from typing import Dict, Any, Optional, List

class DialogueManager:
    def __init__(self, dialogue_data: List[Dict[str, Any]]) -> None:
        self.dialogue_lines: Dict[str, Dict[str, Any]] = {item['tag']: item for item in dialogue_data}
        self.cooldowns: Dict[str, float] = {tag: 0.0 for tag in self.dialogue_lines}

    def update(self, delta_time: float) -> None:
        """Updates all active cooldowns."""
        for tag in self.cooldowns:
            if self.cooldowns[tag] > 0:
                self.cooldowns[tag] -= delta_time

    def get_line(self, tag: str) -> Optional[str]:
        """Gets a random dialogue line for a given tag, respecting cooldowns."""
        if tag not in self.dialogue_lines:
            return None

        if self.cooldowns.get(tag, 0) > 0:
            return None # Still on cooldown

        dialogue_info = self.dialogue_lines[tag]
        cooldown_duration = dialogue_info.get('cooldown_secs', 10.0)
        self.cooldowns[tag] = cooldown_duration

        return random.choice(dialogue_info['lines'])
