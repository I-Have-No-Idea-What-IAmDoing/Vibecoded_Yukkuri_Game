"""
Sprite Pass.
"""

from ....renderer.commands import SpriteCommand
from ....components import Sprite, VisualTransform, Selectable
from ....yukkuri_components import Flight
from ..context import RenderContext


LAYER_ENTITIES = 2


class SpritePass:
    """Renders sprites for visible entities."""

    def execute(self, context: RenderContext) -> None:
        """Executes the sprite pass."""
        for ent, transform, ix, iy, sx, sy in context.visible_render_data:
            sprite = context.world.try_get_component(ent, Sprite)
            visual = context.world.try_get_component(ent, VisualTransform)

            if sprite and visual:
                raw_scale = transform.scale * context.camera.zoom
                scale = round(raw_scale * 20.0) / 20.0

                img = context.surface_cache.get_surface(
                    sprite.image_name,
                    sprite.current_frame,
                    sprite.frame_count,
                    sprite.width,
                    sprite.height,
                    scale,
                    transform.rotation,
                    sprite.flip_x,
                    sprite.flip_y,
                )

                if img:
                    selectable = context.world.try_get_component(ent, Selectable)
                    is_selected = selectable.selected if selectable else False

                    flight = context.world.try_get_component(ent, Flight)
                    flight_offset = flight.altitude if flight else 0.0

                    sprite_sy = sy - (
                        (visual.vertical_offset + flight_offset) * context.camera.zoom
                    )

                    cache_key = (
                        sprite.image_name,
                        sprite.current_frame,
                        round(scale, 3),
                        round(transform.rotation, 1),
                        sprite.flip_x,
                        sprite.flip_y,
                    )

                    context.renderer.submit(
                        SpriteCommand(
                            layer=LAYER_ENTITIES,
                            z_index=iy,
                            image=img,
                            position=(sx, sprite_sy),
                            selected=is_selected,
                            alpha=sprite.alpha,
                            cache_key=cache_key,
                        )
                    )
