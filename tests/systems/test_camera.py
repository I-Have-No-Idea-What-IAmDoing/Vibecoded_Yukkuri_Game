"""
Unit tests for the Camera module.
"""

import pytest
from unittest.mock import MagicMock
import pygame

from yukkuri_game.game.camera import Camera
from yukkuri_game.config import WorldSettings


class TestCameraInitialization:
    """Tests for Camera initialization."""

    def test_default_initialization(self) -> None:
        """Camera initializes with default WorldSettings when none provided."""
        camera = Camera()
        assert camera.camera_x == 0.0
        assert camera.camera_y == 0.0
        assert camera.zoom == 1.0
        assert camera.target_zoom == 1.0
        assert camera.min_zoom == 0.5
        assert camera.max_zoom == 2.0

    def test_initialization_with_settings(self) -> None:
        """Camera initializes with provided WorldSettings."""
        settings = WorldSettings(width=2000, height=1500)
        camera = Camera(settings)
        assert camera.width == 2000
        assert camera.height == 1500

    def test_initial_cached_values_are_none(self) -> None:
        """Cached transformation values start as None."""
        camera = Camera()
        assert camera._cached_zoom_x is None
        assert camera._cached_zoom_y is None
        assert camera._cached_offset_x is None
        assert camera._cached_offset_y is None

    def test_initial_correction_factors(self) -> None:
        """Correction factors default to 1.0."""
        camera = Camera()
        assert camera.correction_x == 1.0
        assert camera.correction_y == 1.0


class TestCoordinateConversion:
    """Tests for world-to-screen and screen-to-world conversion."""

    def test_world_to_screen_at_origin(self) -> None:
        """World (0,0) maps to screen center."""
        camera = Camera()
        sx, sy = camera.world_to_screen(0, 0, 800, 600)
        assert sx == 400.0
        assert sy == 300.0

    def test_world_to_screen_with_camera_offset(self) -> None:
        """World to screen accounts for camera position."""
        camera = Camera()
        camera.camera_x = 100
        camera.camera_y = 50
        sx, sy = camera.world_to_screen(100, 50, 800, 600)
        # Camera is at (100, 50), so world (100, 50) should be at screen center
        assert sx == 400.0
        assert sy == 300.0

    def test_world_to_screen_with_zoom(self) -> None:
        """Zoom affects coordinate conversion."""
        camera = Camera()
        camera.zoom = 2.0
        # World (50, 25) at 2x zoom
        sx, sy = camera.world_to_screen(50, 25, 800, 600)
        # (50 - 0) * 2 + 400 = 500, (25 - 0) * 2 + 300 = 350
        assert sx == 500.0
        assert sy == 350.0

    def test_screen_to_world_at_center(self) -> None:
        """Screen center maps to camera position."""
        camera = Camera()
        camera.camera_x = 100
        camera.camera_y = 50
        wx, wy = camera.screen_to_world(400, 300, 800, 600)
        assert wx == 100.0
        assert wy == 50.0

    def test_screen_to_world_with_zoom(self) -> None:
        """Screen to world accounts for zoom."""
        camera = Camera()
        camera.zoom = 2.0
        # Screen (500, 350) at 2x zoom
        wx, wy = camera.screen_to_world(500, 350, 800, 600)
        # (500 - 400) / 2 + 0 = 50, (350 - 300) / 2 + 0 = 25
        assert wx == 50.0
        assert wy == 25.0

    def test_round_trip_conversion(self) -> None:
        """Converting world->screen->world returns original coordinates."""
        camera = Camera()
        camera.camera_x = 150
        camera.camera_y = 75
        camera.zoom = 1.5

        original_wx, original_wy = 200.0, 100.0
        sx, sy = camera.world_to_screen(original_wx, original_wy, 800, 600)
        wx, wy = camera.screen_to_world(sx, sy, 800, 600)

        assert abs(wx - original_wx) < 0.001
        assert abs(wy - original_wy) < 0.001


