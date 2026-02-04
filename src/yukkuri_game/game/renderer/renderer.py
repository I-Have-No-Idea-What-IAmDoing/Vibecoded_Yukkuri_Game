"""
Renderer Module.

This module provides the `Renderer` class, which serves as the high-level interface
for submitting render commands. It organizes commands into layers and sorts them
by Z-index before dispatching them to the underlying backend.
"""

from collections import defaultdict
from operator import attrgetter

from .backend import RenderBackend
from .commands import (
    LightCommand,
    OccluderCommand,
    RenderCommand,
    ShadowCommand,
    SpriteCommand,
    TextCommand,
)


class Renderer:
    """
    Main renderer class that accepts commands and dispatches them to the backend.

    Attributes:
        backend (RenderBackend): The rendering backend to use.
        _layers (defaultdict[int, list[RenderCommand]]): A mapping of layer IDs to lists of commands.
    """

    def __init__(self, backend: RenderBackend) -> None:
        """
        Initializes the Renderer.

        Args:
            backend (RenderBackend): The rendering backend to use.
        """
        self.backend = backend
        # Optimization: Separate buckets for layers to avoid sorting everything together.
        # This also allows faster sorting within layers (only by z_index).
        self._layers: defaultdict[int, list[RenderCommand]] = defaultdict(list)

    def submit(self, cmd: RenderCommand) -> None:
        """
        Add a command to the render queue.

        Args:
            cmd (RenderCommand): The render command to submit.
        """
        self._layers[cmd.layer].append(cmd)

    def render(self) -> None:
        """
        Process all queued commands and render the frame.

        Sorts commands by Z-index within each layer and dispatches them to the backend.
        """
        self.backend.begin_frame()

        # Sort layers and iterate
        sorted_layers = sorted(self._layers)

        for layer_id in sorted_layers:
            commands = self._layers[layer_id]
            # Optimization: Sort by Z-index within layer using attrgetter (faster than lambda)
            commands.sort(key=attrgetter("z_index"))

            for cmd in commands:
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
        self._layers.clear()

        self.backend.end_frame()

    def clear_screen(self, color: tuple[int, int, int]) -> None:
        """
        Clears the screen with the specified color.

        Args:
            color (tuple[int, int, int]): The RGB color to clear with.
        """
        self.backend.clear(color)

    def set_ambient_light(self, color: tuple[int, int, int, int]) -> None:
        """
        Sets the ambient light color.

        Args:
            color (tuple[int, int, int, int]): The RGBA ambient color.
        """
        self.backend.set_ambient_light(color)

    def toggle_lighting_debug(self, enabled: bool) -> None:
        """
        Toggles lighting debug mode.

        Args:
            enabled (bool): Whether to enable debug mode.
        """
        self.backend.toggle_lighting_debug(enabled)
