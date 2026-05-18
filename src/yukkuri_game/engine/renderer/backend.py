"""
Renderer Backend Protocol.
"""

from typing import Protocol

from .commands import (
    LightCommand,
    OccluderCommand,
    ShadowCommand,
    SpriteCommand,
    TextCommand,
)


class RenderBackend(Protocol):
    """
    Interface for rendering backends.
    """

    def clear(self, color: tuple[int, int, int]) -> None:
        """Clears the screen."""
        ...

    def begin_frame(self) -> None:
        """Prepares for a new frame."""
        ...

    def end_frame(self) -> None:
        """Finalizes the frame."""
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

    def set_ambient_light(self, color: tuple[int, int, int, int]) -> None:
        """Sets the ambient light color."""
        ...

    def draw_line(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        color: tuple[int, int, int],
        width: int = 1,
    ) -> None:
        """Draws a line."""
        ...

    def toggle_lighting_debug(self, enabled: bool) -> None:
        """Toggles lighting debug mode."""
        ...
