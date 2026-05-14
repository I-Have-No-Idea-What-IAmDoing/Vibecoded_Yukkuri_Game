"""
Shadow Pass.
"""

from ....renderer.constants import RenderConstants
from ....renderer.commands import ShadowCommand
from ....components import Flight, Sprite, VisualTransform
from ..context import RenderContext


LAYER_SHADOWS = 1


class ShadowPass:
    """Renders drop shadows for visible entities."""

    def execute(self, context: RenderContext) -> None:
        """Executes the shadow pass."""
        for ent, transform, ix, iy, sx, sy in context.visible_render_data:
            sprite = context.world.try_get_component(ent, Sprite)
            visual = context.world.try_get_component(ent, VisualTransform)

            if sprite and visual and visual.has_drop_shadow and visual.shadow_position:
                raw_scale = transform.scale * context.camera.zoom
                scale = round(raw_scale * 20.0) / 20.0

                feet_offset_y = sprite.height * scale * 0.5
                shadow_x, shadow_y = context.camera.world_to_screen_fast(
                    ix + visual.shadow_position.x,
                    iy + visual.shadow_position.y + feet_offset_y,
                )

                shadow_radius_x = sprite.width * scale * RenderConstants.SHADOW_SCALE_X
                shadow_radius_y = shadow_radius_x * RenderConstants.SHADOW_SCALE_Y

                flight = context.world.try_get_component(ent, Flight)
                shadow_alpha = 100
                if flight and flight.max_altitude > 0:
                    height_factor = min(
                        1.0, max(0.0, flight.altitude / flight.max_altitude)
                    )
                    height_factor = round(height_factor * 20.0) / 20.0

                    shadow_radius_x *= 1.0 - 0.4 * height_factor
                    shadow_radius_y *= 1.0 - 0.4 * height_factor
                    shadow_alpha = int(100 * (1.0 - 0.4 * height_factor))

                if shadow_radius_x > 0:
                    context.renderer.submit(
                        ShadowCommand(
                            layer=LAYER_SHADOWS,
                            z_index=iy,
                            position=(shadow_x, shadow_y),
                            radius=(shadow_radius_x, shadow_radius_y),
                            color=(0, 0, 0, shadow_alpha),
                        )
                    )
