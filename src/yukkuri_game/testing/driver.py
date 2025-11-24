"""
Game Driver for automated testing.
"""
import random
import time
from typing import Generator, Any
import pygame
import numpy as np

from .predicates import WaitCondition, WaitUntil, WaitFrames, Action, InjectInput

class GameDriver:
    """
    Controls the YukkuriGame instance for testing.
    """
    def __init__(self, game_instance, fixed_dt: float = 1.0/60.0):
        self.game = game_instance
        self.fixed_dt = fixed_dt
        self.simulated_time = 0.0
        self.frame_count = 0
        self.timeout_limit = 10.0 # Default 10 seconds timeout for WaitUntil

    def seed_rng(self, seed: int = 42):
        """Seeds random number generators for determinism."""
        random.seed(seed)
        np.random.seed(seed)
        # If there are other RNGs, seed them here

    def setup(self):
        """Sets up the game instance."""
        # Ensure headless mode is set if not already
        self.game.set_headless(True)
        self.game.setup()

    def run_scenario(self, scenario_gen: Generator[Any, None, None]):
        """
        Runs a test scenario generator.
        """
        self.setup()

        for step in scenario_gen:
            if isinstance(step, WaitUntil):
                self._wait_until(step)
            elif isinstance(step, WaitFrames):
                self._wait_frames(step)
            elif isinstance(step, InjectInput):
                step.event_injector()
                # Process events immediately after injection?
                # Or wait for next tick.
                # Usually input is processed at start of tick.
            elif callable(step): # Support raw functions as actions
                step()
            else:
                 # Maybe it's a direct command or assertion?
                 pass

            # After each step (or during waits), we might want to tick once?
            # No, waits handle ticking. Actions happen instantly between ticks usually.

    def _tick(self):
        """Advances the game by one fixed time step."""
        # We need to manually drive the loop

        # 1. Handle Events (Process injected events)
        self.game.handle_events()

        # 2. Update Game State
        # Ensure simulated time is updated in time service if it exists
        # Although YukkuriGame.tick updates gm.time_elapsed, we can also ensure sync here if needed.
        self.game.tick(self.fixed_dt)

        # 3. Render (Optional, for screenshots or verifying render logic)
        # if needed: self.game.draw()
        # But draw() flips display, which we might not want in dummy mode?
        # headless mode usually skips draw() in main loop, but we can call render_world manually if needed.

        self.simulated_time += self.fixed_dt
        self.frame_count += 1

    def _wait_frames(self, condition: WaitFrames):
        for _ in range(condition.frames):
            self._tick()

    def _wait_until(self, condition: WaitUntil):
        start_time = self.simulated_time
        while not condition.predicate():
            if self.simulated_time - start_time > condition.timeout:
                raise TimeoutError(f"Timed out waiting for: {condition.description}")

            self._tick()

    def save_screenshot(self, filename: str):
        """Saves the current screen state to a file."""
        import os
        # Ensure directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        # Need to ensure something was rendered to the surface
        if self.game.headless:
             # In headless mode, we might not be drawing to screen.
             # We might need to force a render to the surface.
             self.game.render_world()
             # And ui
             self.game.ui_manager.draw_ui(self.game.screen)

        pygame.image.save(self.game.screen, filename)
