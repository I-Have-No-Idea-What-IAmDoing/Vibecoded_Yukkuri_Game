"""
Module handling the game camera.
"""

from ..config import WorldSettings


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
        self._cached_zoom_x: float | None = None
        self._cached_zoom_y: float | None = None
        self._cached_offset_x: float | None = None
        self._cached_offset_y: float | None = None

        # Raw interpolated values (no aspect correction)
        self._cached_zoom: float = 1.0
        self._cached_cam_x: float = 0.0
        self._cached_cam_y: float = 0.0

        # Input axis state set by CameraAxisCommand / CameraZoomAxisCommand
        self.input_axis_x: float = 0.0
        self.input_axis_y: float = 0.0
        self.zoom_axis: float = 0.0

        self.correction_x = 1.0
        self.correction_y = 1.0

    def set_aspect_correction(self, x: float, y: float) -> None:
        """
        Sets the aspect ratio correction factors.

        Args:
            x (float): Horizontal aspect correction.
            y (float): Vertical aspect correction.
        """
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

        # Store raw interpolated values for systems that need them
        self._cached_zoom = curr_zoom
        self._cached_cam_x = curr_x
        self._cached_cam_y = curr_y

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

        Args:
            wx (float): World x-coordinate.
            wy (float): World y-coordinate.

        Returns:
            tuple[float, float]: (screen_x, screen_y)

        Raises:
            RuntimeError: If update_matrices() was not called before this method.
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


    def clear(self) -> None:
        """Reset camera to default."""
        self.camera_x = 0.0
        self.camera_y = 0.0
        self.zoom = 1.0
        self.target_zoom = 1.0
        self.prev_camera_x = 0.0
        self.prev_camera_y = 0.0
        self.prev_zoom = 1.0
        self.input_axis_x = 0.0
        self.input_axis_y = 0.0
        self.zoom_axis = 0.0

    def update(self, dt: float) -> None:
        """
        Updates the camera state each frame.

        Applies movement from the current input-axis state, advances
        smooth zoom interpolation, and saves previous state for
        render-interpolation.

        Args:
            dt (float): Delta time.
        """
        # Save previous state for interpolation
        self.prev_camera_x = self.camera_x
        self.prev_camera_y = self.camera_y
        self.prev_zoom = self.zoom

        # Apply keyboard movement from axis state
        speed = 500.0 * dt / self.zoom
        self.camera_x += self.input_axis_x * speed
        self.camera_y += self.input_axis_y * speed

        # Apply keyboard zoom axis
        if self.zoom_axis != 0.0:
            self.target_zoom = max(
                self.min_zoom,
                min(self.max_zoom, self.target_zoom + self.zoom_axis * 0.1 * dt * 10),
            )

        # Smooth zoom interpolation
        self.zoom += (self.target_zoom - self.zoom) * 5.0 * dt

    # ------------------------------------------------------------------
    # Command-driven state setters
    # ------------------------------------------------------------------

    def set_axis(self, x_axis: float, y_axis: float) -> None:
        """
        Sets the movement axis state used in update().

        Called by CameraAxisCommand.

        Args:
            x_axis (float): Horizontal axis in [-1, 1].
            y_axis (float): Vertical axis in [-1, 1].
        """
        self.input_axis_x = x_axis
        self.input_axis_y = y_axis

    def set_zoom_axis(self, zoom_axis: float) -> None:
        """
        Sets the keyboard-zoom axis state used in update().

        Called by CameraZoomAxisCommand.

        Args:
            zoom_axis (float): Zoom axis in [-1, 1].
        """
        self.zoom_axis = zoom_axis

    def add_zoom(self, delta: float) -> None:
        """
        Adds a discrete delta to the target zoom level.

        Called by CameraZoomCommand (mouse wheel).

        Args:
            delta (float): Amount to add to target zoom.
        """
        self.target_zoom += delta
        self.target_zoom = max(self.min_zoom, min(self.max_zoom, self.target_zoom))

    def pan(self, dx: int, dy: int) -> None:
        """
        Pans the camera by a screen-pixel delta.

        Called by CameraPanCommand (middle-mouse drag).

        Args:
            dx (int): Horizontal pixel delta.
            dy (int): Vertical pixel delta.
        """
        self.camera_x -= dx / self.zoom
        self.camera_y -= dy / self.zoom
