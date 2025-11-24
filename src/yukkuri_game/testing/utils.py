import pygame
from typing import Callable
from abc import ABC, abstractmethod

class WaitCondition(ABC):
    @abstractmethod
    def check(self, driver) -> bool:
        pass

class WaitFrames(WaitCondition):
    def __init__(self, frames: int):
        self.frames = frames
        self.target_frame = None

    def check(self, driver) -> bool:
        if self.target_frame is None:
            self.target_frame = driver.frame_count + self.frames
        return driver.frame_count >= self.target_frame

class WaitUntil(WaitCondition):
    def __init__(self, predicate: Callable[[], bool]):
        self.predicate = predicate

    def check(self, driver) -> bool:
        return self.predicate()

class InjectInput(ABC):
    @abstractmethod
    def inject(self):
        pass

class Click(InjectInput):
    def __init__(self, x: int, y: int, button: int = 1):
        self.x = x
        self.y = y
        self.button = button

    def inject(self):
        evt_down = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (self.x, self.y), "button": self.button})
        evt_up = pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": (self.x, self.y), "button": self.button})
        pygame.event.post(evt_down)
        pygame.event.post(evt_up)

class KeyPress(InjectInput):
    def __init__(self, key: int):
        self.key = key

    def inject(self):
        evt_down = pygame.event.Event(pygame.KEYDOWN, {"key": self.key})
        evt_up = pygame.event.Event(pygame.KEYUP, {"key": self.key})
        pygame.event.post(evt_down)
        pygame.event.post(evt_up)
