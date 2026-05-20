"""
Background Pass.
"""

from typing import Optional, Tuple
import pygame

from yukkuri_game.engine.renderer.constants import RenderConstants
from yukkuri_game.engine.renderer.commands import SpriteCommand
from yukkuri_game.game.systems.rendering.context import RenderContext


LAYER_BACKGROUND = 0


class BackgroundPass:
    """
    Handles rendering the background grid and terrain.
    Maintains its own background cache surface to minimize redrawing.
    """

    BACKGROUND_CACHE_MARGIN = 200

    def __init__(self):
        self._background_cache: Optional[pygame.Surface] = None
        self._background_cache_valid: bool = False
        self._last_camera_state: Optional[Tuple[int, int, float, int, int]] = None

    def execute(self, context: RenderContext) -> None:
        """Executes the background pass."""
        sw = context.sw
        sh = context.sh

        interp_zoom = context.camera._cached_zoom
        interp_cam_x = context.camera._cached_cam_x
        interp_cam_y = context.camera._cached_cam_y

        zoom_is_changing = abs(context.camera.zoom - context.camera.target_zoom) > 0.001

        if interp_zoom < 5.0:
            if zoom_is_changing:
                self._draw_grid(context, sw, sh)
                self._background_cache_valid = False
            else:
                should_invalidate = False
                if self._last_camera_state is None:
                    should_invalidate = True
                else:
                    cached_x, cached_y, cached_zoom, cached_sw, cached_sh = (
                        self._last_camera_state
                    )

                    if (
                        cached_zoom != interp_zoom
                        or cached_sw != sw
                        or cached_sh != sh
                    ):
                        should_invalidate = True
                    else:
                        diff_x = (cached_x - interp_cam_x) * interp_zoom
                        diff_y = (cached_y - interp_cam_y) * interp_zoom
                        margin = self.BACKGROUND_CACHE_MARGIN
                        if abs(diff_x) > margin or abs(diff_y) > margin:
                            should_invalidate = True

                if should_invalidate:
                    self._background_cache_valid = False
                    self._last_camera_state = (
                        int(interp_cam_x),
                        int(interp_cam_y),
                        interp_zoom,
                        sw,
                        sh,
                    )

                if not self._background_cache_valid or not self._background_cache:
                    self._rebuild_background_cache(context, sw, sh)

                if self._background_cache and self._last_camera_state is not None:
                    cached_cam_x, cached_cam_y, _, _, _ = self._last_camera_state

                    diff_x = (cached_cam_x - interp_cam_x) * interp_zoom
                    diff_y = (cached_cam_y - interp_cam_y) * interp_zoom

                    final_x = (sw // 2) + diff_x
                    final_y = (sh // 2) + diff_y

                    context.renderer.submit(
                        SpriteCommand(
                            layer=LAYER_BACKGROUND,
                            z_index=-9999,
                            image=self._background_cache,
                            position=(final_x, final_y),
                            selected=False,
                            alpha=255,
                            cache_key=None,
                        )
                    )

    def _rebuild_background_cache(
        self, context: RenderContext, sw: int, sh: int
    ) -> None:
        """Rebuilds the cached background surface (grid)."""
        margin = self.BACKGROUND_CACHE_MARGIN
        req_w, req_h = sw + margin * 2, sh + margin * 2

        if not self._background_cache or self._background_cache.get_size() != (
            req_w,
            req_h,
        ):
            self._background_cache = pygame.Surface((req_w, req_h), pygame.SRCALPHA)

        self._background_cache.fill((0, 0, 0, 0))

        if self._last_camera_state is None:
            return
        cached_cam_x, cached_cam_y, _, _, _ = self._last_camera_state

        self._draw_grid(
            context,
            sw,
            sh,
            target_surface=self._background_cache,
            override_cam_pos=(cached_cam_x, cached_cam_y),
        )
        self._background_cache_valid = True

    def _draw_grid(
        self,
        context: RenderContext,
        sw: int,
        sh: int,
        target_surface: Optional[pygame.Surface] = None,
        override_cam_pos: Optional[Tuple[float, float]] = None,
    ) -> None:
        """Draws the grid.

        Args:
            context (RenderContext): The current render context.
            sw (int): Screen width.
            sh (int): Screen height.
            target_surface (Optional[pygame.Surface]): The surface to draw
                onto. If None, draws to the screen via the backend.
            override_cam_pos (Optional[Tuple[float, float]]): Camera position
                to use instead of the active context camera position.
        """
        grid_size = RenderConstants.GRID_SIZE
        color = RenderConstants.GRID_COLOR
        cam_x = (
            override_cam_pos[0]
            if override_cam_pos
            else context.camera._cached_cam_x
        )
        cam_y = (
            override_cam_pos[1]
            if override_cam_pos
            else context.camera._cached_cam_y
        )
        zoom = context.camera._cached_zoom

        if target_surface:
            draw_w, draw_h = target_surface.get_size()
        else:
            draw_w, draw_h = sw, sh

        def world_to_target(
            wx: int | float, wy: int | float
        ) -> Tuple[float, float]:
            """Translates world coordinates to the drawing target space."""
            return (
                (wx - cam_x) * zoom + draw_w / 2,
                (wy - cam_y) * zoom + draw_h / 2,
            )

        start_col, end_col, start_row, end_row = (
            self._calculate_grid_bounds(
                context, draw_w, draw_h, grid_size, cam_x, cam_y
            )
        )

        if target_surface:
            for col in range(start_col, end_col):
                x = col * grid_size
                sx, _ = world_to_target(x, 0)
                pygame.draw.line(target_surface, color, (sx, 0), (sx, draw_h))
            for row in range(start_row, end_row):
                y = row * grid_size
                _, sy = world_to_target(0, y)
                pygame.draw.line(target_surface, color, (0, sy), (draw_w, sy))
        else:
            for col in range(start_col, end_col):
                x = col * grid_size
                if override_cam_pos:
                    sx, _ = world_to_target(x, 0)
                else:
                    sx, _ = context.camera.world_to_screen_fast(x, 0)
                context.renderer.backend.draw_line((sx, 0), (sx, draw_h), color)
            for row in range(start_row, end_row):
                y = row * grid_size
                if override_cam_pos:
                    _, sy = world_to_target(0, y)
                else:
                    _, sy = context.camera.world_to_screen_fast(0, y)
                context.renderer.backend.draw_line((0, sy), (draw_w, sy), color)

    def _calculate_grid_bounds(
        self,
        context: RenderContext,
        screen_w: int,
        screen_h: int,
        grid_size: int,
        cam_x: Optional[float] = None,
        cam_y: Optional[float] = None,
    ) -> Tuple[int, int, int, int]:
        """Helper to calculate visible grid lines."""
        if cam_x is not None and cam_y is not None:
            half_w = screen_w / 2
            half_h = screen_h / 2
            zoom = context.camera._cached_zoom

            start_x = (0 - half_w) / zoom + cam_x
            start_y = (0 - half_h) / zoom + cam_y
            end_x = (screen_w - half_w) / zoom + cam_x
            end_y = (screen_h - half_h) / zoom + cam_y
        else:
            start_x, start_y = context.camera.screen_to_world(0, 0, screen_w, screen_h)
            end_x, end_y = context.camera.screen_to_world(
                screen_w, screen_h, screen_w, screen_h
            )

        start_col = int(start_x // grid_size)
        end_col = int(end_x // grid_size) + 1
        start_row = int(start_y // grid_size)
        end_row = int(end_y // grid_size) + 1
        return start_col, end_col, start_row, end_row
