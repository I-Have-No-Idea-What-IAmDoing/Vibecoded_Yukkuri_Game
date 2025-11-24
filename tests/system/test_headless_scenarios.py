import os
import pygame
import pytest
from unittest import mock
from src.yukkuri_game.testing.runner import HeadlessGameRunner

@pytest.fixture
def clean_screenshots():
    # Setup: Clean screenshots dir
    if os.path.exists("screenshots"):
        for f in os.listdir("screenshots"):
            os.remove(os.path.join("screenshots", f))
    else:
        os.makedirs("screenshots")
    yield
    # Teardown (optional)

@pytest.fixture
def headless_env():
    # Use mock.patch.dict to set environment variable safely for the test
    with mock.patch.dict(os.environ, {"SDL_VIDEODRIVER": "dummy"}):
        yield

def test_headless_scenario(clean_screenshots, headless_env):
    """
    Runs a headless scenario:
    1. Start game.
    2. Wait 1s.
    3. Take screenshot.
    4. Wait 1s.
    5. Quit.
    """
    scenario = [
        {"time": 1.0, "action": "screenshot"},
        {"time": 2.0, "action": "quit"}
    ]

    runner = HeadlessGameRunner(scenario, max_duration=5.0)
    runner.run()

    # Verify screenshot exists
    screenshots = os.listdir("screenshots")
    assert len(screenshots) == 1
    assert screenshots[0].endswith(".png")

    # Verify file size > 0
    filepath = os.path.join("screenshots", screenshots[0])
    assert os.path.getsize(filepath) > 0

def test_headless_interaction(clean_screenshots, headless_env):
    """
    Runs a headless scenario with interaction:
    1. Click on screen (should spawn something if default tool is selected or just interact).
    2. Take screenshot.
    """
    scenario = [
        {"time": 0.5, "action": "click", "pos": (400, 300), "button": 1},
        {"time": 1.0, "action": "screenshot"},
        {"time": 1.5, "action": "quit"}
    ]

    runner = HeadlessGameRunner(scenario, max_duration=3.0)
    runner.run()

    screenshots = os.listdir("screenshots")
    assert len(screenshots) == 1
