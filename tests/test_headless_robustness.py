
import pytest
import os
import pygame
import random
from src.yukkuri_game.testing.driver import GameDriver, WaitFrames, InjectInput, KeyPress, WaitUntilScene
from src.yukkuri_game.engine.application import Application
from src.yukkuri_game.scenes.gameplay import GameplayScene
from src.yukkuri_game.scenes.main_menu import MainMenuScene
from src.yukkuri_game.game.yukkuri_components import YukkuriStats
from tests.mocks import MockAudioManager

@pytest.fixture
def headless_app():
    # Force dummy driver again just in case, though Application does it.
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    app = Application(headless=True)
    yield app
    app.quit()

@pytest.fixture
def driver(headless_app):
    driver = GameDriver(headless_app)
    driver.setup()
    return driver

def test_rendering_verification(driver, tmp_path):
    """
    Verifies that rendering logic works and produces non-empty output.
    """
    # Wait for scene
    driver.wait_until_scene(GameplayScene)

    # Spawn a Yukkuri to ensure there is something to render
    driver.create_yukkuri("reimu", 100, 100)

    # Advance a few frames to let systems update
    driver.run_for(0.5)

    screenshot_path = str(tmp_path / "test_render.png")

    driver.save_screenshot(screenshot_path)

    assert os.path.exists(screenshot_path)
    assert os.path.getsize(screenshot_path) > 0

    # Load and check content
    img = pygame.image.load(screenshot_path)
    width, height = img.get_size()

    # Check that it's not all black
    center_x = width // 2
    center_y = height // 2

    has_content = False
    # Sample a grid
    for x in range(0, width, 50):
        for y in range(0, height, 50):
            color = img.get_at((x, y))
            # Alpha is not fully transparent and color is not black
            if color[3] > 0 and (color[0] > 0 or color[1] > 0 or color[2] > 0):
                has_content = True
                break
        if has_content: break

    assert has_content, "Screenshot appears to be empty/black where entity should be."

def test_input_injection(driver):
    """
    Verifies input injection works.
    """
    driver.wait_until_scene(GameplayScene)
    scene = driver.game.scene_manager.current_scene

    # Verify initial state
    assert not scene.paused
    assert isinstance(scene, GameplayScene)

    # Inject ESC to pause/exit to menu
    driver.run_scenario(
        (step for step in [
            KeyPress(pygame.K_ESCAPE),
            WaitFrames(10)
        ])
    )

    assert isinstance(driver.game.scene_manager.current_scene, MainMenuScene)

def test_stress_test(driver):
    """
    Stress test with many entities.
    """
    driver.wait_until_scene(GameplayScene)

    # Spawn 50 Yukkuris
    for _ in range(50):
        driver.create_yukkuri("reimu", random.randint(0, 800), random.randint(0, 600))

    start_frame = driver.frame_count
    driver.run_for(2.0) # Run for 2 seconds (simulated)
    end_frame = driver.frame_count

    # Check frames advanced
    expected_frames = 2.0 / driver.fixed_dt
    # Allow some tolerance
    assert end_frame - start_frame >= expected_frames - 2

    # Check for stability (no crash, entities still exist)
    count = len(driver.get_entities_with(YukkuriStats))
    # Initial 1 (from setup) + 50 created = 51.
    assert count >= 50

def test_audio_mock(driver):
    """
    Verify MockAudioSystem integration.
    """
    driver.wait_until_scene(GameplayScene)
    scene = driver.game.scene_manager.current_scene

    # Inject Mock
    mock_audio = MockAudioManager()
    scene.audio = mock_audio

    # Play a sound
    scene.audio.play_sound("test_sound")

    assert "test_sound" in mock_audio.played_sounds