class TestFastConversion:
    """Tests for optimized world_to_screen_fast method."""

    def test_fast_conversion_requires_update_matrices(self) -> None:
        """world_to_screen_fast raises error if update_matrices not called."""
        camera = Camera()
        with pytest.raises(RuntimeError, match="update_matrices"):
            camera.world_to_screen_fast(0, 0)

    def test_fast_conversion_after_update_matrices(self) -> None:
        """world_to_screen_fast works after update_matrices is called."""
        camera = Camera()
        camera.update_matrices(800, 600, 1.0)
        sx, sy = camera.world_to_screen_fast(0, 0)
        assert sx == 400.0
        assert sy == 300.0

    def test_fast_conversion_matches_slow(self) -> None:
        """Fast and slow conversion produce same results."""
        camera = Camera()
        camera.camera_x = 100
        camera.camera_y = 50
        camera.zoom = 1.5
        camera.update_matrices(800, 600, 1.0)

        sx_slow, sy_slow = camera.world_to_screen(200, 100, 800, 600)
        sx_fast, sy_fast = camera.world_to_screen_fast(200, 100)

        assert abs(sx_fast - sx_slow) < 0.001
        assert abs(sy_fast - sy_slow) < 0.001


class TestAspectCorrection:
    """Tests for aspect ratio correction."""

    def test_set_aspect_correction(self) -> None:
        """set_aspect_correction updates correction factors."""
        camera = Camera()
        camera.set_aspect_correction(1.2, 0.9)
        assert camera.correction_x == 1.2
        assert camera.correction_y == 0.9

    def test_aspect_correction_affects_conversion(self) -> None:
        """Aspect correction modifies coordinate conversion."""
        camera = Camera()
        camera.set_aspect_correction(2.0, 1.0)
        sx, sy = camera.world_to_screen(50, 50, 800, 600)
        # x: (50 - 0) * 1.0 * 2.0 + 400 = 500
        # y: (50 - 0) * 1.0 * 1.0 + 300 = 350
        assert sx == 500.0
        assert sy == 350.0


class TestCameraUpdate:
    """Tests for camera update logic."""

    def test_update_stores_previous_state(self) -> None:
        """update() stores previous position for interpolation."""
        camera = Camera()
        camera.camera_x = 100
        camera.camera_y = 50
        camera.zoom = 1.5

        camera.update(0.016)

        assert camera.prev_camera_x == 100
        assert camera.prev_camera_y == 50
        assert camera.prev_zoom == 1.5

    def test_update_interpolates_zoom(self) -> None:
        """update() smoothly interpolates zoom toward target."""
        camera = Camera()
        camera.target_zoom = 2.0
        camera.zoom = 1.0

        # Large dt to see significant movement
        camera.update(0.1)

        assert camera.zoom > 1.0
        assert camera.zoom < 2.0

    def test_clear_resets_state(self) -> None:
        """clear() resets camera to default state."""
        camera = Camera()
        camera.camera_x = 100
        camera.camera_y = 50
        camera.zoom = 1.5
        camera.target_zoom = 2.0
        camera.prev_camera_x = 90
        camera.prev_camera_y = 45

        camera.clear()

        assert camera.camera_x == 0.0
        assert camera.camera_y == 0.0
        assert camera.zoom == 1.0
        assert camera.target_zoom == 1.0
        assert camera.prev_camera_x == 0.0
        assert camera.prev_camera_y == 0.0


