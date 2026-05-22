"""
Renderer Module.
"""

from collections import defaultdict
from operator import attrgetter
from typing import Any

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
    """

    def __init__(self, backend: RenderBackend) -> None:
        self.backend = backend
        self._layers: defaultdict[int, list[RenderCommand]] = defaultdict(list)
        self._dispatch: dict[type, Any] = {
            SpriteCommand: backend.draw_sprite,
            TextCommand: backend.draw_text,
            ShadowCommand: backend.draw_shadow,
            LightCommand: backend.draw_light,
            OccluderCommand: backend.draw_occluder,
        }

    def submit(self, cmd: RenderCommand) -> None:
        """Add a command to the render queue."""
        self._layers[cmd.layer].append(cmd)

    def render(self) -> None:
        """Process all queued commands and render the frame."""
        self.backend.begin_frame()
        sorted_layers = sorted(self._layers)
        dispatch = self._dispatch
        for layer_id in sorted_layers:
            commands = self._layers[layer_id]
            commands.sort(key=attrgetter("z_index"))
            for cmd in commands:
                handler = dispatch.get(type(cmd))
                if handler is not None:
                    handler(cmd)
                else:
                    # Fall back to module-name matching to handle dual-import
                    # edge cases where the same class is loaded under two paths.
                    cmd_type_name = type(cmd).__qualname__
                    handler = next(
                        (v for k, v in dispatch.items() if k.__qualname__ == cmd_type_name),
                        None,
                    )
                    if handler is not None:
                        handler(cmd)
                    else:
                        from loguru import logger
                        logger.warning(
                            f"Renderer: no handler for command type {type(cmd)!r}"
                        )
        self._layers.clear()
        self.backend.end_frame()


    def clear_screen(self, color: tuple[int, int, int]) -> None:
        """Clears the screen."""
        self.backend.clear(color)

    def set_ambient_light(self, color: tuple[int, int, int, int]) -> None:
        """Sets the ambient light color."""
        self.backend.set_ambient_light(color)

    def toggle_lighting_debug(self, enabled: bool) -> None:
        """Toggles lighting debug mode."""
        self.backend.toggle_lighting_debug(enabled)
