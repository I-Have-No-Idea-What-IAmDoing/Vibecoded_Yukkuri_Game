"""
Light Pass.
"""

import math
from typing import cast

from ....renderer.commands import LightCommand
from ....components import FlickerStyle
from yukkuri_game.engine.components import LightSource
from yukkuri_game.engine.services.time_service import TimeService
from ..context import RenderContext


LAYER_EFFECTS = 3


class LightPass:
    """Renders dynamic lighting effects."""

    def __init__(self):
        self.lights_enabled = True

    def execute(self, context: RenderContext) -> None:
        """Executes the light pass."""
        if not self.lights_enabled:
            return

        for ent, transform, ix, iy, sx, sy in context.visible_render_data:
            light = context.world.try_get_component(ent, LightSource)
            if not light:
                continue

            radius = light.radius * context.camera.zoom

            # Culling optimization: skip lights off-screen
            if (
                sx + radius < 0
                or sx - radius > context.sw
                or sy + radius < 0
                or sy - radius > context.sh
            ):
                continue

            intensity = light.intensity
            if light.flicker_style != FlickerStyle.NONE:
                time_service = context.world.services.try_get(TimeService)
                time_elapsed = time_service.time_elapsed if time_service else 0.0

                if light.flicker_style == FlickerStyle.FIRE:
                    noise = (
                        math.sin(time_elapsed * 10.0 + ent) * 0.1
                        + math.sin(time_elapsed * 23.0 + ent * 2) * 0.05
                        + math.sin(time_elapsed * 47.0 + ent * 0.5) * 0.02
                    )
                    intensity = light.intensity * (1.0 + noise)
                elif light.flicker_style == FlickerStyle.PULSE:
                    intensity = light.intensity * (
                        0.8 + 0.2 * math.sin(time_elapsed * math.pi)
                    )

            color = light.color
            rgba_color: tuple[int, int, int, int]
            if len(color) == 3:
                rgba_color = (color[0], color[1], color[2], 255)
            else:
                rgba_color = cast(tuple[int, int, int, int], color)

            context.renderer.submit(
                LightCommand(
                    layer=LAYER_EFFECTS,
                    z_index=iy,
                    entity_id=ent,
                    position=(sx, sy),
                    radius=radius,
                    color=rgba_color,
                    intensity=intensity,
                    flicker_style=light.flicker_style,
                    soft_shadows=light.soft_shadows,
                    static=light.static,
                )
            )
