import json
import os
import copy
from typing import Dict, Any
from loguru import logger

class SettingsService:
    """
    Service responsible for loading and saving game settings.

    Attributes:
        settings_file (str): Path to the settings file.
        settings (Dict[str, Any]): Dictionary containing current settings.
    """
    DEFAULT_SETTINGS = {
        "audio": {
            "master_volume": 0.5,
            "bgm_volume": 0.5,
            "sfx_volume": 0.5
        },
        "window": {
            "width": 1280,
            "height": 720,
            "fullscreen": False
        }
    }

    def __init__(self, settings_file: str = "user_settings.json"):
        """
        Initializes the SettingsService.

        Args:
            settings_file (str): The path to the settings file.
        """
        self.settings_file = settings_file
        self.settings = copy.deepcopy(self.DEFAULT_SETTINGS)
        self.load_settings()

    def load_settings(self) -> None:
        """
        Loads settings from the JSON file.
        """
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r") as f:
                    loaded_settings = json.load(f)
                    # Merge loaded settings with defaults to handle missing keys
                    self._merge_settings(self.settings, loaded_settings)
                logger.info(f"Settings loaded from {self.settings_file}")
            except Exception as e:
                logger.error(f"Failed to load settings: {e}")
        else:
            logger.info("Settings file not found, using defaults.")

    def save_settings(self) -> None:
        """
        Saves the current settings to the JSON file.
        """
        try:
            with open(self.settings_file, "w") as f:
                json.dump(self.settings, f, indent=4)
            logger.info(f"Settings saved to {self.settings_file}")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    def _merge_settings(self, current: Dict[str, Any], new: Dict[str, Any]) -> None:
        """
        Recursively merges new settings into current settings.
        """
        for key, value in new.items():
            if isinstance(value, dict) and key in current and isinstance(current[key], dict):
                self._merge_settings(current[key], value)
            else:
                current[key] = value

    def get(self, category: str, key: str) -> Any:
        """
        Retrieves a setting value.

        Args:
            category (str): The setting category (e.g., "audio", "window").
            key (str): The setting key.

        Returns:
            Any: The setting value.
        """
        return self.settings.get(category, {}).get(key)

    def set(self, category: str, key: str, value: Any) -> None:
        """
        Sets a setting value.

        Args:
            category (str): The setting category.
            key (str): The setting key.
            value (Any): The new value.
        """
        if category not in self.settings:
            self.settings[category] = {}
        self.settings[category][key] = value
