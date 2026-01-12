"""
Module handling the game camera.
"""

from typing import TYPE_CHECKING
import pygame
from ..config import WorldSettings

if TYPE_CHECKING:
    from ..engine.input_manager import InputManager


class Camera:
    """
    Manages the game world view, including coordinate conversion and camera control.

    Attributes:
        width (int): The total width of the game world.
        height (int): The total height of the game world.
        camera_x (float): The x-coordinate of the camera focus point.
        camera_y (float): The y-coordinate of the camera focus point.
        zoom (float): The current zoom level.
        target_zoom (float): The target zoom level for smooth transitions.
        min_zoom (float): Minimum allowed zoom level.
        max_zoom (float): Maximum allowed zoom level.
    """

    def __init__(self, settings: WorldSettings | None = None):
        """
        Initializes the Camera.

        Args:
            settings (WorldSettings | None): World settings configuration.
        """
        _settings = settings if settings is not None else WorldSettings()
        self.width = _settings.width
        self.height = _settings.height
        # Camera properties
        self.camera_x = 0.0
        self.camera_y = 0.0
        self.zoom = 1.0
        self.target_zoom = 1.0

        # Previous state for interpolation
        self.prev_camera_x = 0.0
        self.prev_camera_y = 0.0
        self.prev_zoom = 1.0

        # Bounds
        self.min_zoom = 0.5
        self.max_zoom = 2.0

        # Optimization: Cached values for fast coordinate conversion
        self._cached_zoom_x = None
        self._cached_zoom_y = None
        self._cached_offset_x = None
        self._cached_offset_y = None

        self.correction_x = 1.0
        self.correction_y = 1.0

    def set_aspect_correction(self, x: float, y: float) -> None:
        """Sets the aspect ratio correction factors."""
        self.correction_x = x
        self.correction_y = y

    def update_matrices(self, screen_w: int, screen_h: int, alpha: float = 1.0) -> None:
        """
        Updates cached transformation matrices using interpolation.
        Call this at the beginning of a render frame.

        Args:
            screen_w (int): Screen width.
            screen_h (int): Screen height.
            alpha (float): Interpolation factor (0.0 to 1.0).
        """
        # Interpolate camera position and zoom
        curr_zoom = self.prev_zoom + (self.zoom - self.prev_zoom) * alpha
        curr_x = self.prev_camera_x + (self.camera_x - self.prev_camera_x) * alpha
        curr_y = self.prev_camera_y + (self.camera_y - self.prev_camera_y) * alpha

        self._cached_zoom_x = curr_zoom * self.correction_x
        self._cached_zoom_y = curr_zoom * self.correction_y

        # Precompute offset: -camera * zoom + screen_center
        self._cached_offset_x = -curr_x * self._cached_zoom_x + screen_w / 2
        self._cached_offset_y = -curr_y * self._cached_zoom_y + screen_h / 2

    def world_to_screen(
        self, wx: float, wy: float, screen_w: int, screen_h: int
    ) -> tuple[float, float]:
        """
        Converts world coordinates to screen coordinates.

        Formula: screen = (world - camera) * zoom + screen_center

        Args:
            wx (float): World x-coordinate.
            wy (float): World y-coordinate.
            screen_w (int): Screen width.
            screen_h (int): Screen height.

        Returns:
            tuple[float, float]: (screen_x, screen_y)
        """
        # Note: Slow version does NOT apply aspect correction by default unless we access self.correction_x
        # But for consistency, we probably should?
        # However, slow version is used for Input, which usually maps 1:1 to screen pixels.
        # If visual is squashed, input should be squashed too to match?
        # Yes.
        sx = (wx - self.camera_x) * self.zoom * self.correction_x + screen_w / 2
        sy = (wy - self.camera_y) * self.zoom * self.correction_y + screen_h / 2
        return sx, sy

    def world_to_screen_fast(self, wx: float, wy: float) -> tuple[float, float]:
        """
        Optimized version of world_to_screen that uses cached values.
        Requires update_matrices() to be called first in the frame.
        """
        if (
            self._cached_zoom_x is None
            or self._cached_zoom_y is None
            or self._cached_offset_x is None
            or self._cached_offset_y is None
        ):
            raise RuntimeError(
                "Camera.update_matrices() must be called before world_to_screen_fast()"
            )
        return (
            wx * self._cached_zoom_x + self._cached_offset_x,
            wy * self._cached_zoom_y + self._cached_offset_y,
        )

    def screen_to_world(
        self, sx: float, sy: float, screen_w: int, screen_h: int
    ) -> tuple[float, float]:
        """
        Converts screen coordinates to world coordinates.
        Inverse of world_to_screen.

        Formula: world = (screen - screen_center) / zoom + camera

        Args:
            sx (float): Screen x-coordinate.
            sy (float): Screen y-coordinate.
            screen_w (int): Screen width.
            screen_h (int): Screen height.

        Returns:
            tuple[float, float]: (world_x, world_y)
        """
        wx = (sx - screen_w / 2) / (self.zoom * self.correction_x) + self.camera_x
        wy = (sy - screen_h / 2) / (self.zoom * self.correction_y) + self.camera_y
        return wx, wy

    def handle_input(
        self, event: pygame.event.Event, screen_w: int, screen_h: int
    ) -> None:
        """
        Handles input for camera control (zoom and pan).

        Args:
            event (pygame.event.Event): The Pygame event.
            screen_w (int): Screen width.
            screen_h (int): Screen height.

        Returns:
            None
        """
        zoom_amount = 0.0
        if event.type == pygame.MOUSEWHEEL:
            # Zoom in/out based on wheel movement
            zoom_amount = event.y * 0.1
        elif event.type == pygame.MOUSEMOTION:
            if pygame.mouse.get_pressed()[1]:  # Middle mouse button
                # Pan the camera
                dx, dy = event.rel
                # Adjust panning speed by zoom so it feels natural at all levels
                self.camera_x -= dx / self.zoom
                self.camera_y -= dy / self.zoom
        elif event.type == pygame.KEYDOWN:
            mods = pygame.key.get_mods()
            if mods & pygame.KMOD_CTRL:
                if event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS:
                    # Zoom In with Keyboard
                    zoom_amount = 0.1
                elif event.key == pygame.K_MINUS:
                    # Zoom Out with Keyboard
                    zoom_amount = -0.1

        if zoom_amount != 0.0:
            self.target_zoom += zoom_amount
            self.target_zoom = max(self.min_zoom, min(self.max_zoom, self.target_zoom))

    def clear(self) -> None:
        """Reset camera to default."""
        self.camera_x = 0.0
        self.camera_y = 0.0
        self.zoom = 1.0
        self.target_zoom = 1.0
        self.prev_camera_x = 0.0
        self.prev_camera_y = 0.0
        self.prev_zoom = 1.0

    def update(self, dt: float) -> None:
        """
        Updates the camera state (e.g., smooth zoom).
        This method now only handles smooth zoom interpolation.
        Keyboard/mouse movement is handled by process_input().

        Args:
            dt (float): Delta time.

        Returns:
            None
        """
        # Save previous state for interpolation
        self.prev_camera_x = self.camera_x
        self.prev_camera_y = self.camera_y
        self.prev_zoom = self.zoom

        # Smooth zoom interpolation
        # Using linear interpolation (Lerp) with a factor of 5.0 for smooth transition
        self.zoom += (self.target_zoom - self.zoom) * 5.0 * dt

    def process_input(self, input_manager: "InputManager", dt: float) -> None:
        """
        Processes camera input using the InputManager.
        Should be called every frame.

        Args:
            input_manager (InputManager): The input manager instance.
            dt (float): Delta time.
        """
        # Keyboard Movement
        speed = 500.0 * dt / self.zoom  # Adjust by zoom for consistent feel

        if input_manager.is_action_pressed("up"):
            self.camera_y -= speed
        if input_manager.is_action_pressed("down"):
            self.camera_y += speed
        if input_manager.is_action_pressed("left"):
            self.camera_x -= speed
        if input_manager.is_action_pressed("right"):
            self.camera_x += speed

        # Keyboard Zoom (Ctrl + +/-)
        # Uses time_speed_up/down actions since +/- are mapped there; Ctrl differentiates zoom from speed.
        if input_manager.is_action_pressed("ctrl"):
            if input_manager.is_action_pressed("time_speed_up"):
                self.target_zoom = min(self.max_zoom, self.target_zoom + 0.1 * dt * 10)
            if input_manager.is_action_pressed("time_speed_down"):
                self.target_zoom = max(self.min_zoom, self.target_zoom - 0.1 * dt * 10)

        # Mouse Wheel Zoom (handled via get_mouse_wheel)
        wheel = input_manager.get_mouse_wheel()
        if wheel != 0.0:
            self.target_zoom += wheel * 0.1
            self.target_zoom = max(self.min_zoom, min(self.max_zoom, self.target_zoom))
