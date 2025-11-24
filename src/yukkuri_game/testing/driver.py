"""
Game Driver for automated testing.
"""
import random
import time
import pygame
from typing import Generator, Any

from .predicates import WaitUntil, WaitFrames, InjectInput

class GameDriver:
    """
    Controls a YukkuriGame instance for deterministic headless testing.
    """
    def __init__(self, game_instance, fixed_dt: float = 1.0/60.0):
        self.game = game_instance
        self.fixed_dt = fixed_dt
        self.simulated_time = 0.0
        self.frame_count = 0
        # Default fallback timeout if condition doesn't specify one
        self.default_timeout = 10.0

    def seed_rng(self, seed: int = 42):
        """Seeds random number generators for determinism."""
        random.seed(seed)
        try:
            import numpy as np
            np.random.seed(seed)
        except ImportError:
            pass
        # If there are other RNGs, seed them here

    def setup(self):
        """Sets up the game instance."""
        # Requirement 4: Explicitly seed RNG before initialization
        self.seed_rng()

        # Ensure headless mode is set if not already
        if not self.game.headless:
             self.game.set_headless(True)
        self.game.setup()

    def cleanup(self):
        """
        Cleans up the game instance.
        """
        self.game.quit()

    def run_scenario(self, scenario_gen: Generator[Any, None, None]):
        """
        Runs a test scenario generator.
        """
        self.setup()

        try:
            for step in scenario_gen:
                if isinstance(step, WaitUntil):
                    self._wait_until(step)
                elif isinstance(step, WaitFrames):
                    self._wait_frames(step)
                elif isinstance(step, InjectInput):
                    # Execute the injection callable
                    step.event_injector()
                elif callable(step): # Support raw functions as actions
                    step()
                else:
                     # Maybe it's a direct command or assertion?
                     pass
        finally:
            self.cleanup()

    def _tick(self):
        """Advances the game by one fixed time step."""
        # We need to manually drive the loop

        # 1. Handle Events (Process injected events)
        # Ensure queue is pumped
        pygame.event.pump()

        if hasattr(self.game, "handle_events"):
            self.game.handle_events()

        # 2. Update Game State
        # Ensure simulated time is updated in time service if it exists
        self.game.tick(self.fixed_dt)

        self.simulated_time += self.fixed_dt
        self.frame_count += 1

    def _wait_frames(self, condition: WaitFrames):
        for _ in range(condition.frames):
            self._tick()

    def _wait_until(self, condition: WaitUntil):
        start_time = self.simulated_time
        timeout = condition.timeout if condition.timeout is not None else self.default_timeout

        while not condition.predicate():
            if self.simulated_time - start_time > timeout:
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
