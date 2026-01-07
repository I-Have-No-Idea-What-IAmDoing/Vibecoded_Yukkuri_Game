from typing import Tuple, Any, List, Optional
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

class NativeLightBackend(RenderBackend):
    """
    Backend using native Pygame drawing and custom shadow casting.
    """

    def __init__(self, screen: pygame.Surface):
        self.screen = screen

        # State
        self.ambient_color = (20, 20, 20, 255)  # Default ambient
        self.commands: List[Any] = []
        self.lights: List[LightCommand] = []
        self.occluders: List[OccluderCommand] = []

        self.shadow_caster = ShadowCaster()

        # Caches
        self.font_cache = {}
        self.light_texture_cache = {} # (radius, color) -> Surface

        # Surfaces
        self.lightmap_surface: Optional[pygame.Surface] = None
        self.occlusion_mask: Optional[pygame.Surface] = None

    def clear(self, color: Tuple[int, int, int]) -> None:
        self.screen.fill(color)

    def begin_frame(self) -> None:
        self.commands.clear()
        self.lights.clear()
        self.occluders.clear()

        # Ensure surfaces match screen size
        w, h = self.screen.get_size()
        if self.lightmap_surface is None or self.lightmap_surface.get_size() != (w, h):
            self.lightmap_surface = pygame.Surface((w, h))

        # We don't necessarily clear here as we redraw everything

    def end_frame(self) -> None:
        w, h = self.screen.get_size()

        # 1. Render all non-light commands (Sprites, Shadows, Text)
        # Sort by layer and z-index
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
            # Fill with ambient
            self.lightmap_surface.fill(self.ambient_color)

            # Prepare occluders (list of polygons)
            occluder_polys = []
            for occ in self.occluders:
                occluder_polys.append(occ.vertices)

            # Render each light
            for light in self.lights:
                self._render_light(light, occluder_polys)

            # Blend lightmap onto screen
            # MULTIPLY mode: Result = Screen * Lightmap / 255
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
        self.occluders.append(cmd)

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

        if cmd.selected:
            # Draw selection outline
            pygame.draw.rect(self.screen, (255, 255, 0), dest_rect.inflate(4, 4), 2)

        self.screen.blit(cmd.image, dest_rect)

    def _render_text(self, cmd: TextCommand) -> None:
        font = self._get_font(cmd.size, cmd.font_name)
        surf = font.render(cmd.text, True, cmd.color)
        if cmd.alpha < 255:
            surf.set_alpha(cmd.alpha)

        dest_rect = surf.get_rect(center=(int(cmd.position[0]), int(cmd.position[1])))
        self.screen.blit(surf, dest_rect)

    def _render_shadow(self, cmd: ShadowCommand) -> None:
        # Simple ellipse shadow
        rx, ry = int(cmd.radius[0]), int(cmd.radius[1])
        if rx <= 0 or ry <= 0:
            return

        s = pygame.Surface((rx * 2, ry * 2), pygame.SRCALPHA)
        pygame.draw.ellipse(s, cmd.color, s.get_rect())

        dest_rect = s.get_rect(center=(int(cmd.position[0]), int(cmd.position[1])))
        self.screen.blit(s, dest_rect)

    def _render_light(self, light: LightCommand, occluders: List[List[Tuple[float, float]]]) -> None:
        # 1. Calculate Visibility Polygon
        poly_points = self.shadow_caster.calculate_visibility_polygon(
            light.position, light.radius, occluders
        )

        if not poly_points:
            return

        # 2. Prepare Light Texture (Gradient)
        # Create or fetch cached light texture
        key = (int(light.radius), light.color, light.intensity)
        # TODO: handle intensity scaling

        # We need a surface that covers the light area
        r = int(light.radius)
        if r <= 0: return

        light_surf = self._get_light_texture(r, light.color, light.intensity)

        # 3. Mask the texture with the polygon
        # Create a mask surface
        mask = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        # mask.fill((0, 0, 0, 0)) # Transparent

        # Draw polygon on mask (white, opaque)
        # The polygon points are in screen space. We need them local to the light surface.
        lx, ly = light.position
        local_poly = [(px - (lx - r), py - (ly - r)) for px, py in poly_points]

        if len(local_poly) > 2:
            pygame.draw.polygon(mask, (255, 255, 255, 255), local_poly)

        # 4. Apply mask to light texture
        # We want: Output = LightTexture * Mask
        # Pygame 2.0+ supports BLEND_RGBA_MULT

        final_light = light_surf.copy()
        final_light.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        # 5. Add to Lightmap
        # Position on lightmap
        dest_pos = (lx - r, ly - r)
        self.lightmap_surface.blit(final_light, dest_pos, special_flags=pygame.BLEND_ADD)


    def _get_light_texture(self, radius: int, color: Tuple[int, int, int, int], intensity: float) -> pygame.Surface:
        # Cache key
        # Truncate color to int
        c = (int(color[0]), int(color[1]), int(color[2]))
        key = (radius, c, int(intensity * 100))

        if key in self.light_texture_cache:
            return self.light_texture_cache[key]

        # Create radial gradient
        surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)

        # Simple radial gradient: Center is Color * Intensity, Edge is Transparent
        # We can simulate this by drawing multiple circles or per-pixel.
        # Per-pixel is slow in Python.
        # Use a pre-generated gradient image or draw concentric circles?
        # Better: create a grayscale radial gradient and tint it.

        # For now, let's just draw a simple fuzzy circle using `pygame.draw.circle` with alpha?
        # Pygame primitives don't support gradients.
        # But we can hack it with multiple alpha circles.

        # Center color
        center_alpha = min(255, int(255 * intensity))

        # Draw ~10 circles
        steps = 20
        for i in range(steps):
            frac = i / steps
            r = int(radius * (1 - frac))
            if r <= 0: continue
            # Quadratic falloff looks better
            alpha = int(center_alpha * (frac ** 2)) / steps
            # This is additive logic, hard to do with alpha circles.

        # Alternate: blit a specialized radial gradient image asset.
        # Or: Use numpy/surfarray (fast).
        # Fallback: Just a solid circle with alpha falloff?

        # Let's use a simple approach: 3-step gradient
        # Inner: Bright
        # Middle: Dim
        # Outer: Faint

        # To make it look decent without slow generation, let's iterate
        # But `pygame.draw.circle` with alpha doesn't blend well on empty surface unless we handle it right.

        # Optimized approach: create one large white radial gradient once, scale and tint it.
        # But for now, let's implement a simple generator.

        center = (radius, radius)

        # Very simple "soft" light:
        # Draw a few circles with low alpha
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
