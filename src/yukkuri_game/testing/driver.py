import pygame
import random
import numpy as np
from unittest.mock import patch
from typing import Generator, Any
from .utils import WaitFrames, WaitUntil, InjectInput

class GameDriver:
    """
    Controls the YukkuriGame instance for testing using a deterministic loop.
    """
    def __init__(self, game_instance, fixed_dt: float = 1.0/60.0, render_enabled: bool = False, timeout: float = 10.0):
        self.game = game_instance
        self.fixed_dt = fixed_dt
        self.simulated_time = 0.0
        self.frame_count = 0
        self.timeout_limit = timeout
        self.render_enabled = render_enabled

    def seed_rng(self, seed: int = 42):
        """Seeds random number generators for determinism."""
        random.seed(seed)
        np.random.seed(seed)

    def setup(self):
        """Sets up the game instance."""
        # If render_enabled is True, we tell the game it's NOT headless
        # so it initializes visual systems for screenshot verification.
        # SDL_VIDEODRIVER=dummy handles the lack of a physical window.
        if self.render_enabled:
            self.game.set_headless(False)
        else:
            self.game.set_headless(True)

        self.game.setup()

    def _tick_game(self):
        """Advances the game by one fixed timestep."""
        # 1. Process events (including injected ones)
        # We rely on the game's internal event handling or call it explicitly
        if hasattr(self.game, 'handle_events'):
            self.game.handle_events()
        else:
            pygame.event.pump()

        # 2. Update game logic
        self.game.tick(self.fixed_dt)

        # 3. Render (optional, for screenshots)
        if self.render_enabled and hasattr(self.game, 'render_world'):
            # Use render_world as per YukkuriGame implementation
            # Also might want to trigger UI draw?
            # YukkuriGame.draw() calls render_world and ui_manager.draw_ui
            pass

        self.simulated_time += self.fixed_dt
        self.frame_count += 1

    def run_scenario(self, scenario_gen: Generator[Any, None, None]):
        """
        Executes a scenario generator. Enforces a mocked time environment.
        """
        # Mock time.time and pygame.time.get_ticks to ensure strict determinism based on simulated ticks
        with patch('time.time', side_effect=lambda: self.simulated_time), \
             patch('pygame.time.get_ticks', side_effect=lambda: int(self.simulated_time * 1000)):
            self.setup() # Ensure setup is called
            iterator = iter(scenario_gen)
            active_wait = None

            while True:
                # Enforce global timeout
                if self.simulated_time > self.timeout_limit:
                    raise TimeoutError(f"Scenario timed out after {self.simulated_time:.2f}s")

                # Check active wait condition
                if active_wait:
                    if active_wait.check(self):
                        active_wait = None
                    else:
                        self._tick_game()
                        continue

                # Get next command
                try:
                    command = next(iterator)
                except StopIteration:
                    break

                # Process Command
                if isinstance(command, (WaitFrames, WaitUntil)):
                    active_wait = command
                    # Check immediately to avoid unnecessary tick
                    if active_wait.check(self):
                        active_wait = None

                elif isinstance(command, InjectInput):
                    command.inject()
                    # Do not tick immediately; allow next command or loop to handle it

                else:
                    pass
                    # raise ValueError(f"Unknown command yielded by scenario: {command}")

    def save_screenshot(self, filename: str):
        """Saves the current frame to disk."""
        if self.game.screen:
            # If render_enabled, force a draw call to update the surface
            if self.render_enabled:
                 # Call the full draw method which handles screen clearing, world render and UI
                 if hasattr(self.game, 'draw'):
                     self.game.draw()
                 elif hasattr(self.game, 'render_world'):
                     self.game.render_world()
                     if hasattr(self.game, 'ui_manager'):
                         self.game.ui_manager.draw_ui(self.game.screen)

            import os
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            pygame.image.save(self.game.screen, filename)
        else:
            raise RuntimeError("Cannot save screenshot: No screen surface available.")
