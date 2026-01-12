"""
Unit tests for the Camera module.
"""

import pytest
from unittest.mock import MagicMock, patch
import pygame

from yukkuri_game.game.camera import Camera
from yukkuri_game.config import WorldSettings


class TestCameraInitialization:
    """Tests for Camera initialization."""

    def test_default_initialization(self):
        """Camera initializes with default WorldSettings when none provided."""
        camera = Camera()
        assert camera.camera_x == 0.0
        assert camera.camera_y == 0.0
        assert camera.zoom == 1.0
        assert camera.target_zoom == 1.0
        assert camera.min_zoom == 0.5
        assert camera.max_zoom == 2.0

    def test_initialization_with_settings(self):
        """Camera initializes with provided WorldSettings."""
        settings = WorldSettings(width=2000, height=1500)
        camera = Camera(settings)
        assert camera.width == 2000
        assert camera.height == 1500

    def test_initial_cached_values_are_none(self):
        """Cached transformation values start as None."""
        camera = Camera()
        assert camera._cached_zoom_x is None
        assert camera._cached_zoom_y is None
        assert camera._cached_offset_x is None
        assert camera._cached_offset_y is None

    def test_initial_correction_factors(self):
        """Correction factors default to 1.0."""
        camera = Camera()
        assert camera.correction_x == 1.0
        assert camera.correction_y == 1.0


class TestCoordinateConversion:
    """Tests for world-to-screen and screen-to-world conversion."""

    def test_world_to_screen_at_origin(self):
        """World (0,0) maps to screen center."""
        camera = Camera()
        sx, sy = camera.world_to_screen(0, 0, 800, 600)
        assert sx == 400.0
        assert sy == 300.0

    def test_world_to_screen_with_camera_offset(self):
        """World to screen accounts for camera position."""
        camera = Camera()
        camera.camera_x = 100
        camera.camera_y = 50
        sx, sy = camera.world_to_screen(100, 50, 800, 600)
        # Camera is at (100, 50), so world (100, 50) should be at screen center
        assert sx == 400.0
        assert sy == 300.0

    def test_world_to_screen_with_zoom(self):
        """Zoom affects coordinate conversion."""
        camera = Camera()
        camera.zoom = 2.0
        # World (50, 25) at 2x zoom
        sx, sy = camera.world_to_screen(50, 25, 800, 600)
        # (50 - 0) * 2 + 400 = 500, (25 - 0) * 2 + 300 = 350
        assert sx == 500.0
        assert sy == 350.0

    def test_screen_to_world_at_center(self):
        """Screen center maps to camera position."""
        camera = Camera()
        camera.camera_x = 100
        camera.camera_y = 50
        wx, wy = camera.screen_to_world(400, 300, 800, 600)
        assert wx == 100.0
        assert wy == 50.0

    def test_screen_to_world_with_zoom(self):
        """Screen to world accounts for zoom."""
        camera = Camera()
        camera.zoom = 2.0
        # Screen (500, 350) at 2x zoom
        wx, wy = camera.screen_to_world(500, 350, 800, 600)
        # (500 - 400) / 2 + 0 = 50, (350 - 300) / 2 + 0 = 25
        assert wx == 50.0
        assert wy == 25.0

    def test_round_trip_conversion(self):
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

    def test_fast_conversion_requires_update_matrices(self):
        """world_to_screen_fast raises error if update_matrices not called."""
        camera = Camera()
        with pytest.raises(RuntimeError, match="update_matrices"):
            camera.world_to_screen_fast(0, 0)

    def test_fast_conversion_after_update_matrices(self):
        """world_to_screen_fast works after update_matrices is called."""
        camera = Camera()
        camera.update_matrices(800, 600, 1.0)
        sx, sy = camera.world_to_screen_fast(0, 0)
        assert sx == 400.0
        assert sy == 300.0

    def test_fast_conversion_matches_slow(self):
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

    def test_set_aspect_correction(self):
        """set_aspect_correction updates correction factors."""
        camera = Camera()
        camera.set_aspect_correction(1.2, 0.9)
        assert camera.correction_x == 1.2
        assert camera.correction_y == 0.9

    def test_aspect_correction_affects_conversion(self):
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

    def test_update_stores_previous_state(self):
        """update() stores previous position for interpolation."""
        camera = Camera()
        camera.camera_x = 100
        camera.camera_y = 50
        camera.zoom = 1.5

        camera.update(0.016)

        assert camera.prev_camera_x == 100
        assert camera.prev_camera_y == 50
        assert camera.prev_zoom == 1.5

    def test_update_interpolates_zoom(self):
        """update() smoothly interpolates zoom toward target."""
        camera = Camera()
        camera.target_zoom = 2.0
        camera.zoom = 1.0

        # Large dt to see significant movement
        camera.update(0.1)

        assert camera.zoom > 1.0
        assert camera.zoom < 2.0

    def test_clear_resets_state(self):
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

    def test_update_matrices_with_full_alpha(self):
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

    def test_update_matrices_with_zero_alpha(self):
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


