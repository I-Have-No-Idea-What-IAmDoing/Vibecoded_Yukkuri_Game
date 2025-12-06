"""
Module handling the game camera.
"""

import pygame
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

        # Bounds
        self.min_zoom = 0.5
        self.max_zoom = 2.0

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
        sx = (wx - self.camera_x) * self.zoom + screen_w / 2
        sy = (wy - self.camera_y) * self.zoom + screen_h / 2
        return sx, sy

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
        wx = (sx - screen_w / 2) / self.zoom + self.camera_x
        wy = (sy - screen_h / 2) / self.zoom + self.camera_y
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
        if event.type == pygame.MOUSEWHEEL:
            # Zoom in/out based on wheel movement
            self.target_zoom += event.y * 0.1
            self.target_zoom = max(self.min_zoom, min(self.max_zoom, self.target_zoom))
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
                    self.target_zoom += 0.1
                    self.target_zoom = max(
                        self.min_zoom, min(self.max_zoom, self.target_zoom)
                    )
                elif event.key == pygame.K_MINUS:
                    # Zoom Out with Keyboard
                    self.target_zoom -= 0.1
                    self.target_zoom = max(
                        self.min_zoom, min(self.max_zoom, self.target_zoom)
                    )

    def clear(self) -> None:
        """Reset camera to default."""
        self.camera_x = 0.0
        self.camera_y = 0.0
        self.zoom = 1.0
        self.target_zoom = 1.0

    def update(self, dt: float) -> None:
        """
        Updates the camera state (e.g., smooth zoom).

        Args:
            dt (float): Delta time.

        Returns:
            None
        """
        # Handle continuous camera movement via keyboard
        keys = pygame.key.get_pressed()
        speed = (
            500.0 * dt / self.zoom
        )  # Adjust speed based on zoom so movement is consistent relative to screen

        if keys[pygame.K_w] or keys[pygame.K_UP]:
            self.camera_y -= speed
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            self.camera_y += speed
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            self.camera_x -= speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            self.camera_x += speed

        # Smooth zoom interpolation
        # Using linear interpolation (Lerp) with a factor of 5.0 for smooth transition
        self.zoom += (self.target_zoom - self.zoom) * 5.0 * dt
