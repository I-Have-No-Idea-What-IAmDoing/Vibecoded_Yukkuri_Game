"""
Game Driver for automated testing.
"""
import random
import time
import pygame
import os
from typing import Generator, Any, Callable, Union, List
from dataclasses import dataclass

# --- Predicates & Commands ---

@dataclass
class WaitUntil:
    """Waits until a predicate returns True."""
    predicate: Callable[[], bool]
    timeout: float = 10.0
    description: str = "condition"

@dataclass
class WaitFrames:
    """Waits for a specific number of frames."""
    frames: int

@dataclass
class InjectInput:
    """Wraps a list of input events to inject."""
    events: List[pygame.event.Event]

@dataclass
class Screenshot:
    """Command to take a screenshot."""
    filename: str

# --- Input Helpers ---

def Click(x: int, y: int) -> InjectInput:
    """Creates a full click (Down + Up) event at x, y."""
    return InjectInput([
        pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (x, y), "button": 1}),
        pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": (x, y), "button": 1})
    ])

def KeyPress(key: int) -> InjectInput:
    """Creates a key press (Down + Up) event."""
    return InjectInput([
        pygame.event.Event(pygame.KEYDOWN, {"key": key}),
        pygame.event.Event(pygame.KEYUP, {"key": key})
    ])

# --- Driver ---

class GameDriver:
    """
    Controls a YukkuriGame instance for deterministic headless testing.
    """
    def __init__(self, game_instance, fixed_dt: float = 1.0/60.0):
        self.game = game_instance
        self.fixed_dt = fixed_dt
        self.simulated_time = 0.0
        self.frame_count = 0
        self._scenario_deadline = None

    def seed_rng(self, seed: int = 42):
        """Seeds random number generators for determinism."""
        random.seed(seed)
        try:
            import numpy as np
            np.random.seed(seed)
        except ImportError:
            pass

    def setup(self):
        """Sets up the game instance."""
        self.seed_rng()
        if not self.game.headless:
             self.game.set_headless(True)
        self.game.setup()

    def cleanup(self):
        """Cleans up the game instance."""
        self.game.quit()

    def run_scenario(self, scenario_gen: Generator[Any, None, None], timeout: float = 10.0):
        """
        Runs a test scenario generator.
        """
        self.setup()
        start_sim_time = self.simulated_time
        self._scenario_deadline = start_sim_time + timeout

        try:
            iterator = iter(scenario_gen)
            while True:
                try:
                    step = next(iterator)
                except StopIteration:
                    break

                self._check_global_timeout()

                if isinstance(step, WaitUntil):
                    self._wait_until(step)
                elif isinstance(step, WaitFrames):
                    self._wait_frames(step)
                elif isinstance(step, InjectInput):
                    for event in step.events:
                        pygame.event.post(event)
                elif isinstance(step, Screenshot):
                    self.save_screenshot(step.filename)
                elif callable(step):
                    step()
                else:
                     pass
        except Exception as e:
            self.save_screenshot(f"screenshots/failure_{self.frame_count}.png")
            raise e
        finally:
            self._scenario_deadline = None

    def _tick(self):
        """Advances the game by one fixed time step."""
        # 1. Handle Events
        if hasattr(self.game, "handle_events"):
            self.game.handle_events()
        else:
            pygame.event.pump()

        # 2. Update Game State
        self.game.tick(self.fixed_dt)

        self.simulated_time += self.fixed_dt
        self.frame_count += 1
        self._check_global_timeout()

    def _check_global_timeout(self):
        if self._scenario_deadline is not None and self.simulated_time > self._scenario_deadline:
             raise TimeoutError("Scenario exceeded global simulated time limit")

    def _wait_frames(self, condition: WaitFrames):
        for _ in range(condition.frames):
            self._tick()

    def _wait_until(self, condition: WaitUntil):
        start_time = self.simulated_time
        timeout = condition.timeout

        while not condition.predicate():
            if self.simulated_time - start_time > timeout:
                raise TimeoutError(f"Timed out waiting for: {condition.description}")
            self._tick()

    def save_screenshot(self, filename: str):
        """Saves the current screen state to a file."""
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        if hasattr(self.game, "init_render_system_headless"):
             self.game.init_render_system_headless()

        # Force a render to the surface (logic loop doesn't do it)
        if hasattr(self.game, "render"):
             self.game.render()

        pygame.image.save(self.game.screen, filename)
