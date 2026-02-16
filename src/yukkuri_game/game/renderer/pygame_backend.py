"""
Pygame Renderer Backend.

This module provides the `PygameBackend` implementation of the `RenderBackend` protocol.
It uses native Pygame drawing functions and the custom `SoftwareLightingEngine` for
lighting and shadows.
"""

from collections import OrderedDict

import pygame

from .backend import RenderBackend
from .commands import (
    LightCommand,
    OccluderCommand,
    ShadowCommand,
    SpriteCommand,
    TextCommand,
)
from .software_lighting import SoftwareLightingEngine


class PygameBackend(RenderBackend):
    """
    Software renderer backend using native Pygame drawing and custom shadow casting.

    Attributes:
        screen (pygame.Surface): The main display surface.
        ambient_color (tuple[int, int, int, int]): The ambient light color.
        lighting_engine (SoftwareLightingEngine): The lighting system.
        font_cache (dict): Cache of Pygame fonts.
        shadow_surface_cache (dict): Cache of small shadow surfaces.
        text_cache (OrderedDict): LRU cache of rendered text surfaces.
        max_text_cache_size (int): Max size of the text cache.
    """

    def __init__(self, screen: pygame.Surface) -> None:
        """
        Initializes the PygameBackend.

        Args:
            screen (pygame.Surface): The main display surface.
        """
        self.screen = screen

        # State
        self.ambient_color = (20, 20, 20, 255)

        # New Lighting Engine
        w, h = screen.get_size()
        self.lighting_engine = SoftwareLightingEngine((w, h))

        # Caches
        self.font_cache: dict[tuple[int, str | None], pygame.font.Font] = {}
        self.shadow_surface_cache: dict[
            tuple[int, int, tuple[int, int, int, int]], pygame.Surface
        ] = {}  # (rx, ry, color) -> Surface
        self.MAX_SHADOW_CACHE_SIZE = 1000

        # Text Cache (LRU)
        # Key: (text, size, color, font_name)
        self.text_cache: OrderedDict[
            tuple[str, int, tuple[int, int, int], str | None], pygame.Surface
        ] = OrderedDict()
        self.max_text_cache_size = 500

    def clear(self, color: tuple[int, int, int]) -> None:
        """
        Clears the screen with the specified color.

        Args:
            color (tuple[int, int, int]): The RGB color.
        """
        self.screen.fill(color)

    def begin_frame(self) -> None:
        """
        Prepares for a new frame.

        Resizes the lighting engine if necessary and clears it.
        """
        # Sync size if changed
        w, h = self.screen.get_size()
        if self.lighting_engine.native_size != (w, h):
            self.lighting_engine.resize(w, h)

        c = self.ambient_color
        self.lighting_engine.clear((c[0], c[1], c[2]))

    def end_frame(self) -> None:
        """
        Finalizes the frame.

        Composites the lighting overlay onto the screen.
        """
        # Render Lighting Overlay
        # (Lights have already been processed into the engine via draw_light)
        # We just get the final surface and blit it.
        lightmap = self.lighting_engine.get_surface()
        self.screen.blit(lightmap, (0, 0), special_flags=pygame.BLEND_MULT)

    def draw_sprite(self, cmd: SpriteCommand) -> None:
        """
        Draws a sprite.

        Args:
            cmd (SpriteCommand): The sprite command.
        """
        self._render_sprite(cmd)

    def draw_text(self, cmd: TextCommand) -> None:
        """
        Draws text.

        Args:
            cmd (TextCommand): The text command.
        """
        self._render_text(cmd)

    def draw_shadow(self, cmd: ShadowCommand) -> None:
        """
        Draws a blob shadow.

        Args:
            cmd (ShadowCommand): The shadow command.
        """
        self._render_shadow(cmd)

    def draw_light(self, cmd: LightCommand) -> None:
        """
        Process a light source.

        Args:
            cmd (LightCommand): The light command.
        """
        # Submit directly to engine
        self.lighting_engine.render_light(
            cmd.position,
            cmd.radius,
            cmd.color[:3],  # Ensure 3-tuple
            cmd.intensity,
            soft_shadows=cmd.soft_shadows,
            static=cmd.static,
            entity_id=cmd.entity_id,
        )

    def draw_occluder(self, cmd: OccluderCommand) -> None:
        """
        Process an occluder.

        Args:
            cmd (OccluderCommand): The occluder command.
        """
        # Submit directly to engine
        # Calculate AABB immediately if not present
        if not cmd.vertices:
            return

        # Snap vertices to integers to match Sprite rendering precision.
        # Sprites are drawn at int(x), int(y).
        # Shadows must originate from the same pixel boundaries to avoid relative jitter during zoom.
        snapped_vertices = [(int(v[0]), int(v[1])) for v in cmd.vertices]

        xs = [v[0] for v in snapped_vertices]
        ys = [v[1] for v in snapped_vertices]
        aabb = (min(xs), max(xs), min(ys), max(ys))

        self.lighting_engine.add_occluder(
            aabb, [(float(v[0]), float(v[1])) for v in snapped_vertices]
        )

    def set_ambient_light(self, color: tuple[int, int, int, int]) -> None:
        """
        Sets the ambient light color.

        Args:
            color (tuple[int, int, int, int]): RGBA color.
        """
        self.ambient_color = color

    def draw_line(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        color: tuple[int, int, int],
        width: int = 1,
    ) -> None:
        """
        Draws a line.

        Args:
            start (tuple[float, float]): Start point.
            end (tuple[float, float]): End point.
            color (tuple[int, int, int]): RGB color.
            width (int): Line width. Defaults to 1.
        """
        pygame.draw.line(self.screen, color, start, end, width)

    def toggle_lighting_debug(self, enabled: bool) -> None:
        """
        Toggles lighting debug mode.

        Args:
            enabled (bool): Enable/Disable flag.
        """
        self.lighting_engine.toggle_debug(enabled)

    # Internal Rendering Methods

    def _render_sprite(self, cmd: SpriteCommand) -> None:
        dest_rect = cmd.image.get_rect()
        dest_rect.center = (int(cmd.position[0]), int(cmd.position[1]))

        image_to_blit = cmd.image
        if cmd.alpha < 255:
            # Optimization: Toggle alpha instead of copy.
            # This avoids expensive surface copying every frame.
            # We must restore the original alpha afterwards because the surface might be shared/cached.
            original_alpha = image_to_blit.get_alpha()
            image_to_blit.set_alpha(cmd.alpha)
            self.screen.blit(image_to_blit, dest_rect)
            image_to_blit.set_alpha(
                original_alpha if original_alpha is not None else 255
            )
        else:
            self.screen.blit(image_to_blit, dest_rect)

        if cmd.selected:
            pygame.draw.rect(self.screen, (255, 255, 0), dest_rect.inflate(4, 4), 2)

    def _render_text(self, cmd: TextCommand) -> None:
        # Check cache
        key = (cmd.text, cmd.size, cmd.color, cmd.font_name)
        if key in self.text_cache:
            self.text_cache.move_to_end(key)
            surf = self.text_cache[key]
        else:
            font = self._get_font(cmd.size, cmd.font_name)
            surf = font.render(cmd.text, True, cmd.color)
            self.text_cache[key] = surf
            if len(self.text_cache) > self.max_text_cache_size:
                self.text_cache.popitem(last=False)

        dest_rect = surf.get_rect(center=(int(cmd.position[0]), int(cmd.position[1])))

        if cmd.alpha < 255:
            # Optimization: Toggle alpha instead of copy/creating new surface.
            original_alpha = surf.get_alpha()
            surf.set_alpha(cmd.alpha)
            self.screen.blit(surf, dest_rect)
            surf.set_alpha(original_alpha if original_alpha is not None else 255)
        else:
            self.screen.blit(surf, dest_rect)

    def _render_shadow(self, cmd: ShadowCommand) -> None:
        rx, ry = int(cmd.radius[0]), int(cmd.radius[1])
        if rx <= 0 or ry <= 0:
            return

        # Optimization: Don't cache large shadows (e.g. valid during zoom)
        # Use surface pool instead to prevent cache thrashing/bloat.
        is_large = rx > 50

        if is_large:
            # Use Pool
            w, h = rx * 2, ry * 2
            s = self.lighting_engine.surface_pool.acquire(w, h)
            # Ensure clean surface (acquire cleans it?)
            # surface_pool.acquire() clears it with (0,0,0,0)

            pygame.draw.ellipse(s, cmd.color, pygame.Rect(0, 0, w, h))

            dest_rect = s.get_rect(center=(int(cmd.position[0]), int(cmd.position[1])))
            self.screen.blit(s, dest_rect)

            # Release immediately
            self.lighting_engine.surface_pool.release(s)

        else:
            # Small shadows: Cache them (Clear-on-full)
            key = (rx, ry, cmd.color)
            if key not in self.shadow_surface_cache:
                if len(self.shadow_surface_cache) >= self.MAX_SHADOW_CACHE_SIZE:
                    self.shadow_surface_cache.clear()

                s = pygame.Surface((rx * 2, ry * 2), pygame.SRCALPHA)
                pygame.draw.ellipse(s, cmd.color, s.get_rect())
                self.shadow_surface_cache[key] = s

            s = self.shadow_surface_cache[key]
            dest_rect = s.get_rect(center=(int(cmd.position[0]), int(cmd.position[1])))
            self.screen.blit(s, dest_rect)

    def _get_font(self, size: int, name: str | None = None) -> pygame.font.Font:
        key = (size, name)
        if key not in self.font_cache:
            self.font_cache[key] = pygame.font.SysFont(name, size)
        return self.font_cache[key]
