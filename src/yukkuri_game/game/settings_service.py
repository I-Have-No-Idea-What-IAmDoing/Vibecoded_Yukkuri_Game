"""
Module defining the SettingsService.
"""

from typing import Any
from loguru import logger

from ..engine.data_models import UserSettings
from ..engine.resource_manager import ResourceManager


class SettingsService:
    """
    Service responsible for loading and saving game settings.

    Attributes:
        settings_file (str): Path to the settings file.
        settings (UserSettings): The current settings.
        resource_manager (ResourceManager): The resource manager instance.
    """

    def __init__(
        self,
        resource_manager: ResourceManager | None = None,
        settings_file: str = "user_settings.toml",
    ):
        """
        Initializes the SettingsService.

        Args:
            resource_manager (ResourceManager, optional): The resource manager to use.
            settings_file (str): The path to the settings file relative to the data directory.
        """
        self.settings_file = settings_file
        self.resource_manager = resource_manager or ResourceManager()
        self.settings: UserSettings = UserSettings()
        self.load_settings()

    def load_settings(self) -> None:
        """
        Loads settings from the TOML file.

        Returns:
            None
        """
        loaded_settings = self.resource_manager.load_toml_model(
            self.settings_file, UserSettings
        )
        if loaded_settings:
            self.settings = loaded_settings
            logger.info(f"Settings loaded from {self.settings_file}")
        else:
            logger.info("Settings file not found or failed to load, using defaults.")
            self.settings = UserSettings()
            self.save_settings()  # Save defaults

    def save_settings(self) -> None:
        """
        Saves the current settings to the TOML file.

        Returns:
            None
        """
        if self.resource_manager.save_toml_model(self.settings_file, self.settings):
            logger.info(f"Settings saved to {self.settings_file}")
        else:
            logger.error("Failed to save settings.")

    def get(self, category: str, key: str) -> Any:
        """
        Retrieves a setting value.

        Args:
            category (str): The setting category (e.g., "audio", "window").
            key (str): The setting key.

        Returns:
            Any: The setting value.
        """
        if hasattr(self.settings, category):
            cat_obj = getattr(self.settings, category)
            if hasattr(cat_obj, key):
                return getattr(cat_obj, key)
        return None

    def set(self, category: str, key: str, value: Any) -> None:
        """
        Sets a setting value.

        Args:
            category (str): The setting category.
            key (str): The setting key.
            value (Any): The new value.

        Returns:
            None
        """
        if hasattr(self.settings, category):
            cat_obj = getattr(self.settings, category)
            if hasattr(cat_obj, key):
                setattr(cat_obj, key, value)
            else:
                logger.warning(
                    f"Setting key '{key}' not found in category '{category}'"
                )
        else:
            logger.warning(f"Setting category '{category}' not found")
