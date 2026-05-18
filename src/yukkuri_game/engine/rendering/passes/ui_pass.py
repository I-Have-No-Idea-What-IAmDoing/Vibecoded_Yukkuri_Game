"""
UI Pass (Engine Version).
"""

from ...renderer.commands import TextCommand
from ...components import FloatingText
from ..context import RenderContext


LAYER_UI = 10


class UIPass:
    """Renders generic UI elements like floating text."""

    def execute(self, context: RenderContext) -> None:
        """Executes the UI pass."""
        self._process_floating_text(context)

    def _process_floating_text(self, context: RenderContext) -> None:
        """Processes floating text components for visible entities."""
        for ent, transform, ix, iy, sx, sy in context.visible_render_data:
            text = context.world.try_get_component(ent, FloatingText)
            if not text:
                continue

            if 0 <= sx <= context.sw and 0 <= sy <= context.sh:
                alpha_val = 255
                if text.max_lifetime > 0:
                    alpha_val = int(255 * (text.lifetime / text.max_lifetime))

                context.renderer.submit(
                    TextCommand(
                        layer=LAYER_UI,
                        z_index=transform.y + 1000,
                        text=text.text,
                        position=(sx, sy),
                        size=text.size,
                        color=text.color,
                        alpha=alpha_val,
                    )
                )
