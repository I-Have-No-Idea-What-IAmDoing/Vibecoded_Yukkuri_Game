"""Integration tests for the visual diff regression testing utility."""

import os
from unittest.mock import MagicMock
import pygame
import pytest
from yukkuri_game.testing.driver import GameDriver
from yukkuri_game.testing.environment import test_environment as mock_test_env


@pytest.fixture
def headless_driver() -> GameDriver:
    """Provides a GameDriver running in a headless environment mock.

    Returns:
        GameDriver: A configured testing driver instance.
    """
    mock_game = MagicMock()
    # Mock game screen to satisfy attribute checks
    mock_game.screen = pygame.Surface((100, 100))
    driver = GameDriver(mock_game)
    # Patch save_screenshot to do nothing so we can write test files manually
    driver.save_screenshot = MagicMock()  # type: ignore[assignment]
    return driver


def test_visual_diff_dimension_mismatch(
    headless_driver: GameDriver, tmp_path: pytest.TempPathFactory
) -> None:
    """Tests that a size mismatch raises AssertionError with file:/// URLs."""
    curr_path = str(tmp_path / "current.png")
    ref_path = str(tmp_path / "reference.png")

    curr_surf = pygame.Surface((100, 100), depth=24)
    ref_surf = pygame.Surface((100, 120), depth=24)

    pygame.image.save(curr_surf, curr_path)
    pygame.image.save(ref_surf, ref_path)

    with mock_test_env():
        with pytest.raises(AssertionError) as exc_info:
            headless_driver.compare_screenshot(curr_path, ref_path)

        err_str = str(exc_info.value)
        assert "Visual Regression Dimension Mismatch!" in err_str
        assert f"file:///{os.path.abspath(ref_path)}" in err_str
        assert f"file:///{os.path.abspath(curr_path)}" in err_str


def test_visual_diff_exact_match(
    headless_driver: GameDriver, tmp_path: pytest.TempPathFactory
) -> None:
    """Tests that two identical images return True successfully."""
    curr_path = str(tmp_path / "current.png")
    ref_path = str(tmp_path / "reference.png")

    # Both blue rectangles
    curr_surf = pygame.Surface((50, 50), depth=24)
    curr_surf.fill((0, 0, 255))
    ref_surf = pygame.Surface((50, 50), depth=24)
    ref_surf.fill((0, 0, 255))

    pygame.image.save(curr_surf, curr_path)
    pygame.image.save(ref_surf, ref_path)

    with mock_test_env():
        matched = headless_driver.compare_screenshot(curr_path, ref_path)
        assert matched is True


def test_visual_diff_mismatch_zero_tolerance(
    headless_driver: GameDriver, tmp_path: pytest.TempPathFactory
) -> None:
    """Tests zero tolerance mismatch raises AssertionError and saves diff."""
    curr_path = str(tmp_path / "current.png")
    ref_path = str(tmp_path / "reference.png")
    diff_path = str(tmp_path / "current_diff.png")

    # Blue reference vs Red actual
    ref_surf = pygame.Surface((10, 10), depth=24)
    ref_surf.fill((0, 0, 255))
    curr_surf = pygame.Surface((10, 10), depth=24)
    curr_surf.fill((255, 0, 0))

    pygame.image.save(curr_surf, curr_path)
    pygame.image.save(ref_surf, ref_path)

    with mock_test_env():
        with pytest.raises(AssertionError) as exc_info:
            headless_driver.compare_screenshot(curr_path, ref_path, tolerance=0.0)

        err_str = str(exc_info.value)
        assert "Visual Regression Mismatch Detected!" in err_str
        assert "Difference Ratio: 100.0000%" in err_str
        assert f"file:///{os.path.abspath(ref_path)}" in err_str
        assert f"file:///{os.path.abspath(curr_path)}" in err_str
        assert f"file:///{os.path.abspath(diff_path)}" in err_str

        # Assert diff mask was created
        assert os.path.exists(diff_path)
        diff_mask_surf = pygame.image.load(diff_path)
        assert diff_mask_surf.get_size() == (10, 10)

        # Mismatched pixels should be Neon Magenta (255, 0, 255)
        for x in range(10):
            for y in range(10):
                color = diff_mask_surf.get_at((x, y))
                assert color[:3] == (255, 0, 255)


def test_visual_diff_permissive_tolerance(
    headless_driver: GameDriver, tmp_path: pytest.TempPathFactory
) -> None:
    """Tests that a single pixel mismatch passes with permissive tolerance."""
    curr_path = str(tmp_path / "current.png")
    ref_path = str(tmp_path / "reference.png")

    # 10x10 images (100 pixels)
    ref_surf = pygame.Surface((10, 10), depth=24)
    ref_surf.fill((0, 0, 255))
    curr_surf = pygame.Surface((10, 10), depth=24)
    curr_surf.fill((0, 0, 255))
    # Mismatch exactly 1 pixel (1% difference)
    curr_surf.set_at((5, 5), (255, 0, 0))

    pygame.image.save(curr_surf, curr_path)
    pygame.image.save(ref_surf, ref_path)

    with mock_test_env():
        # 1% diff <= 2% tolerance -> returns True
        matched = headless_driver.compare_screenshot(
            curr_path, ref_path, tolerance=0.02
        )
        assert matched is True

        # 1% diff > 0.5% tolerance -> raises AssertionError
        with pytest.raises(AssertionError):
            headless_driver.compare_screenshot(
                curr_path, ref_path, tolerance=0.005
            )


def test_visual_diff_drift_threshold(
    headless_driver: GameDriver, tmp_path: pytest.TempPathFactory
) -> None:
    """Tests color channel drift threshold tolerance limits."""
    curr_path = str(tmp_path / "current.png")
    ref_path = str(tmp_path / "reference.png")

    ref_surf = pygame.Surface((5, 5), depth=24)
    ref_surf.fill((0, 0, 255))
    curr_surf = pygame.Surface((5, 5), depth=24)
    # Drift by 3 in blue channel (within 5, outside 2)
    curr_surf.fill((0, 0, 252))

    pygame.image.save(curr_surf, curr_path)
    pygame.image.save(ref_surf, ref_path)

    with mock_test_env():
        # Drift 3 is <= threshold 5 -> passes with zero tolerance
        matched = headless_driver.compare_screenshot(
            curr_path, ref_path, tolerance=0.0, drift_threshold=5
        )
        assert matched is True

        # Drift 3 is > threshold 2 -> fails with zero tolerance
        with pytest.raises(AssertionError):
            headless_driver.compare_screenshot(
                curr_path, ref_path, tolerance=0.0, drift_threshold=2
            )
