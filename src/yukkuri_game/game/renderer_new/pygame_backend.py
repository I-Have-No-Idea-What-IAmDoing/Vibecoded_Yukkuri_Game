from typing import Tuple, Any, List, Optional, Dict
import pygame
import math
from .backend import RenderBackend
from .commands import (
    SpriteCommand,
    TextCommand,
    LightCommand,
    ShadowCommand,
    OccluderCommand,
)
from .shadow_caster import ShadowCaster

class PygameBackend(RenderBackend):
    """
    Software renderer backend using native Pygame drawing and custom shadow casting.
    """

    def __init__(self, screen: pygame.Surface):
        self.screen = screen

        # State
        self.ambient_color = (20, 20, 20, 255)
        self.commands: List[Any] = []
        self.lights: List[LightCommand] = []

        # Occluders stored as: (aabb_tuple, vertices_list, entity_id, static_flag)
        self.occluders: List[Tuple[Tuple[float, float, float, float], List[Tuple[float, float]], int, bool]] = []

        self.shadow_caster = ShadowCaster()

        # Caches
        self.font_cache = {}
        self.light_texture_cache = {} # (radius, color) -> Surface
        self.shadow_surface_cache = {} # (rx, ry, color) -> Surface

        # Shadow Cache: entity_id -> (signature, polygon_points)
        # signature = (x, y, radius, tuple(sorted_static_ids))
        self.shadow_cache: Dict[int, Tuple[Tuple, List[Tuple[float, float]]]] = {}

        # Surfaces
        self.lightmap_surface: Optional[pygame.Surface] = None

    def clear(self, color: Tuple[int, int, int]) -> None:
        self.screen.fill(color)

    def begin_frame(self) -> None:
        self.commands.clear()
        self.lights.clear()
        self.occluders.clear()

        w, h = self.screen.get_size()
        if self.lightmap_surface is None or self.lightmap_surface.get_size() != (w, h):
            self.lightmap_surface = pygame.Surface((w, h))

    def end_frame(self) -> None:
        w, h = self.screen.get_size()

        # 1. Render all non-light commands
        self.commands.sort(key=lambda cmd: (cmd.layer, cmd.z_index))

        for cmd in self.commands:
            if isinstance(cmd, SpriteCommand):
                self._render_sprite(cmd)
            elif isinstance(cmd, TextCommand):
                self._render_text(cmd)
            elif isinstance(cmd, ShadowCommand):
                self._render_shadow(cmd)

        # 2. Render Lighting
        if self.lightmap_surface:
            self.lightmap_surface.fill(self.ambient_color)

            # Render each light
            for light in self.lights:
                self._render_light(light)

            self.screen.blit(self.lightmap_surface, (0, 0), special_flags=pygame.BLEND_MULT)

    def draw_sprite(self, cmd: SpriteCommand) -> None:
        self.commands.append(cmd)

    def draw_text(self, cmd: TextCommand) -> None:
        self.commands.append(cmd)

    def draw_shadow(self, cmd: ShadowCommand) -> None:
        self.commands.append(cmd)

    def draw_light(self, cmd: LightCommand) -> None:
        self.lights.append(cmd)

    def draw_occluder(self, cmd: OccluderCommand) -> None:
        # Calculate AABB immediately
        if not cmd.vertices:
            return

        xs = [v[0] for v in cmd.vertices]
        ys = [v[1] for v in cmd.vertices]
        aabb = (min(xs), max(xs), min(ys), max(ys))

        self.occluders.append((aabb, cmd.vertices, cmd.entity_id, cmd.static))

    def set_ambient_light(self, color: Tuple[int, int, int, int]) -> None:
        self.ambient_color = color

    def draw_line(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        color: Tuple[int, int, int],
        width: int = 1,
    ) -> None:
        pygame.draw.line(self.screen, color, start, end, width)

    # Internal Rendering Methods

    def _render_sprite(self, cmd: SpriteCommand) -> None:
        dest_rect = cmd.image.get_rect()
        dest_rect.center = (int(cmd.position[0]), int(cmd.position[1]))

        if cmd.alpha < 255:
            cmd.image.set_alpha(cmd.alpha)

        self.screen.blit(cmd.image, dest_rect)

        if cmd.selected:
            pygame.draw.rect(self.screen, (255, 255, 0), dest_rect.inflate(4, 4), 2)


    def _render_text(self, cmd: TextCommand) -> None:
        font = self._get_font(cmd.size, cmd.font_name)
        surf = font.render(cmd.text, True, cmd.color)
        if cmd.alpha < 255:
            surf.set_alpha(cmd.alpha)

        dest_rect = surf.get_rect(center=(int(cmd.position[0]), int(cmd.position[1])))
        self.screen.blit(surf, dest_rect)

    def _render_shadow(self, cmd: ShadowCommand) -> None:
        rx, ry = int(cmd.radius[0]), int(cmd.radius[1])
        if rx <= 0 or ry <= 0:
            return

        key = (rx, ry, cmd.color)
        if key not in self.shadow_surface_cache:
            s = pygame.Surface((rx * 2, ry * 2), pygame.SRCALPHA)
            pygame.draw.ellipse(s, cmd.color, s.get_rect())
            self.shadow_surface_cache[key] = s

        s = self.shadow_surface_cache[key]
        dest_rect = s.get_rect(center=(int(cmd.position[0]), int(cmd.position[1])))
        self.screen.blit(s, dest_rect)

    def _render_light(self, light: LightCommand) -> None:
        # 1. Identify relevant occluders and check cache
        lx, ly = light.position
        r = light.radius

        # AABB for light
        min_x, max_x = lx - r, lx + r
        min_y, max_y = ly - r, ly + r

        relevant_static_ids = []
        has_dynamic = False
        active_occluders = []

        for (aabb, poly, eid, static) in self.occluders:
            omin_x, omax_x, omin_y, omax_y = aabb

            # AABB Overlap Check
            if (omax_x < min_x or omin_x > max_x or
                omax_y < min_y or omin_y > max_y):
                continue

            active_occluders.append((aabb, poly))

            if static:
                relevant_static_ids.append(eid)
            else:
                has_dynamic = True

        poly_points = None

        # Try Cache
        if not has_dynamic:
            relevant_static_ids.sort()
            # Quantize position/radius to improve cache hit rate for floating point jitters
            # 0.01 precision
            qx = round(lx, 2)
            qy = round(ly, 2)
            qr = round(r, 2)

            signature = (qx, qy, qr, tuple(relevant_static_ids))

            if light.entity_id in self.shadow_cache:
                cached_sig, cached_poly = self.shadow_cache[light.entity_id]
                if cached_sig == signature:
                    poly_points = cached_poly

            if poly_points is None:
                # Recalculate
                poly_points = self.shadow_caster.calculate_visibility_polygon(
                    light.position, light.radius, active_occluders
                )
                self.shadow_cache[light.entity_id] = (signature, poly_points)
        else:
            # Dynamic objects present, always recalculate (and don't cache, or don't use cache)
            poly_points = self.shadow_caster.calculate_visibility_polygon(
                light.position, light.radius, active_occluders
            )

        if not poly_points:
            return

        # 2. Prepare Light Texture
        ri = int(r)
        if ri <= 0: return

        light_surf = self._get_light_texture(ri, light.color, light.intensity)

        # 3. Mask the texture
        mask = pygame.Surface((ri * 2, ri * 2), pygame.SRCALPHA)

        local_poly = [(px - (lx - r), py - (ly - r)) for px, py in poly_points]

        if len(local_poly) > 2:
            pygame.draw.polygon(mask, (255, 255, 255, 255), local_poly)

        final_light = light_surf.copy()
        final_light.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        # 4. Add to Lightmap
        dest_pos = (lx - r, ly - r)
        self.lightmap_surface.blit(final_light, dest_pos, special_flags=pygame.BLEND_ADD)


    def _get_light_texture(self, radius: int, color: Tuple[int, int, int, int], intensity: float) -> pygame.Surface:
        c = (int(color[0]), int(color[1]), int(color[2]))
        key = (radius, c, int(intensity * 100))

        if key in self.light_texture_cache:
            return self.light_texture_cache[key]

        surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        center = (radius, radius)

        # Simple Gradient
        current_alpha = max(10, int(30 * intensity))
        pygame.draw.circle(surf, c + (current_alpha,), center, radius)
        pygame.draw.circle(surf, c + (current_alpha,), center, int(radius * 0.7))
        pygame.draw.circle(surf, c + (current_alpha,), center, int(radius * 0.4))
        pygame.draw.circle(surf, c + (current_alpha,), center, int(radius * 0.2))

        self.light_texture_cache[key] = surf
        return surf

    def _get_font(self, size: int, name: str = None) -> pygame.font.Font:
        key = (size, name)
        if key not in self.font_cache:
            self.font_cache[key] = pygame.font.SysFont(name, size)
        return self.font_cache[key]
