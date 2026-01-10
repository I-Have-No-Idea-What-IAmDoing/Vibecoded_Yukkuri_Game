import pytest
import os
import pygame
import random
from yukkuri_game.testing.driver import (
    GameDriver,
    WaitFrames,
    KeyPress,
)
from yukkuri_game.scenes.gameplay import GameplayScene
from yukkuri_game.scenes.main_menu import MainMenuScene
from yukkuri_game.game.yukkuri_components import YukkuriStats
from tests.mocks import MockAudioManager


# Note: game_driver fixture comes from conftest.py


def test_rendering_verification(game_driver: GameDriver, tmp_path):
    """
    Verifies that rendering logic works and produces non-empty output.
    Uses log capture to ensure rendering system is doing work.
    """
    driver = game_driver
    # Wait for scene
    driver.wait_until_scene(GameplayScene)
    # Ensure clean state
    driver.reload_scene(GameplayScene)

    # Capture logs during setup/render
    with driver.capture_logs() as logs:
        # Spawn a Yukkuri to ensure there is something to render
        driver.create_yukkuri("reimu", 100, 100)

        # Advance a few frames to let systems update
        driver.run_for(0.5)

        screenshot_path = str(tmp_path / "test_render.png")

        # Saving screenshot forces a render
        driver.save_screenshot(screenshot_path)

        assert os.path.exists(screenshot_path)
        assert os.path.getsize(screenshot_path) > 0

    # Note: Application init logs are captured if we wrap creation, but here we wrap usage.
    # We can check if any warning/error occurred.
    logs.assert_not_logged("Error")

    # Load and check content
    img = pygame.image.load(screenshot_path)
    width, height = img.get_size()

    # Check that it's not all black
    has_content = False
    for x in range(0, width, 50):
        for y in range(0, height, 50):
            color = img.get_at((x, y))
            if color[3] > 0 and (color[0] > 0 or color[1] > 0 or color[2] > 0):
                has_content = True
                break
        if has_content:
            break

    assert has_content, "Screenshot appears to be empty/black where entity should be."


def test_input_injection(game_driver: GameDriver):
    """
    Verifies input injection works.
    """
    driver = game_driver
    driver.wait_until_scene(GameplayScene)
    driver.reload_scene(GameplayScene)
    
    scene = driver.game.scene_manager.current_scene

    # Verify initial state
    assert not scene.paused
    assert isinstance(scene, GameplayScene)

    # Inject ESC to pause/exit to menu
    driver.run_scenario((step for step in [KeyPress(pygame.K_ESCAPE), WaitFrames(10)]))

    # Depending on implementation, ESC might toggle pause or push menu.
    # Assuming standard behavior is MainMenuScene or PauseOverlay.
    # Previous test asserted MainMenuScene.
    assert isinstance(driver.game.scene_manager.current_scene, MainMenuScene)


def test_stress_test(game_driver: GameDriver):
    """
    Stress test with many entities.
    """
    driver = game_driver
    driver.wait_until_scene(GameplayScene)

    # Use reset to ensure clean slate 
    driver.reload_scene(GameplayScene)

    # Spawn 50 Yukkuris
    for _ in range(50):
        driver.create_yukkuri("reimu", random.randint(0, 800), random.randint(0, 600))

    start_frame = driver.frame_count

    with driver.capture_logs() as logs:
        driver.run_for(2.0)  # Run for 2 seconds (simulated)

    logs.assert_not_logged("Exception")

    end_frame = driver.frame_count

    # Check frames advanced
    expected_frames = 2.0 / driver.fixed_dt
    # Allow some tolerance
    assert end_frame - start_frame >= expected_frames - 2

    # Check for stability (no crash, entities still exist)
    count = len(driver.get_entities_with(YukkuriStats))
    # 50 created.
    assert count >= 50


def test_audio_mock(game_driver: GameDriver):
    """
    Verify MockAudioSystem integration.
    """
    driver = game_driver
    driver.wait_until_scene(GameplayScene)
    driver.reload_scene(GameplayScene)
    
    scene = driver.game.scene_manager.current_scene

    # Inject Mock
    mock_audio = MockAudioManager()
    scene.audio = mock_audio

    # Play a sound
    scene.audio.play_sound("test_sound")

    assert "test_sound" in mock_audio.played_sounds

