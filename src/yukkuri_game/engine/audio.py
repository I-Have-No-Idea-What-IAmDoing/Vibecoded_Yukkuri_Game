"""
Module for managing audio playback.
"""

import os
import sys
import pygame
from loguru import logger
from typing import Any


from collections import OrderedDict

class AudioManager:
    """
    Manages audio playback for the game, including sound effects and music.

    Attributes:
        enabled (bool): Whether audio is enabled (initialized successfully).
        sounds (OrderedDict[str, pygame.mixer.Sound]): A cache of loaded sound objects.
        sound_cache_limit (int): Maximum number of sound effects in memory.
        preloaded_sounds (Set[str]): Sounds that should never be evicted from the cache.
        music (Optional[Any]): The current background music (not currently used).
        master_volume (float): The global volume level (0.0 to 1.0).
        bgm_volume (float): The background music volume level (0.0 to 1.0).
        sfx_volume (float): The sound effects volume level (0.0 to 1.0).
    """

    def __init__(self, sound_cache_limit: int = 50) -> None:
        """
        Initializes the AudioManager.

        Attempts to initialize the pygame mixer. If it fails, audio is disabled.

        Args:
            sound_cache_limit (int): Max number of cached sounds. Defaults to 50.
        """
        try:
            # Frequency, size (16bit), channels (2), buffer size
            # 44100 is standard. -16 means 16-bit unsigned (or signed? usually signed in Pygame defaults)
            # Default is usually fine, but explicit init helps consistency.
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            self.enabled = True
        except pygame.error as e:
            logger.warning(f"Audio initialization failed (likely no device): {e}")
            self.enabled = False

        self.sounds: OrderedDict[str, pygame.mixer.Sound] = OrderedDict()
        self.sound_cache_limit = sound_cache_limit
        self.preloaded_sounds: set[str] = set()
        
        self.music: Any | None = None
        self.master_volume: float = 1.0
        self.bgm_volume: float = 1.0
        self.sfx_volume: float = 1.0

    def load_from_config(self, config_path: str = "data/sounds.toml") -> None:
        """
        Loads sounds from configuration or fallback.

        Args:
            config_path (str): Path to the sounds configuration file.

        Returns:
            None
        """
        if os.path.exists(config_path):
            if sys.version_info >= (3, 11):
                import tomllib
            else:
                try:
                    import tomli as tomllib
                except ImportError:
                    tomllib = None

            if tomllib:
                try:
                    with open(config_path, "rb") as f:
                        sounds = tomllib.load(f)
                        for name, path in sounds.get("sounds", {}).items():
                            # Config loads are considered "normal" loads, but arguably could be preloads?
                            # For now, treat them as normal LRU candidates unless explicitly preloaded.
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
        """
        Loads fallback sounds if configuration fails.

        Returns:
            None
        """
        defaults = {
            "click": "data/audio/click.wav",
            "place": "data/audio/place.wav",
            "cancel": "data/audio/cancel.wav",
            "sell": "data/audio/sell.wav",
            "train": "data/audio/train.wav",
            "eat": "data/audio/eat.wav",
            "cry": "data/audio/cry.wav",
        }
        for name, path in defaults.items():
            self.preload_sound(name, path)

    def preload_sound(self, name: str, filepath: str) -> None:
        """
        Loads a sound and safeguards it from eviction.

        Args:
            name (str): Name of the sound.
            filepath (str): Path to the file.
        """
        if not self.enabled:
            return
            
        self.load_sound(name, filepath)
        self.preloaded_sounds.add(name)

    def load_sound(self, name: str, filepath: str) -> None:
        """
        Loads a sound effect from a file into the LRU cache.

        Args:
            name (str): The name to assign to the sound.
            filepath (str): The path to the sound file.

        Returns:
            None
        """
        if not self.enabled:
            return

        if name in self.sounds:
            # Cache hit: move to end (Most Recently Used)
            self.sounds.move_to_end(name)
            return

        # Cache miss: Load from disk
        if os.path.exists(filepath):
            try:
                # Enforce cache limit before loading new item
                self._ensure_cache_space()
                
                sound = pygame.mixer.Sound(filepath)
                self.sounds[name] = sound
                self._update_sound_volume(sound)
            except Exception as e:
                logger.error(f"Failed to load sound {filepath}: {e}")
        else:
            # logger.warning(f"Sound file not found: {filepath}")
            pass

    def _ensure_cache_space(self) -> None:
        """
        Evicts the oldest non-preloaded sound if cache limit is reached.
        """
        while len(self.sounds) >= self.sound_cache_limit:
            # We need to find the oldest item that is NOT in preloaded_sounds.
            # OrderedDict doesn't support easy "pop first item that matches condition".
            # So we iterate. Iterating a dictionary is roughly in insertion order (LRU at start).
            
            evicted_key = None
            for key in self.sounds:
                if key not in self.preloaded_sounds:
                    evicted_key = key
                    break
            
            if evicted_key:
                # logger.debug(f"Audio Cache Full. Evicting: {evicted_key}")
                self.sounds.pop(evicted_key)
            else:
                # Edge case: All sounds are preloaded. We cannot evict anything.
                # Just break and allow the cache to grow slightly beyond limit.
                # logger.warning("Audio Cache limit reached, but all items are preloaded. Expanding cache.")
                break

    def play_sound(self, name: str) -> None:
        """
        Plays a loaded sound effect.

        Args:
            name (str): The name of the sound to play.

        Returns:
            None
        """
        if not self.enabled:
            return

        if name in self.sounds:
            # Mark as recently used
            self.sounds.move_to_end(name)
            self.sounds[name].play()
        else:
            # Optional: try to auto-load if we know the path? 
            # For now, assuming explicit load/preload was done.
            # logger.warning(f"Sound '{name}' not found in cache.")
            pass

    def play_music(self, filepath: str, loops: int = -1, fade_ms: int = 1000) -> None:
        """
        Streams and plays background music from a file.

        Args:
            filepath (str): Path to the music file.
            loops (int): Number of times to loop (-1 for infinite).
            fade_ms (int): Fade-in duration in milliseconds.
        """
        if not self.enabled:
            return

        if os.path.exists(filepath):
            try:
                # Stop current music with fadeout? Default stop is abrupt.
                # pygame.mixer.music.stop() 
                pygame.mixer.music.load(filepath)
                pygame.mixer.music.set_volume(self.master_volume * self.bgm_volume)
                pygame.mixer.music.play(loops=loops, fade_ms=fade_ms)
            except Exception as e:
                logger.error(f"Failed to stream music {filepath}: {e}")
        else:
            logger.error(f"Music file not found: {filepath}")

    def set_master_volume(self, volume: float) -> None:
        """
        Sets the master volume.

        Args:
            volume (float): The volume level between 0.0 and 1.0.

        Returns:
            None
        """
        # Clamp volume
        self.master_volume = max(0.0, min(1.0, volume))
        self._update_all_volumes()

    def set_bgm_volume(self, volume: float) -> None:
        """
        Sets the background music volume.

        Args:
            volume (float): The volume level between 0.0 and 1.0.

        Returns:
            None
        """
        self.bgm_volume = max(0.0, min(1.0, volume))
        if self.enabled and pygame.mixer.get_init():
            try:
                pygame.mixer.music.set_volume(self.master_volume * self.bgm_volume)
            except pygame.error:
                pass

    def set_sfx_volume(self, volume: float) -> None:
        """
        Sets the sound effects volume.

        Args:
            volume (float): The volume level between 0.0 and 1.0.

        Returns:
            None
        """
        self.sfx_volume = max(0.0, min(1.0, volume))
        self._update_all_volumes()

    def _update_sound_volume(self, sound: pygame.mixer.Sound) -> None:
        """
        Updates the volume of a single sound object.

        Args:
            sound (pygame.mixer.Sound): The sound object to update.

        Returns:
            None
        """
        sound.set_volume(self.master_volume * self.sfx_volume)

    def _update_all_volumes(self) -> None:
        """
        Updates volumes for all loaded sounds and music.

        Returns:
            None
        """
        if not self.enabled:
            return

        for s in self.sounds.values():
            self._update_sound_volume(s)

        if pygame.mixer.get_init():
            try:
                pygame.mixer.music.set_volume(self.master_volume * self.bgm_volume)
            except pygame.error:
                pass

    def set_volume(self, volume: float) -> None:
        """
        Sets the global volume for all sounds (Legacy support).
        Maps to master volume.

        Args:
            volume (float): The volume level between 0.0 (mute) and 1.0 (max).

        Returns:
            None
        """
        self.set_master_volume(volume)

    def clear(self) -> None:
        """
        Stops all playback and clears loaded sounds to free memory.
        Retains preloaded sounds.
        """
        if not self.enabled:
            return

        pygame.mixer.stop()
        
        # Identify non-preloaded keys to remove
        # We modify the dict, so we can't iterate it directly while popping
        keys_to_remove = [k for k in self.sounds if k not in self.preloaded_sounds]
        
        for k in keys_to_remove:
            self.sounds.pop(k)

        # Stop music as well
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
