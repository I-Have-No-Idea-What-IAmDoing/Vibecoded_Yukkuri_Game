from typing import Tuple, Any
from collections import OrderedDict
import pygame
import pygame_light2d as pl2d
from .backend import RenderBackend
from .commands import (
    SpriteCommand,
    TextCommand,
    LightCommand,
    ShadowCommand,
    OccluderCommand,
)


class OpenGLBackend(RenderBackend):
    """
    Hardware-accelerated renderer backend using pygame_light2d.
    Manages convertion of Pygame surfaces to OpenGL textures and batch rendering.

    DEPRECATED: This backend is currently broken and should not be used.
    Use PygameBackend (Software Renderer) instead.
    """

    def __init__(self, screen: pygame.Surface, engine: pl2d.LightingEngine):
        import warnings

        warnings.warn(
            "OpenGLBackend is deprecated and currently broken. Use PygameBackend instead.",
            DeprecationWarning,
            stacklevel=2,
        )

        self.screen = screen
        self.engine = engine

        # Cache for textures: cache_key (hashable) -> pl2d.Texture
        self.texture_cache: OrderedDict[Any, Any] = OrderedDict()
        self.texture_cache_max_size = 500  # Hardcoded as parameter was removed

        self.font_cache = {}
        self.shadow_surface_cache = {}  # Cache for Pygame Surfaces for shadows (not Textures, to avoid recreation)
        self.shadow_texture_cache = OrderedDict()  # Cache for Shadow Textures

        # State tracking for lights and occluders
        self.active_lights = {}  # entity_id -> pl2d.PointLight
        self.active_hulls = {}  # entity_id -> pl2d.Hull

        # We need to track which lights/hulls were updated this frame to remove stale ones
        self.updated_lights = set()
        self.updated_hulls = set()

        # Track static hulls separately to avoid recreation/check
        # entity_id -> vertices tuple
        self.static_hull_vertices = {}

        self._clear_color = (0, 0, 0)
        self.screen_rect = self.screen.get_rect()

    def clear(self, color: Tuple[int, int, int]) -> None:
        self._clear_color = color

    def begin_frame(self) -> None:
        # Clear lightmap and background with the stored clear color
        self.engine.clear(*self._clear_color, 255)
        self.updated_lights.clear()
        self.updated_hulls.clear()
        self.screen_rect = self.screen.get_rect()

    def end_frame(self) -> None:
        # Cleanup stale lights
        to_remove_lights = []
        for eid, light in self.active_lights.items():
            if eid not in self.updated_lights:
                if light in self.engine.lights:
                    self.engine.lights.remove(light)
                to_remove_lights.append(eid)
        for eid in to_remove_lights:
            del self.active_lights[eid]

        # Cleanup stale hulls from internal dict
        to_remove_hulls = []
        for eid, hull in self.active_hulls.items():
            if eid not in self.updated_hulls:
                # Also remove from static tracking if present
                if eid in self.static_hull_vertices:
                    del self.static_hull_vertices[eid]
                to_remove_hulls.append(eid)
        for eid in to_remove_hulls:
            del self.active_hulls[eid]

        # Rebuild engine hull list (O(M))
        # Note: If hulls didn't change, we could skip this, but detecting that is harder.
        # Given user feedback, rebuilding is better than removing individually in loop.
        self.engine.hulls[:] = list(self.active_hulls.values())

        self.engine.render()

    def _get_texture(self, surface: pygame.Surface, cache_key: Any) -> Any:
        if cache_key in self.texture_cache:
            self.texture_cache.move_to_end(cache_key)
            return self.texture_cache[cache_key]

        tex = self.engine.surface_to_texture(surface)
        self.texture_cache[cache_key] = tex

        # LRU Eviction
        if len(self.texture_cache) > self.texture_cache_max_size:
            _, old_tex = self.texture_cache.popitem(last=False)
            old_tex.release()

        return tex

    def draw_sprite(self, cmd: SpriteCommand) -> None:
        # If cache_key is provided, use it. Otherwise fall back to id(surface) (less safe but fallback)
        key = cmd.cache_key if cmd.cache_key is not None else id(cmd.image)
        tex = self._get_texture(cmd.image, key)

        dest_rect = pygame.Rect(0, 0, cmd.image.get_width(), cmd.image.get_height())
        dest_rect.center = (int(cmd.position[0]), int(cmd.position[1]))

        # Render to BACKGROUND layer (standard sprites)
        self.engine.render_texture(
            tex, pl2d.BACKGROUND, dest_rect, pygame.Rect(0, 0, tex.width, tex.height)
        )

        if cmd.selected:
            self.engine.graphics.render_rectangle(
                self.engine._get_layer(pl2d.BACKGROUND),
                (1.0, 1.0, 0.0, 1.0),
                dest_rect.center,
                dest_rect.width,
                dest_rect.height,
                0,
                False,
            )

    def draw_text(self, cmd: TextCommand) -> None:
        # Font rendering creates a surface
        font = self._get_font(cmd.size, cmd.font_name)
        surf = font.render(cmd.text, True, cmd.color)
        if cmd.alpha < 255:
            surf.set_alpha(cmd.alpha)

        tex = self.engine.surface_to_texture(surf)  # One-off texture
        dest_rect = surf.get_rect(center=(int(cmd.position[0]), int(cmd.position[1])))

        self.engine.render_texture(
            tex,
            pl2d.FOREGROUND,  # GUI usually on top
            dest_rect,
            pygame.Rect(0, 0, tex.width, tex.height),
        )
        tex.release()  # Release immediately as text changes often

    def draw_shadow(self, cmd: ShadowCommand) -> None:
        # Use cache for shadow textures based on radius and color
        key = (int(cmd.radius[0]), int(cmd.radius[1]), cmd.color)

        if key in self.shadow_texture_cache:
            tex = self.shadow_texture_cache[key]
            self.shadow_texture_cache.move_to_end(key)
        else:
            rx, ry = int(cmd.radius[0]), int(cmd.radius[1])
            s = pygame.Surface((rx * 2, ry * 2), pygame.SRCALPHA)
            pygame.draw.ellipse(s, cmd.color, s.get_rect())
            tex = self.engine.surface_to_texture(s)
            self.shadow_texture_cache[key] = tex

            # LRU for shadows
            if len(self.shadow_texture_cache) > 100:  # Arbitrary limit
                _, old_tex = self.shadow_texture_cache.popitem(last=False)
                old_tex.release()

        dest_rect = pygame.Rect(0, 0, tex.width, tex.height)
        dest_rect.center = (int(cmd.position[0]), int(cmd.position[1]))

        self.engine.render_texture(
            tex, pl2d.BACKGROUND, dest_rect, pygame.Rect(0, 0, tex.width, tex.height)
        )
        # Do not release texture here as it is cached

    def draw_light(self, cmd: LightCommand) -> None:
        # Frustum Culling: Check if light is within screen bounds
        # Expand bounds by radius
        light_rect = pygame.Rect(
            cmd.position[0] - cmd.radius,
            cmd.position[1] - cmd.radius,
            cmd.radius * 2,
            cmd.radius * 2,
        )

        if not self.screen_rect.colliderect(light_rect):
            # Light is off-screen, ignore it.
            # It will be cleaned up in end_frame if it was previously active.
            return

        self.updated_lights.add(cmd.entity_id)

        # Snap position to int to match sprite rendering (avoid jitter)
        pos = (int(cmd.position[0]), int(cmd.position[1]))

        if cmd.entity_id in self.active_lights:
            l = self.active_lights[cmd.entity_id]
            l.position = pos
            l.radius = cmd.radius
            l.power = cmd.intensity
            l.set_color(*cmd.color)
        else:
            l = pl2d.PointLight(pos, cmd.intensity, cmd.radius)
            l.set_color(*cmd.color)
            self.engine.lights.append(l)
            self.active_lights[cmd.entity_id] = l

    def draw_occluder(self, cmd: OccluderCommand) -> None:
        # Frustum Culling: Check if occluder is visible
        min_x = min(v[0] for v in cmd.vertices)
        max_x = max(v[0] for v in cmd.vertices)
        min_y = min(v[1] for v in cmd.vertices)
        max_y = max(v[1] for v in cmd.vertices)

        occluder_rect = pygame.Rect(min_x, min_y, max_x - min_x, max_y - min_y)
        if not self.screen_rect.colliderect(occluder_rect):
            return

        self.updated_hulls.add(cmd.entity_id)

        # Static Optimization
        if cmd.static:
            vertices_tuple = tuple(tuple(v) for v in cmd.vertices)
            if cmd.entity_id in self.static_hull_vertices:
                # Check if changed (shouldn't for static, but maybe camera moved so screen coords changed?)
                # Wait, screen coordinates WILL change if camera moves.
                # So "static" refers to world space. But we receive screen space vertices.
                # Thus, we must recreate the hull if screen coordinates changed.
                # However, recalculating if vertices changed is still good.
                if self.static_hull_vertices[cmd.entity_id] == vertices_tuple:
                    # No change, reuse existing hull
                    return

            self.static_hull_vertices[cmd.entity_id] = vertices_tuple

        # Snap vertices to int to match sprite rendering
        vertices = [(int(x), int(y)) for x, y in cmd.vertices]

        h = pl2d.Hull(vertices)
        self.active_hulls[cmd.entity_id] = h

    def set_ambient_light(self, color: Tuple[int, int, int, int]) -> None:
        self.engine.set_ambient(*color)

    def draw_line(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        color: Tuple[int, int, int],
        width: int = 1,
    ) -> None:
        # Draw to background
        self.engine.graphics.render_lines(
            self.engine._get_layer(pl2d.BACKGROUND),
            (color[0] / 255, color[1] / 255, color[2] / 255, 1.0),
            [start, end],
            width,
            False,
        )

    def _get_font(self, size: int, name: str = None) -> pygame.font.Font:
        key = (size, name)
        if key not in self.font_cache:
            self.font_cache[key] = pygame.font.SysFont(name, size)
        return self.font_cache[key]
