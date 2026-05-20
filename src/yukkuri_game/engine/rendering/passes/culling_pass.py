"""
Culling Pass.
"""

from typing import List

from yukkuri_game.engine.components import Transform
from yukkuri_game.engine.protocols import ISpatialService
from ..context import RenderContext


class CullingPass:
    """
    Queries spatial partitioning to find visible entities,
    and pre-calculates interpolated screen positions for downstream passes.
    """

    VISIBILITY_BUFFER = 500.0

    def execute(self, context: RenderContext) -> None:
        """Executes the culling pass."""
        ents = self._get_visible_entities(context)
        context.visible_render_data.clear()

        for ent in ents:
            transform = context.world.try_get_component(ent, Transform)
            if not transform:
                continue

            ix = transform.x
            iy = transform.y
            if transform.prev_x is not None and transform.prev_y is not None:
                ix = transform.prev_x + (transform.x - transform.prev_x) * context.alpha
                iy = transform.prev_y + (transform.y - transform.prev_y) * context.alpha

            sx, sy = context.camera.world_to_screen_fast(ix, iy)
            context.visible_render_data.append((ent, transform, ix, iy, sx, sy))

    def _get_visible_entities(self, context: RenderContext) -> List[int]:
        """Returns entities visible on screen using spatial partitioning."""
        spatial_service = context.world.services.try_get(ISpatialService)
        if spatial_service:
            buffer = self.VISIBILITY_BUFFER
            start_x, start_y = context.camera.screen_to_world(
                0, 0, context.sw, context.sh
            )
            end_x, end_y = context.camera.screen_to_world(
                context.sw, context.sh, context.sw, context.sh
            )

            min_x = min(start_x, end_x) - buffer
            min_y = min(start_y, end_y) - buffer
            width = abs(end_x - start_x) + 2 * buffer
            height = abs(end_y - start_y) + 2 * buffer

            entities = spatial_service.get_entities_in_rect(min_x, min_y, width, height)
            return [e for e in entities if e >= 0]
        else:
            return [
                e for e, _ in context.world.get_components_tuple(Transform) if e >= 0
            ]