class TestHandleInput:
    """Tests for handle_input event processing."""

    @pytest.fixture
    def pygame_init(self):
        """Initialize pygame for event tests."""
        pygame.init()
        yield
        pygame.quit()

    def test_mousewheel_zoom_in(self, pygame_init):
        """Mouse wheel up zooms in."""
        camera = Camera()
        camera.target_zoom = 1.0

        event = pygame.event.Event(pygame.MOUSEWHEEL, y=1)
        camera.handle_input(event, 800, 600)

        assert camera.target_zoom == 1.1

    def test_mousewheel_zoom_out(self, pygame_init):
        """Mouse wheel down zooms out."""
        camera = Camera()
        camera.target_zoom = 1.0

        event = pygame.event.Event(pygame.MOUSEWHEEL, y=-1)
        camera.handle_input(event, 800, 600)

        assert camera.target_zoom == 0.9

    def test_zoom_clamped_to_max(self, pygame_init):
        """Zoom is clamped to max_zoom."""
        camera = Camera()
        camera.target_zoom = 1.95
        camera.max_zoom = 2.0

        event = pygame.event.Event(pygame.MOUSEWHEEL, y=1)
        camera.handle_input(event, 800, 600)

        assert camera.target_zoom == 2.0

    def test_zoom_clamped_to_min(self, pygame_init):
        """Zoom is clamped to min_zoom."""
        camera = Camera()
        camera.target_zoom = 0.55
        camera.min_zoom = 0.5

        event = pygame.event.Event(pygame.MOUSEWHEEL, y=-1)
        camera.handle_input(event, 800, 600)

        assert camera.target_zoom == 0.5


class TestProcessInput:
    """Tests for process_input with InputManager."""

    def test_keyboard_movement_up(self):
        """Arrow keys move camera."""
        camera = Camera()
        input_manager = MagicMock()
        input_manager.is_action_pressed.side_effect = lambda x: x == "up"
        input_manager.get_mouse_wheel.return_value = 0.0

        camera.process_input(input_manager, 0.1)

        # At zoom 1.0, speed = 500 * 0.1 / 1.0 = 50
        assert camera.camera_y < 0  # Moved up

    def test_keyboard_movement_down(self):
        """Down key moves camera down."""
        camera = Camera()
        input_manager = MagicMock()
        input_manager.is_action_pressed.side_effect = lambda x: x == "down"
        input_manager.get_mouse_wheel.return_value = 0.0

        camera.process_input(input_manager, 0.1)

        assert camera.camera_y > 0  # Moved down

    def test_keyboard_movement_left(self):
        """Left key moves camera left."""
        camera = Camera()
        input_manager = MagicMock()
        input_manager.is_action_pressed.side_effect = lambda x: x == "left"
        input_manager.get_mouse_wheel.return_value = 0.0

        camera.process_input(input_manager, 0.1)

        assert camera.camera_x < 0  # Moved left

    def test_keyboard_movement_right(self):
        """Right key moves camera right."""
        camera = Camera()
        input_manager = MagicMock()
        input_manager.is_action_pressed.side_effect = lambda x: x == "right"
        input_manager.get_mouse_wheel.return_value = 0.0

        camera.process_input(input_manager, 0.1)

        assert camera.camera_x > 0  # Moved right

    def test_ctrl_plus_zooms_in(self):
        """Ctrl + time_speed_up zooms in."""
        camera = Camera()
        camera.target_zoom = 1.0
        input_manager = MagicMock()
        input_manager.is_action_pressed.side_effect = lambda x: x in [
            "ctrl",
            "time_speed_up",
        ]
        input_manager.get_mouse_wheel.return_value = 0.0

        camera.process_input(input_manager, 0.1)

        assert camera.target_zoom > 1.0

    def test_ctrl_minus_zooms_out(self):
        """Ctrl + time_speed_down zooms out."""
        camera = Camera()
        camera.target_zoom = 1.0
        input_manager = MagicMock()
        input_manager.is_action_pressed.side_effect = lambda x: x in [
            "ctrl",
            "time_speed_down",
        ]
        input_manager.get_mouse_wheel.return_value = 0.0

        camera.process_input(input_manager, 0.1)

        assert camera.target_zoom < 1.0

    def test_mouse_wheel_via_input_manager(self):
        """Mouse wheel input via InputManager zooms."""
        camera = Camera()
        camera.target_zoom = 1.0
        input_manager = MagicMock()
        input_manager.is_action_pressed.return_value = False
        input_manager.get_mouse_wheel.return_value = 2.0

        camera.process_input(input_manager, 0.1)

        # 1.0 + 2.0 * 0.1 = 1.2
        assert camera.target_zoom == 1.2

    def test_zoom_speed_affected_by_current_zoom(self):
        """Camera movement speed is faster when zoomed out."""
        camera_zoomed_in = Camera()
        camera_zoomed_in.zoom = 2.0
        camera_zoomed_out = Camera()
        camera_zoomed_out.zoom = 0.5

        input_manager = MagicMock()
        input_manager.is_action_pressed.side_effect = lambda x: x == "up"
        input_manager.get_mouse_wheel.return_value = 0.0

        camera_zoomed_in.process_input(input_manager, 0.1)
        camera_zoomed_out.process_input(input_manager, 0.1)

        # Zoomed out should move faster (larger delta)
        assert abs(camera_zoomed_out.camera_y) > abs(camera_zoomed_in.camera_y)
