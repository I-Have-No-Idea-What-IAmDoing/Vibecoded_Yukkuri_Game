import pygame
from loguru import logger
import os

class AudioManager:
    def __init__(self):
        try:
            pygame.mixer.init()
            self.enabled = True
        except pygame.error as e:
            logger.warning(f"Audio initialization failed (likely no device): {e}")
            self.enabled = False

        self.sounds = {}
        self.music = None
        self.volume = 0.5

    def load_sound(self, name, filepath):
        if not self.enabled:
            return

        if os.path.exists(filepath):
            try:
                self.sounds[name] = pygame.mixer.Sound(filepath)
                self.sounds[name].set_volume(self.volume)
            except Exception as e:
                logger.error(f"Failed to load sound {filepath}: {e}")

    def play_sound(self, name):
        if not self.enabled:
            return

        if name in self.sounds:
            self.sounds[name].play()

    def set_volume(self, volume):
        self.volume = max(0.0, min(1.0, volume))
        for s in self.sounds.values():
            s.set_volume(self.volume)
