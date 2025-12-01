"""
Module for managing audio playback.
"""

import os
import sys
import pygame
from loguru import logger
from typing import Dict, Optional

class AudioManager:
    """
    Manages audio playback for the game, including sound effects and music.

    Attributes:
        enabled (bool): Whether audio is enabled (initialized successfully).
        sounds (Dict[str, pygame.mixer.Sound]): A dictionary mapping sound names to
            pygame.mixer.Sound objects.
        music (Optional[Any]): The current background music (not currently used).
        master_volume (float): The global volume level (0.0 to 1.0).
        bgm_volume (float): The background music volume level (0.0 to 1.0).
        sfx_volume (float): The sound effects volume level (0.0 to 1.0).
    """

    def __init__(self) -> None:
        """
        Initializes the AudioManager.

        Attempts to initialize the pygame mixer. If it fails, audio is disabled.
        """
        try:
            pygame.mixer.init()
            self.enabled = True
        except pygame.error as e:
            logger.warning(f"Audio initialization failed (likely no device): {e}")
            self.enabled = False

        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        self.music: Optional[Any] = None
        self.master_volume: float = 1.0
        self.bgm_volume: float = 1.0
        self.sfx_volume: float = 1.0

    def load_from_config(self, config_path: str = "data/sounds.toml") -> None:
        """
        Loads sounds from configuration or fallback.

        Args:
            config_path (str): Path to the sounds configuration file.
        """
        if os.path.exists(config_path):
            if sys.version_info >= (3, 11):
                import tomllib  # type: ignore
            else:
                try:
                    import tomli as tomllib  # type: ignore
                except ImportError:
                    tomllib = None

            if tomllib:
                try:
                    with open(config_path, "rb") as f:
                        sounds = tomllib.load(f)
                        for name, path in sounds.get("sounds", {}).items():
                            self.load_sound(name, path)
                except Exception as e:
                    logger.error(f"Failed to load sound config from {config_path}: {e}")
                    self._load_fallback_sounds()
            else:
                logger.warning("tomllib not available, falling back to default sounds.")
                self._load_fallback_sounds()
        else:
            self._load_fallback_sounds()

    def _load_fallback_sounds(self) -> None:
        """Loads fallback sounds if configuration fails."""
        defaults = {
            "click": "data/audio/click.wav",
            "place": "data/audio/place.wav",
            "cancel": "data/audio/cancel.wav",
            "sell": "data/audio/sell.wav",
            "train": "data/audio/train.wav",
            "eat": "data/audio/eat.wav",
            "cry": "data/audio/cry.wav"
        }
        for name, path in defaults.items():
            self.load_sound(name, path)

    def load_sound(self, name: str, filepath: str) -> None:
        """
        Loads a sound effect from a file.

        Args:
            name (str): The name to assign to the sound.
            filepath (str): The path to the sound file.
        """
        if not self.enabled:
            return

        if os.path.exists(filepath):
            try:
                self.sounds[name] = pygame.mixer.Sound(filepath)
                self._update_sound_volume(self.sounds[name])
            except Exception as e:
                logger.error(f"Failed to load sound {filepath}: {e}")

    def play_sound(self, name: str) -> None:
        """
        Plays a loaded sound effect.

        Args:
            name (str): The name of the sound to play.
        """
        if not self.enabled:
            return

        if name in self.sounds:
            self.sounds[name].play()

    def set_master_volume(self, volume: float) -> None:
        """
        Sets the master volume.

        Args:
            volume (float): The volume level between 0.0 and 1.0.
        """
        # Clamp volume
        self.master_volume = max(0.0, min(1.0, volume))
        self._update_all_volumes()

    def set_bgm_volume(self, volume: float) -> None:
        """
        Sets the background music volume.

        Args:
            volume (float): The volume level between 0.0 and 1.0.
        """
        self.bgm_volume = max(0.0, min(1.0, volume))
        if self.enabled and pygame.mixer.get_init():
             pygame.mixer.music.set_volume(self.master_volume * self.bgm_volume)

    def set_sfx_volume(self, volume: float) -> None:
        """
        Sets the sound effects volume.

        Args:
            volume (float): The volume level between 0.0 and 1.0.
        """
        self.sfx_volume = max(0.0, min(1.0, volume))
        self._update_all_volumes()

    def _update_sound_volume(self, sound: pygame.mixer.Sound) -> None:
        """
        Updates the volume of a single sound object.

        Args:
            sound (pygame.mixer.Sound): The sound object to update.
        """
        sound.set_volume(self.master_volume * self.sfx_volume)

    def _update_all_volumes(self) -> None:
        """
        Updates volumes for all loaded sounds and music.
        """
        if not self.enabled:
            return

        for s in self.sounds.values():
            self._update_sound_volume(s)

        if pygame.mixer.get_init():
             pygame.mixer.music.set_volume(self.master_volume * self.bgm_volume)

    def set_volume(self, volume: float) -> None:
        """
        Sets the global volume for all sounds (Legacy support).
        Maps to master volume.

        Args:
            volume (float): The volume level between 0.0 (mute) and 1.0 (max).
        """
        self.set_master_volume(volume)
