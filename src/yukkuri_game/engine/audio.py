import pygame
from loguru import logger
import os

class AudioManager:
    """
    Manages audio playback for the game, including sound effects and music.

    Attributes:
        enabled (bool): Whether audio is enabled (initialized successfully).
        sounds (dict[str, pygame.mixer.Sound]): A dictionary mapping sound names to pygame.mixer.Sound objects.
        music (pygame.mixer.Music): The current background music (not currently used).
        volume (float): The global volume level (0.0 to 1.0).
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

        self.sounds: dict[str, pygame.mixer.Sound] = {}
        self.music = None
        self.master_volume = 1.0
        self.bgm_volume = 1.0
        self.sfx_volume = 1.0

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
        self.master_volume = max(0.0, min(1.0, volume))
        self._update_all_volumes()

    def set_bgm_volume(self, volume: float) -> None:
        """
        Sets the background music volume.

        Args:
            volume (float): The volume level between 0.0 and 1.0.
        """
        self.bgm_volume = max(0.0, min(1.0, volume))
        if self.music:
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
