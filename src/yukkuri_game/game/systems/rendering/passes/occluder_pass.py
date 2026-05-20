"""
Occluder Pass.
"""

from yukkuri_game.engine.renderer.commands import OccluderCommand
from yukkuri_game.engine.renderer.geometry_utils import GeometryUtils
from yukkuri_game.engine.components import Occluder
from yukkuri_game.engine.components import Sprite
from yukkuri_game.engine.components import PhysicsBody
from yukkuri_game.engine.components import LightSource
from yukkuri_game.game.systems.rendering.context import RenderContext


LAYER_BACKGROUND = 0


class OccluderPass:
    """Renders shadow-casting occluder geometry."""

    def execute(self, context: RenderContext) -> None:
        """Executes the occluder pass."""
        for ent, transform, ix, iy, sx, sy in context.visible_render_data:
            occluder = context.world.try_get_component(ent, Occluder)
            if not occluder:
                continue

            # Skip self-shadowing: don't render occluder if entity has active light.
            light = context.world.try_get_component(ent, LightSource)
            if light and light.intensity > 0:
                continue

            sprite = context.world.try_get_component(ent, Sprite)
            body = context.world.try_get_component(ent, PhysicsBody)

            world_verts = GeometryUtils.get_occluder_vertices(
                ent, transform, occluder, sprite, body, override_x=ix, override_y=iy
            )

            if len(world_verts) < 3:
                continue

            zoom_x = context.camera._cached_zoom_x or 1.0
            zoom_y = context.camera._cached_zoom_y or 1.0
            off_x = context.camera._cached_offset_x or 0.0
            off_y = context.camera._cached_offset_y or 0.0

            screen_verts = [
                (wx * zoom_x + off_x, wy * zoom_y + off_y) for wx, wy in world_verts
            ]

            context.renderer.submit(
                OccluderCommand(
                    layer=LAYER_BACKGROUND,
                    z_index=0,
                    entity_id=ent,
                    vertices=screen_verts,
                    static=occluder.static,
                )
            )
