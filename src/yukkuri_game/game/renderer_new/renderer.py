from typing import List, Tuple, Optional
import pygame
from .backend import RenderBackend
from .commands import RenderCommand, SpriteCommand, TextCommand, LightCommand, ShadowCommand, OccluderCommand

class Renderer:
    """
    Main renderer class that accepts commands and dispatches them to the backend.
    """

    def __init__(self, backend: RenderBackend):
        self.backend = backend
        self._commands: List[RenderCommand] = []

    def submit(self, cmd: RenderCommand) -> None:
        """Add a command to the queue."""
        self._commands.append(cmd)

    def render(self) -> None:
        """Process all commands and render the frame."""
        self.backend.begin_frame()

        # Sort commands
        # 1. By Layer
        # 2. By Z-Index (Y position usually)
        self._commands.sort(key=lambda c: (c.layer, c.z_index))

        for cmd in self._commands:
            if isinstance(cmd, SpriteCommand):
                self.backend.draw_sprite(cmd)
            elif isinstance(cmd, TextCommand):
                self.backend.draw_text(cmd)
            elif isinstance(cmd, ShadowCommand):
                self.backend.draw_shadow(cmd)
            elif isinstance(cmd, LightCommand):
                self.backend.draw_light(cmd)
            elif isinstance(cmd, OccluderCommand):
                self.backend.draw_occluder(cmd)

        # Clear command queue
        self._commands.clear()

        self.backend.end_frame()

    def clear_screen(self, color: Tuple[int, int, int]) -> None:
        self.backend.clear(color)

    def set_ambient_light(self, color: Tuple[int, int, int, int]) -> None:
        self.backend.set_ambient_light(color)

    def draw_debug_grid(self, width: int, height: int, cell_size: int, color: Tuple[int, int, int], camera_x: float, camera_y: float) -> None:
        """Helper to draw grid directly (bypassing command queue for simplicity if needed, or we can make GridCommand)."""
        # For now, immediate mode for debug is fine
        # But wait, backend coordinates are screen space.
        # We need to calculate screen lines.
        # It's better if the RenderSystem handles the logic and submits LineCommands (if we had them).
        # Let's add draw_line to backend.
        pass
