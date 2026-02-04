"""
Renderer Backend Protocol.

This module defines the `RenderBackend` protocol, which specifies the interface
that any rendering backend (e.g., Pygame, OpenGL) must implement.
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

    Defines the contract for drawing operations.
    """

    def clear(self, color: tuple[int, int, int]) -> None:
        """
        Clears the screen.

        Args:
            color (tuple[int, int, int]): The RGB color to clear with.
        """
        ...

    def begin_frame(self) -> None:
        """
        Prepares for a new frame.

        This might involve clearing buffers, resetting state, or other setup tasks.
        """
        ...

    def end_frame(self) -> None:
        """
        Finalizes the frame.

        This usually involves flipping the display buffers.
        """
        ...

    def draw_sprite(self, cmd: SpriteCommand) -> None:
        """
        Draws a sprite.

        Args:
            cmd (SpriteCommand): The sprite command.
        """
        ...

    def draw_text(self, cmd: TextCommand) -> None:
        """
        Draws text.

        Args:
            cmd (TextCommand): The text command.
        """
        ...

    def draw_shadow(self, cmd: ShadowCommand) -> None:
        """
        Draws a blob shadow.

        Args:
            cmd (ShadowCommand): The shadow command.
        """
        ...

    def draw_light(self, cmd: LightCommand) -> None:
        """
        Process a light source.

        Args:
            cmd (LightCommand): The light command.
        """
        ...

    def draw_occluder(self, cmd: OccluderCommand) -> None:
        """
        Process an occluder.

        Args:
            cmd (OccluderCommand): The occluder command.
        """
        ...

    def set_ambient_light(self, color: tuple[int, int, int, int]) -> None:
        """
        Sets the ambient light color.

        Args:
            color (tuple[int, int, int, int]): The RGBA ambient color.
        """
        ...

    def draw_line(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        color: tuple[int, int, int],
        width: int = 1,
    ) -> None:
        """
        Draws a line (mainly for debug/grid).

        Args:
            start (tuple[float, float]): Start point (x, y).
            end (tuple[float, float]): End point (x, y).
            color (tuple[int, int, int]): RGB color.
            width (int): Line width in pixels. Defaults to 1.
        """
        ...

    def toggle_lighting_debug(self, enabled: bool) -> None:
        """
        Toggles lighting debug mode.

        Args:
            enabled (bool): Whether to enable debug mode.
        """
        ...