class TestUpdateMatrices:
    """Tests for update_matrices interpolation."""

    def test_update_matrices_with_full_alpha(self) -> None:
        """update_matrices at alpha=1.0 uses current values."""
        camera = Camera()
        camera.camera_x = 100
        camera.camera_y = 50
        camera.zoom = 2.0
        camera.prev_camera_x = 0
        camera.prev_camera_y = 0
        camera.prev_zoom = 1.0

        camera.update_matrices(800, 600, 1.0)

        # At alpha=1.0, should use current zoom (2.0)
        assert camera._cached_zoom_x == 2.0
        assert camera._cached_zoom_y == 2.0

    def test_update_matrices_with_zero_alpha(self) -> None:
        """update_matrices at alpha=0.0 uses previous values."""
        camera = Camera()
        camera.camera_x = 100
        camera.camera_y = 50
        camera.zoom = 2.0
        camera.prev_camera_x = 0
        camera.prev_camera_y = 0
        camera.prev_zoom = 1.0

        camera.update_matrices(800, 600, 0.0)

        # At alpha=0.0, should use prev zoom (1.0)
        assert camera._cached_zoom_x == 1.0
        assert camera._cached_zoom_y == 1.0


class TestCameraCommandMethods:
    """Tests for the new command-driven Camera API methods."""

    def test_add_zoom_zooms_in(self) -> None:
        """add_zoom with positive delta increases target_zoom."""
        camera = Camera()
        camera.target_zoom = 1.0

        camera.add_zoom(0.1)

        assert camera.target_zoom == pytest.approx(1.1)

    def test_add_zoom_zooms_out(self) -> None:
        """add_zoom with negative delta decreases target_zoom."""
        camera = Camera()
        camera.target_zoom = 1.0

        camera.add_zoom(-0.1)

        assert camera.target_zoom == pytest.approx(0.9)

    def test_add_zoom_clamped_to_max(self) -> None:
        """add_zoom is clamped to max_zoom."""
        camera = Camera()
        camera.target_zoom = 1.95
        camera.max_zoom = 2.0

        camera.add_zoom(0.1)

        assert camera.target_zoom == pytest.approx(2.0)

    def test_add_zoom_clamped_to_min(self) -> None:
        """add_zoom is clamped to min_zoom."""
        camera = Camera()
        camera.target_zoom = 0.55
        camera.min_zoom = 0.5

        camera.add_zoom(-0.1)

        assert camera.target_zoom == pytest.approx(0.5)

    def test_set_axis_moves_camera_via_update(self) -> None:
        """set_axis followed by update() moves the camera."""
        camera = Camera()
        camera.set_axis(0.0, -1.0)  # moving up
        camera.update(0.1)

        assert camera.camera_y < 0

    def test_set_axis_right_moves_right(self) -> None:
        """Positive x_axis moves camera right."""
        camera = Camera()
        camera.set_axis(1.0, 0.0)
        camera.update(0.1)

        assert camera.camera_x > 0

    def test_set_axis_speed_affected_by_zoom(self) -> None:
        """Camera movement speed scales inversely with zoom."""
        cam_in = Camera()
        cam_in.zoom = 2.0
        cam_in.set_axis(0.0, -1.0)

        cam_out = Camera()
        cam_out.zoom = 0.5
        cam_out.set_axis(0.0, -1.0)

        cam_in.update(0.1)
        cam_out.update(0.1)

        assert abs(cam_out.camera_y) > abs(cam_in.camera_y)

    def test_pan_adjusts_camera_position(self) -> None:
        """pan() moves camera_x/y by pixel delta / zoom."""
        camera = Camera()
        camera.zoom = 1.0

        camera.pan(100, 50)

        assert camera.camera_x == pytest.approx(-100.0)
        assert camera.camera_y == pytest.approx(-50.0)

    def test_pan_accounts_for_zoom(self) -> None:
        """pan() adjusts panning speed by zoom level."""
        camera = Camera()
        camera.zoom = 2.0

        camera.pan(100, 0)

        assert camera.camera_x == pytest.approx(-50.0)

    def test_set_zoom_axis_affects_target_zoom(self) -> None:
        """set_zoom_axis > 0 increases target_zoom on update."""
        camera = Camera()
        camera.target_zoom = 1.0
        camera.set_zoom_axis(1.0)
        camera.update(0.1)

        assert camera.target_zoom > 1.0
