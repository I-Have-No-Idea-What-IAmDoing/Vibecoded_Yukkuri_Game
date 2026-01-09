
import os
import sys
import pygame

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from yukkuri_game.testing.environment import TestEnvironment
from yukkuri_game.testing.driver import GameDriver
from yukkuri_game.engine.application import Application

def reproduce():
    with TestEnvironment():
        # Initialize Application
        app = Application(headless=True)

        # Initialize Driver
        driver = GameDriver(app)
        driver.setup()

        # Wait for scene to be active and some frames to pass
        driver.run_for(1.0)

        # Place a street lamp
        # We need to find the ID for street lamp. Usually it is 'street_lamp' or similar.
        # Let's try to create an item.
        # Based on file structure, I should check entity_factory but I can just try 'street_lamp'.
        driver.create_item("lamp", 200, 200)

        # Run a bit more to let it render
        driver.run_for(0.5)

        # Take screenshot
        screenshot_path = "screenshots/reproduce_issue.png"
        driver.save_screenshot(screenshot_path)
        print(f"Screenshot saved to {screenshot_path}")

if __name__ == "__main__":
    reproduce()
