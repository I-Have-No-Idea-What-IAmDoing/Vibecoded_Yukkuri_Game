"""
A simple localization system.
"""
from typing import Dict

from game.core.data.loader import GameData


class Localization:
    """Provides a simple interface for string localization."""

    def __init__(self, game_data: GameData):
        self._strings: Dict[str, str] = game_data.localization

    def get(self, key: str, default: str = "") -> str:
        """
        Gets a localized string for the given key.

        :param key: The key of the string to retrieve.
        :param default: The default value to return if the key is not found.
        :return: The localized string.
        """
        return self._strings.get(key, default or f"<{key}>")
