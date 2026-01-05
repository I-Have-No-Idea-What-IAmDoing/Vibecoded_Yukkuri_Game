from typing import List, Tuple, Dict, Any, Optional
from collections import OrderedDict
import pygame
import pygame_light2d as pl2d
from .backend import RenderBackend
from .commands import RenderCommand, SpriteCommand, TextCommand, LightCommand, ShadowCommand, OccluderCommand
import types
import moderngl
import math

class Light2DBackend(RenderBackend):
    """Backend using pygame-light2d."""

    def __init__(self, screen: pygame.Surface, lighting_engine: pl2d.LightingEngine, texture_cache_max_size: int = 500):
        self.screen = screen
        self.engine = lighting_engine

        self.texture_cache: OrderedDict[int, Any] = OrderedDict()
        self.texture_cache_max_size = texture_cache_max_size
        self.font_cache = {}

        # State tracking for lights and occluders
        self.active_lights = {} # entity_id -> pl2d.PointLight
        self.active_hulls = {} # entity_id -> pl2d.Hull

        # We need to track which lights/hulls were updated this frame to remove stale ones
        self.updated_lights = set()
        self.updated_hulls = set()

    def clear(self, color: Tuple[int, int, int]) -> None:
        # Clear the background layer with the color
        # This prevents "hall of mirrors"
        bg_layer = self.engine._get_layer(pl2d.BACKGROUND)
        self.engine.graphics.clear(bg_layer, (color[0]/255, color[1]/255, color[2]/255, 1.0))

    def begin_frame(self) -> None:
        self.engine.clear(0, 0, 0, 0) # Clear lightmap
        self.updated_lights.clear()
        self.updated_hulls.clear()

    def end_frame(self) -> None:
        # Cleanup stale lights
        to_remove_lights = []
        for eid, light in self.active_lights.items():
            if eid not in self.updated_lights:
                self.engine.lights.remove(light)
                to_remove_lights.append(eid)
        for eid in to_remove_lights:
            del self.active_lights[eid]

        # Cleanup stale hulls
        to_remove_hulls = []
        for eid, hull in self.active_hulls.items():
            if eid not in self.updated_hulls:
                if hull in self.engine.hulls:
                    self.engine.hulls.remove(hull)
                to_remove_hulls.append(eid)
        for eid in to_remove_hulls:
            del self.active_hulls[eid]

        self.engine.render()

    def _get_texture(self, surface: pygame.Surface) -> Any:
        # Use surface ID as key.
        # This assumes surface objects are persistent or reused by SurfaceCache.
        key = id(surface)

        if key in self.texture_cache:
            self.texture_cache.move_to_end(key)
            return self.texture_cache[key]

        tex = self.engine.surface_to_texture(surface)
        self.texture_cache[key] = tex

        # LRU Eviction
        if len(self.texture_cache) > self.texture_cache_max_size:
             _, old_tex = self.texture_cache.popitem(last=False)
             old_tex.release()

        return tex

    def draw_sprite(self, cmd: SpriteCommand) -> None:
        tex = self._get_texture(cmd.image)

        dest_rect = pygame.Rect(0, 0, cmd.image.get_width(), cmd.image.get_height())
        dest_rect.center = (int(cmd.position[0]), int(cmd.position[1]))

        # Render to BACKGROUND layer (standard sprites)
        self.engine.render_texture(
            tex,
            pl2d.BACKGROUND,
            dest_rect,
            pygame.Rect(0, 0, tex.width, tex.height)
        )

        if cmd.selected:
             self.engine.graphics.render_rectangle(
                self.engine._get_layer(pl2d.BACKGROUND),
                (1.0, 1.0, 0.0, 1.0),
                dest_rect.center,
                dest_rect.width,
                dest_rect.height,
                0,
                False
             )

    def draw_text(self, cmd: TextCommand) -> None:
        # Font rendering creates a surface
        font = self._get_font(cmd.size, cmd.font_name)
        surf = font.render(cmd.text, True, cmd.color)
        if cmd.alpha < 255:
            surf.set_alpha(cmd.alpha)

        tex = self.engine.surface_to_texture(surf) # One-off texture
        dest_rect = surf.get_rect(center=(int(cmd.position[0]), int(cmd.position[1])))

        self.engine.render_texture(
            tex,
            pl2d.FOREGROUND, # GUI usually on top
            dest_rect,
            pygame.Rect(0, 0, tex.width, tex.height)
        )
        tex.release() # Release immediately as text changes often

    def draw_shadow(self, cmd: ShadowCommand) -> None:
        # Shadows are also drawn to background?
        # TODO: Caching shadow textures is harder because we create them on fly in backend usually.
        # But here we create surface every time.
        s = pygame.Surface((cmd.radius[0]*2, cmd.radius[1]*2), pygame.SRCALPHA)
        pygame.draw.ellipse(s, cmd.color, s.get_rect())
        tex = self.engine.surface_to_texture(s)

        dest_rect = s.get_rect(center=(int(cmd.position[0]), int(cmd.position[1])))
        self.engine.render_texture(
            tex,
            pl2d.BACKGROUND,
            dest_rect,
            pygame.Rect(0, 0, tex.width, tex.height)
        )
        tex.release()

    def draw_light(self, cmd: LightCommand) -> None:
        self.updated_lights.add(cmd.entity_id)

        # Convert color to 0-1 range
        col = (cmd.color[0]/255, cmd.color[1]/255, cmd.color[2]/255, cmd.color[3]/255)

        if cmd.entity_id in self.active_lights:
            l = self.active_lights[cmd.entity_id]
            l.position = cmd.position
            l.radius = cmd.radius
            l.power = cmd.intensity
            l._color = col
        else:
            l = pl2d.PointLight(cmd.position, cmd.intensity, cmd.radius)
            l.set_color(*cmd.color) # This expects 0-255 or 0-1? pl2d usually takes 0-255 in set_color wrapper?
            # Looking at source, set_color usually normalizes.
            # But here I manually set _color above, let's use the public API.
            l.set_color(*cmd.color) # This takes r,g,b,a ints usually?
            # pl2d.PointLight.set_color(r, g, b, a)
            self.engine.lights.append(l)
            self.active_lights[cmd.entity_id] = l

    def draw_occluder(self, cmd: OccluderCommand) -> None:
        self.updated_hulls.add(cmd.entity_id)

        # Hull vertices must be list of (x,y)
        if cmd.entity_id in self.active_hulls:
            # We need to update vertices.
            # Hull doesn't support update?
            # If not, remove and add.
             self.engine.hulls.remove(self.active_hulls[cmd.entity_id])

        h = pl2d.Hull(cmd.vertices)
        self.engine.hulls.append(h)
        self.active_hulls[cmd.entity_id] = h

    def set_ambient_light(self, color: Tuple[int, int, int, int]) -> None:
        self.engine.set_ambient(color)

    def draw_line(self, start: Tuple[float, float], end: Tuple[float, float], color: Tuple[int, int, int], width: int = 1) -> None:
        # Draw to background
        self.engine.graphics.render_lines(
            self.engine._get_layer(pl2d.BACKGROUND),
            (color[0]/255, color[1]/255, color[2]/255, 1.0),
            [start, end],
            width,
            False
        )

    def _get_font(self, size: int, name: str = None) -> pygame.font.Font:
        key = (size, name)
        if key not in self.font_cache:
            self.font_cache[key] = pygame.font.SysFont(name, size)
        return self.font_cache[key]
