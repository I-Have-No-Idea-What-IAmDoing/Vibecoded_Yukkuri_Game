"""
Module defining the SettingsService.
"""
import msgspec
import os
from typing import Any
from pathlib import Path
from loguru import logger

class AudioSettings(msgspec.Struct):
    """
    Configuration settings for audio.

    Attributes:
        master_volume (float): Master volume level (0.0 to 1.0).
        bgm_volume (float): Background music volume level (0.0 to 1.0).
        sfx_volume (float): Sound effects volume level (0.0 to 1.0).
    """
    master_volume: float = 0.5
    bgm_volume: float = 0.5
    sfx_volume: float = 0.5

class WindowSettings(msgspec.Struct):
    """
    Configuration settings for the game window.

    Attributes:
        width (int): Window width in pixels.
        height (int): Window height in pixels.
        fullscreen (bool): Whether to run in fullscreen mode.
    """
    width: int = 1280
    height: int = 720
    fullscreen: bool = False

class UserSettings(msgspec.Struct):
    """
    Structure of the user settings file.

    Attributes:
        audio (AudioSettings): Audio settings.
        window (WindowSettings): Window settings.
    """
    audio: AudioSettings = msgspec.field(default_factory=AudioSettings)
    window: WindowSettings = msgspec.field(default_factory=WindowSettings)

class SettingsService:
    """
    Service responsible for loading and saving game settings.

    Attributes:
        settings_file (Path): Path to the settings file.
        settings (UserSettings): Current settings.
    """

    def __init__(self, settings_file: str = "data/user_settings.toml"):
        """
        Initializes the SettingsService.

        Args:
            settings_file (str): The path to the settings file.
        """
        self.settings_file = Path(settings_file)
        self.settings: UserSettings = UserSettings()
        self.load_settings()

    def load_settings(self) -> None:
        """
        Loads settings from the TOML file.

        Returns:
            None
        """
        if self.settings_file.exists():
            try:
                with open(self.settings_file, "rb") as f:
                    # Decode directly into UserSettings struct
                    self.settings = msgspec.toml.decode(f.read(), type=UserSettings)
                logger.info(f"Settings loaded from {self.settings_file}")
            except Exception as e:
                logger.error(f"Failed to load settings: {e}")
                # Fallback to default settings is handled by __init__ if load fails,
                # but since we already initialized self.settings, we might want to keep it or reset it?
                # If decode fails, self.settings remains as initialized (defaults).
        else:
            logger.info("Settings file not found, using defaults.")
            # Ensure directory exists if we are going to save later, or at least warn.
            # But we don't save here.

    def save_settings(self) -> None:
        """
        Saves the current settings to the TOML file.

        Returns:
            None
        """
        try:
            # Ensure directory exists
            if self.settings_file.parent:
                self.settings_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.settings_file, "wb") as f:
                f.write(msgspec.toml.encode(self.settings))
            logger.info(f"Settings saved to {self.settings_file}")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    def get(self, category: str, key: str) -> Any:
        """
        Retrieves a setting value.

        Args:
            category (str): The setting category (e.g., "audio", "window").
            key (str): The setting key.

        Returns:
            Any: The setting value, or None if not found.
        """
        try:
            cat = getattr(self.settings, category)
            return getattr(cat, key)
        except AttributeError:
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
        try:
            cat = getattr(self.settings, category)
            setattr(cat, key, value)
        except AttributeError:
            logger.error(f"Attempted to set invalid setting: {category}.{key}")
