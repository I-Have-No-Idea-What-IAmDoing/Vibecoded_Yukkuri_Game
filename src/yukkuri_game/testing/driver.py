"""
Game Driver for automated testing.
"""
import random
import time
from typing import Generator, Any, Optional
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

        # Determinism: Seed RNGs
        self.seed_rng()

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

    def cleanup(self):
        """
        Cleans up the game environment.
        Call this after running tests to close the Pygame window/context.
        """
        if pygame.get_init():
            pygame.quit()

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
                # Input is injected immediately; it will be processed in the next _tick()
            elif callable(step): # Support raw functions as actions
                step()
            else:
                 pass

    def _tick(self):
        """Advances the game by one fixed time step."""
        # We need to manually drive the loop

        # 1. Pump Events (Process injected events)
        # We call game.handle_events() to process SDL queue into game state
        self.game.handle_events()

        # 2. Update Game State
        self.game.tick(self.fixed_dt)

        self.simulated_time += self.fixed_dt
        self.frame_count += 1

    def _wait_frames(self, condition: WaitFrames):
        """Advances the simulation for a specific number of frames."""
        target_frame = self.frame_count + condition.frames
        while self.frame_count < target_frame:
            self._tick()

    def _wait_until(self, condition: WaitUntil):
        start_time = self.simulated_time

        # Use condition specific timeout or fall back to driver default
        timeout = condition.timeout if condition.timeout is not None else self.timeout_limit

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
