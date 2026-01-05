from typing import Protocol, List, Tuple
import pygame
from .commands import RenderCommand, SpriteCommand, TextCommand, LightCommand, ShadowCommand, OccluderCommand

class RenderBackend(Protocol):
    """Interface for rendering backends."""

    def clear(self, color: Tuple[int, int, int]) -> None:
        """Clears the screen."""
        ...

    def begin_frame(self) -> None:
        """Prepares for a new frame."""
        ...

    def end_frame(self) -> None:
        """Finalizes the frame (flips buffers, etc.)."""
        ...

    def draw_sprite(self, cmd: SpriteCommand) -> None:
        """Draws a sprite."""
        ...

    def draw_text(self, cmd: TextCommand) -> None:
        """Draws text."""
        ...

    def draw_shadow(self, cmd: ShadowCommand) -> None:
        """Draws a blob shadow."""
        ...

    def draw_light(self, cmd: LightCommand) -> None:
        """Process a light source."""
        ...

    def draw_occluder(self, cmd: OccluderCommand) -> None:
        """Process an occluder."""
        ...

    def set_ambient_light(self, color: Tuple[int, int, int, int]) -> None:
        """Sets the ambient light color."""
        ...

    def draw_line(self, start: Tuple[float, float], end: Tuple[float, float], color: Tuple[int, int, int], width: int = 1) -> None:
        """Draws a line (mainly for debug/grid)."""
        ...
