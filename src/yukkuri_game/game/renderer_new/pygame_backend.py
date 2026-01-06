from typing import Tuple
import pygame
from .backend import RenderBackend
from .commands import (
    SpriteCommand,
    TextCommand,
    LightCommand,
    ShadowCommand,
    OccluderCommand,
)


class PygameBackend(RenderBackend):
    """Standard Pygame backend (no dynamic lighting)."""

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.font_cache = {}
        self.shadow_surface_cache = {}

    def clear(self, color: Tuple[int, int, int]) -> None:
        self.screen.fill(color)

    def begin_frame(self) -> None:
        pass

    def end_frame(self) -> None:
        pass

    def draw_sprite(self, cmd: SpriteCommand) -> None:
        # Assuming cmd.image is already scaled/rotated by the system or pre-cached?
        # Actually, in the command I put 'image' as pygame.Surface.
        # The system usually handles caching.
        # But if the command has rotation/scale parameters, the backend should handle transformation?
        # Typically rendering massive amounts of transformed sprites is expensive if done every frame.
        # But for simplicity, let's assume the passed 'image' is the base image, and we transform it here OR it is already transformed.
        # Looking at previous implementation, SurfaceCache handled transformation.
        # Let's assume the System uses SurfaceCache to get the transformed image, OR we do it here.
        # If I pass the base image and params, I can cache it here.
        # But `SpriteCommand` has `image` which implies the source.

        # NOTE: For now, I will assume `cmd.image` IS the final surface to blit, or I will apply simple transformations.
        # However, `RenderCommand` has `rotation`, `scale`, etc.
        # If the caller provides a pre-transformed image, those should be default.

        # Let's trust the Caller to provide the correct image if they use a cache,
        # OR we use the params to transform (slow without cache).
        # Given the `SurfaceCache` in the old code, the System likely resolves the specific surface.
        # So `cmd.image` is likely the *result* of the cache lookup.

        dest_rect = cmd.image.get_rect(
            center=(int(cmd.position[0]), int(cmd.position[1]))
        )

        if cmd.alpha < 255:
            cmd.image.set_alpha(cmd.alpha)

        self.screen.blit(cmd.image, dest_rect)

        if cmd.selected:
            pygame.draw.rect(self.screen, (255, 255, 0), dest_rect, 2)

    def draw_text(self, cmd: TextCommand) -> None:
        font = self._get_font(cmd.size, cmd.font_name)
        surf = font.render(cmd.text, True, cmd.color)
        if cmd.alpha < 255:
            surf.set_alpha(cmd.alpha)
        dest_rect = surf.get_rect(center=(int(cmd.position[0]), int(cmd.position[1])))
        self.screen.blit(surf, dest_rect)

    def draw_shadow(self, cmd: ShadowCommand) -> None:
        # Simple ellipse shadow
        rx, ry = int(cmd.radius[0]), int(cmd.radius[1])
        if rx <= 0 or ry <= 0:
            return

        key = (rx, ry, cmd.color)
        if key not in self.shadow_surface_cache:
            s = pygame.Surface((rx * 2, ry * 2), pygame.SRCALPHA)
            pygame.draw.ellipse(s, cmd.color, s.get_rect())
            self.shadow_surface_cache[key] = s

        surf = self.shadow_surface_cache[key]
        dest_rect = surf.get_rect(center=(int(cmd.position[0]), int(cmd.position[1])))
        self.screen.blit(surf, dest_rect)

    def draw_light(self, cmd: LightCommand) -> None:
        # No-op for standard pygame backend
        pass

    def draw_occluder(self, cmd: OccluderCommand) -> None:
        # No-op
        pass

    def set_ambient_light(self, color: Tuple[int, int, int, int]) -> None:
        # No-op, or maybe overlay a dark rect if we wanted fake darkness
        pass

    def draw_line(
        self,
        start: Tuple[float, float],
        end: Tuple[float, float],
        color: Tuple[int, int, int],
        width: int = 1,
    ) -> None:
        pygame.draw.line(self.screen, color, start, end, width)

    def _get_font(self, size: int, name: str = None) -> pygame.font.Font:
        key = (size, name)
        if key not in self.font_cache:
            self.font_cache[key] = pygame.font.SysFont(name, size)
        return self.font_cache[key]
