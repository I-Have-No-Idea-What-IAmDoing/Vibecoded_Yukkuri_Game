"""
Module for testing infrastructure.
"""
from typing import List, Dict, Any, Optional
import pygame
from loguru import logger
from ..main import YukkuriGame

class InputInjector:
    """
    Injects simulated input events into the game loop.
    """
    @staticmethod
    def post_event(event_type: int, **kwargs) -> None:
        """
        Posts a pygame event.
        """
        event = pygame.event.Event(event_type, kwargs)
        pygame.event.post(event)

    @staticmethod
    def click(x: int, y: int, button: int = 1) -> None:
        """
        Simulates a mouse click.
        """
        InputInjector.post_event(pygame.MOUSEBUTTONDOWN, pos=(x, y), button=button)
        InputInjector.post_event(pygame.MOUSEBUTTONUP, pos=(x, y), button=button)

    @staticmethod
    def key_press(key: int) -> None:
        """
        Simulates a key press.
        """
        InputInjector.post_event(pygame.KEYDOWN, key=key)
        InputInjector.post_event(pygame.KEYUP, key=key)

class HeadlessGameRunner(YukkuriGame):
    """
    Runs the game in headless mode with a predefined scenario.
    """
    def __init__(self, scenario: List[Dict[str, Any]], max_duration: float = 10.0):
        super().__init__(headless=True, render_headless=True)
        self.scenario = sorted(scenario, key=lambda x: x["time"])
        self.max_duration = max_duration
        self.scenario_index = 0
        self.elapsed_time = 0.0

    def update(self) -> None:
        self.elapsed_time += self.dt

        # Process scenario events
        while self.scenario_index < len(self.scenario):
            event_def = self.scenario[self.scenario_index]
            if self.elapsed_time >= event_def["time"]:
                self.process_scenario_event(event_def)
                self.scenario_index += 1
            else:
                break

        super().update()

        # Auto-terminate
        if self.elapsed_time >= self.max_duration:
            logger.info("Max duration reached. Stopping.")
            self.running = False

    def process_scenario_event(self, event_def: Dict[str, Any]) -> None:
        action = event_def["action"]
        logger.info(f"Executing scenario action: {action} at {self.elapsed_time:.2f}s")

        if action == "click":
            InputInjector.click(event_def["pos"][0], event_def["pos"][1], event_def.get("button", 1))
        elif action == "key":
            # Assume key is passed as pygame constant integer or we might need mapping
            InputInjector.key_press(event_def["key"])
        elif action == "screenshot":
            self.take_screenshot()
            # Rename last screenshot if name provided?
            # Current take_screenshot uses timestamp.
            # We could modify take_screenshot to accept name, or just log it.
        elif action == "quit":
            self.running = False
