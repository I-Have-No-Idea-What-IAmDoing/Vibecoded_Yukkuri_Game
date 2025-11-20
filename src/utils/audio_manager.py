import pygame
import os
from typing import Dict

class AudioManager:
    def __init__(self, config: Dict = None):
        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        self.music_volume = 0.5
        self.sfx_volume = 0.5

        if config:
            self.music_volume = config.get("music_volume", 0.5)
            self.sfx_volume = config.get("sfx_volume", 0.5)

        self.initialized = False
        try:
            pygame.mixer.init()
            self.initialized = True
            print("Audio initialized.")
        except pygame.error as e:
            print(f"Audio initialization failed: {e}")

    def load_sound(self, name: str, filepath: str):
        if not self.initialized or not os.path.exists(filepath):
            return
        try:
            sound = pygame.mixer.Sound(filepath)
            sound.set_volume(self.sfx_volume)
            self.sounds[name] = sound
        except pygame.error as e:
            print(f"Failed to load sound {name}: {e}")

    def play_sound(self, name: str):
        if not self.initialized: return
        if name in self.sounds:
            self.sounds[name].play()
        else:
            # Placeholder logging for development
            # print(f"Playing sound: {name}")
            pass

    def play_music(self, filepath: str, loops: int = -1):
        if not self.initialized or not os.path.exists(filepath):
            # print(f"Playing music: {filepath}")
            return
        try:
            pygame.mixer.music.load(filepath)
            pygame.mixer.music.set_volume(self.music_volume)
            pygame.mixer.music.play(loops)
        except pygame.error as e:
            print(f"Failed to play music {filepath}: {e}")

    def stop_music(self):
        if self.initialized:
            pygame.mixer.music.stop()
