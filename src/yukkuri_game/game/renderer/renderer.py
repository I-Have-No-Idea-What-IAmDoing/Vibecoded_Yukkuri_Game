from collections import defaultdict
from operator import attrgetter
from .backend import RenderBackend
from .commands import (
    RenderCommand,
    SpriteCommand,
    TextCommand,
    LightCommand,
    ShadowCommand,
    OccluderCommand,
)


class Renderer:
    """
    Main renderer class that accepts commands and dispatches them to the backend.
    """

    def __init__(self, backend: RenderBackend):
        self.backend = backend
        # Optimization: Separate buckets for layers to avoid sorting everything together.
        # This also allows faster sorting within layers (only by z_index).
        self._layers: defaultdict[int, list[RenderCommand]] = defaultdict(list)

    def submit(self, cmd: RenderCommand) -> None:
        """Add a command to the queue."""
        self._layers[cmd.layer].append(cmd)

    def render(self) -> None:
        """Process all commands and render the frame."""
        self.backend.begin_frame()

        # Sort layers and iterate
        sorted_layers = sorted(self._layers.keys())

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
        self.backend.clear(color)

    def set_ambient_light(self, color: tuple[int, int, int, int]) -> None:
        self.backend.set_ambient_light(color)

    def toggle_lighting_debug(self, enabled: bool) -> None:
        self.backend.toggle_lighting_debug(enabled)
