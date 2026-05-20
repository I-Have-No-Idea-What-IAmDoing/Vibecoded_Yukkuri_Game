"""
UI Pass.
"""

import pygame

from yukkuri_game.engine.renderer.commands import TextCommand
from yukkuri_game.engine.renderer.commands import SpriteCommand
from yukkuri_game.engine.components import FloatingText
from yukkuri_game.game.systems.rendering.context import RenderContext


LAYER_UI = 10


class UIPass:
    """Renders floating text and placement previews."""

    DEFAULT_SPRITE_SIZE = 64

    def execute(self, context: RenderContext) -> None:
        """Executes the UI pass."""
        self._process_floating_text(context)
        self._process_placement_preview(context)

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

    def _process_placement_preview(self, context: RenderContext) -> None:
        """Renders the placement preview (ghost sprite)."""
        # Lazy import to avoid circular dependency
        from yukkuri_game.game.services import InputService

        input_service = context.world.services.try_get(InputService)

        if not input_service or not input_service.is_placing:
            return

        image_name = input_service.place_image_name
        wx, wy = input_service.current_placement_pos
        sx, sy = context.camera.world_to_screen_fast(wx, wy)

        img = None
        if image_name:
            from yukkuri_game.engine.resource_manager import ResourceManager

            rm = context.world.services.try_get(ResourceManager)

            if rm:
                raw_surf = rm.load_image(image_name)
                if raw_surf:
                    place_type = input_service.place_type
                    entity_type = input_service.place_entity_type

                    sprite_width = self.DEFAULT_SPRITE_SIZE
                    sprite_height = self.DEFAULT_SPRITE_SIZE

                    if entity_type == "item" and place_type in rm.item_types:
                        item_data = rm.item_types[place_type]
                        sprite_width = getattr(item_data, "width", 32)
                        sprite_height = getattr(item_data, "height", 32)
                    elif entity_type == "yukkuri" and place_type in rm.yukkuri_types:
                        yuk_data = rm.yukkuri_types[place_type]
                        sprite_width = getattr(yuk_data, "width", 64)
                        sprite_height = getattr(yuk_data, "height", 64)

                        from yukkuri_game.game.yukkuri_constants import get_initial_scale

                        initial_scale = get_initial_scale()
                        sprite_width = int(sprite_width * initial_scale)
                        sprite_height = int(sprite_height * initial_scale)

                    raw_scale = context.camera.zoom
                    scale = round(raw_scale * 20.0) / 20.0

                    final_w = int(sprite_width * scale)
                    final_h = int(sprite_height * scale)

                    if final_w > 0 and final_h > 0:
                        img = pygame.transform.scale(raw_surf, (final_w, final_h))

        if not img:
            size = int(32 * context.camera.zoom)
            img = pygame.Surface((size, size), pygame.SRCALPHA)
            img.fill((0, 255, 0, 128))

        if img:
            context.renderer.submit(
                SpriteCommand(
                    layer=LAYER_UI,
                    z_index=99999,
                    image=img,
                    position=(sx, sy),
                    selected=False,
                    alpha=128,
                    cache_key=None,
                )
            )
