import pygame
import pygame_light2d as pl2d
from typing import Tuple, List, Optional, Callable
from abc import ABC, abstractmethod
from collections import OrderedDict
from .camera import Camera
from .surface_cache import SurfaceCache
from .components import Transform, Sprite, VisualTransform, FloatingText

class RenderBackend(ABC):
    """
    Abstract base class for rendering backends.
    """

    def __init__(self):
        self.font_cache = {}

    def _get_font(self, size: int) -> pygame.font.Font:
        if size not in self.font_cache:
            self.font_cache[size] = pygame.font.SysFont(None, size)
        return self.font_cache[size]

    @abstractmethod
    def clear(self):
        """Clears the screen or prepares for a new frame."""
        pass

    @abstractmethod
    def draw_grid(self, camera: Camera, screen_w: int, screen_h: int):
        """Draws the world grid."""
        pass

    @abstractmethod
    def draw_entity(
        self,
        screen: pygame.Surface,
        camera: Camera,
        surface_cache: SurfaceCache,
        transform: Transform,
        sprite: Sprite,
        visual_transform: VisualTransform,
        is_selected: bool,
        alpha: float
    ):
        """Draws a single entity (shadow + sprite + selection)."""
        pass

    @abstractmethod
    def draw_floating_text(
        self,
        screen: pygame.Surface,
        camera: Camera,
        transform: Transform,
        text_comp: FloatingText,
        screen_w: int,
        screen_h: int
    ):
        """Draws floating text."""
        pass


class PygameRenderBackend(RenderBackend):
    """
    Standard Pygame rendering backend.
    """
    def __init__(self, screen: pygame.Surface):
        super().__init__()
        self.screen = screen

    def clear(self):
        # In standard pygame, we usually fill screen, but WorldRenderer might handle background.
        pass

    def draw_grid(self, camera: Camera, screen_w: int, screen_h: int):
        grid_size = 100
        start_x, start_y = camera.screen_to_world(0, 0, screen_w, screen_h)
        end_x, end_y = camera.screen_to_world(screen_w, screen_h, screen_w, screen_h)

        start_col = int(start_x // grid_size)
        end_col = int(end_x // grid_size) + 1
        start_row = int(start_y // grid_size)
        end_row = int(end_y // grid_size) + 1

        for col in range(start_col, end_col):
            x = col * grid_size
            sx, _ = camera.world_to_screen(x, 0, screen_w, screen_h)
            pygame.draw.line(self.screen, (50, 50, 50), (int(sx), 0), (int(sx), screen_h))

        for row in range(start_row, end_row):
            y = row * grid_size
            _, sy = camera.world_to_screen(0, y, screen_w, screen_h)
            pygame.draw.line(self.screen, (50, 50, 50), (0, int(sy)), (screen_w, int(sy)))

    def draw_entity(
        self,
        screen: pygame.Surface,
        camera: Camera,
        surface_cache: SurfaceCache,
        transform: Transform,
        sprite: Sprite,
        visual_transform: VisualTransform,
        is_selected: bool,
        alpha: float
    ):
        # Interpolation
        curr_x = transform.x
        curr_y = transform.y
        prev_x = getattr(transform, "prev_x", curr_x)
        prev_y = getattr(transform, "prev_y", curr_y)

        interp_x = prev_x + (curr_x - prev_x) * alpha
        interp_y = prev_y + (curr_y - prev_y) * alpha

        sw, sh = screen.get_size()
        scale = transform.scale * camera.zoom

        # Sprite
        scaled_img = surface_cache.get_surface(
            sprite.image_name,
            sprite.current_frame,
            sprite.frame_count,
            sprite.width,
            sprite.height,
            scale,
            transform.rotation,
            sprite.flip_x,
            sprite.flip_y
        )

        if scaled_img:
            base_screen_x, base_screen_y = camera.world_to_screen(
                interp_x, interp_y, sw, sh
            )
            screen_y = base_screen_y - (visual_transform.vertical_offset * camera.zoom)

            rect = scaled_img.get_rect()
            rect.center = (int(base_screen_x), int(screen_y))

            if rect.colliderect(self.screen.get_rect()):
                # Shadow
                shadow_radius_x = int(sprite.width * scale * 0.4)
                shadow_radius_y = int(shadow_radius_x * 0.5)

                if shadow_radius_x > 0 and shadow_radius_y > 0:
                    shadow_x, shadow_y = camera.world_to_screen(
                        visual_transform.shadow_position.x,
                        visual_transform.shadow_position.y,
                        sw,
                        sh,
                    )
                    shadow_color = (0, 0, 0, 100)
                    shadow_surface = pygame.Surface(
                        (shadow_radius_x * 2, shadow_radius_y * 2), pygame.SRCALPHA
                    )
                    pygame.draw.ellipse(
                        shadow_surface, shadow_color, shadow_surface.get_rect()
                    )
                    self.screen.blit(
                        shadow_surface,
                        (shadow_x - shadow_radius_x, shadow_y - shadow_radius_y),
                    )

                self.screen.blit(scaled_img, rect)

                if is_selected:
                    pygame.draw.rect(self.screen, (255, 255, 0), rect, 2)

    def draw_floating_text(
        self,
        screen: pygame.Surface,
        camera: Camera,
        transform: Transform,
        text_comp: FloatingText,
        screen_w: int,
        screen_h: int
    ):
        font = self._get_font(text_comp.size)
        text_surface = font.render(text_comp.text, True, text_comp.color)

        if text_comp.max_lifetime > 0:
            alpha = int(255 * (text_comp.lifetime / text_comp.max_lifetime))
            alpha = max(0, min(255, alpha))
            text_surface.set_alpha(alpha)

        screen_x, screen_y = camera.world_to_screen(
            transform.x, transform.y, screen_w, screen_h
        )
        rect = text_surface.get_rect(center=(int(screen_x), int(screen_y)))
        self.screen.blit(text_surface, rect)


class Light2DRenderBackend(RenderBackend):
    """
    Pygame Light2D rendering backend.
    """
    def __init__(self, lights_engine: pl2d.LightingEngine, texture_cache_max_size: int = 500):
        super().__init__()
        self.lights_engine = lights_engine
        self.texture_cache: OrderedDict[tuple, "pl2d.Texture"] = OrderedDict()
        self.texture_cache_max_size = texture_cache_max_size

    def clear(self):
        pass

    def _get_cached_texture(self, key: tuple, surface_generator: Callable[[], pygame.Surface]) -> "pl2d.Texture":
        if key in self.texture_cache:
            self.texture_cache.move_to_end(key)
            return self.texture_cache[key]

        surface = surface_generator()
        if surface is None:
            return None

        tex = self.lights_engine.surface_to_texture(surface)
        self.texture_cache[key] = tex

        if len(self.texture_cache) > self.texture_cache_max_size:
            _, old_tex = self.texture_cache.popitem(last=False)
            old_tex.release()

        return tex

    def draw_grid(self, camera: Camera, screen_w: int, screen_h: int):
        grid_size = 100
        start_x, start_y = camera.screen_to_world(0, 0, screen_w, screen_h)
        end_x, end_y = camera.screen_to_world(screen_w, screen_h, screen_w, screen_h)

        start_col = int(start_x // grid_size)
        end_col = int(end_x // grid_size) + 1
        start_row = int(start_y // grid_size)
        end_row = int(end_y // grid_size) + 1

        bg_layer = self.lights_engine._get_layer(pl2d.BACKGROUND)
        vertices = []

        for col in range(start_col, end_col):
            x = col * grid_size
            sx, _ = camera.world_to_screen(x, 0, screen_w, screen_h)
            vertices.extend([(sx, 0), (sx, screen_h)])

        for row in range(start_row, end_row):
            y = row * grid_size
            _, sy = camera.world_to_screen(0, y, screen_w, screen_h)
            vertices.extend([(0, sy), (screen_w, sy)])

        if vertices:
            color = (50/255, 50/255, 50/255, 1.0)
            self.lights_engine.graphics.render_lines(
                bg_layer,
                color,
                vertices,
                antialias=False
            )

    def draw_entity(
        self,
        screen: pygame.Surface,
        camera: Camera,
        surface_cache: SurfaceCache,
        transform: Transform,
        sprite: Sprite,
        visual_transform: VisualTransform,
        is_selected: bool,
        alpha: float
    ):
        curr_x = transform.x
        curr_y = transform.y
        prev_x = getattr(transform, "prev_x", curr_x)
        prev_y = getattr(transform, "prev_y", curr_y)

        interp_x = prev_x + (curr_x - prev_x) * alpha
        interp_y = prev_y + (curr_y - prev_y) * alpha

        sw, sh = screen.get_size()
        scale = transform.scale * camera.zoom

        # Texture Key
        sprite_key = (
            sprite.image_name,
            sprite.current_frame,
            round(scale, 3),
            round(transform.rotation, 1),
            sprite.flip_x,
            sprite.flip_y
        )

        def sprite_gen():
            return surface_cache.get_surface(
                sprite.image_name,
                sprite.current_frame,
                sprite.frame_count,
                sprite.width,
                sprite.height,
                scale,
                transform.rotation,
                sprite.flip_x,
                sprite.flip_y
            )

        tex = self._get_cached_texture(sprite_key, sprite_gen)
        if not tex:
            return

        tex_w, tex_h = tex.width, tex.height

        # Calculate Position
        base_screen_x, base_screen_y = camera.world_to_screen(
            interp_x, interp_y, sw, sh
        )
        screen_y = base_screen_y - (visual_transform.vertical_offset * camera.zoom)

        rect = pygame.Rect(0, 0, tex_w, tex_h)
        rect.center = (int(base_screen_x), int(screen_y))

        # Culling
        if rect.colliderect(screen.get_rect()):
            # Shadow
            shadow_radius_x = int(sprite.width * scale * 0.4)
            shadow_radius_y = int(shadow_radius_x * 0.5)

            if shadow_radius_x > 0 and shadow_radius_y > 0:
                shadow_x, shadow_y = camera.world_to_screen(
                    visual_transform.shadow_position.x,
                    visual_transform.shadow_position.y,
                    sw,
                    sh,
                )
                shadow_key = ("shadow", shadow_radius_x, shadow_radius_y)

                def shadow_gen():
                    surf = pygame.Surface(
                        (shadow_radius_x * 2, shadow_radius_y * 2), pygame.SRCALPHA
                    )
                    shadow_color = (0, 0, 0, 100)
                    pygame.draw.ellipse(surf, shadow_color, surf.get_rect())
                    return surf

                shadow_tex = self._get_cached_texture(shadow_key, shadow_gen)
                if shadow_tex:
                    self.lights_engine.render_texture(
                        shadow_tex,
                        pl2d.BACKGROUND,
                        pygame.Rect(shadow_x - shadow_radius_x, shadow_y - shadow_radius_y, shadow_radius_x * 2, shadow_radius_y * 2),
                        pygame.Rect(0, 0, shadow_radius_x * 2, shadow_radius_y * 2)
                    )

            # Draw Sprite
            self.lights_engine.render_texture(
                tex,
                pl2d.BACKGROUND,
                rect,
                pygame.Rect(0, 0, tex.width, tex.height)
            )

            # Selection
            if is_selected:
                bg_layer = self.lights_engine._get_layer(pl2d.BACKGROUND)
                color = (1.0, 1.0, 0.0, 1.0)
                self.lights_engine.graphics.render_rectangle(
                    bg_layer,
                    color,
                    rect.center,
                    rect.width,
                    rect.height,
                    angle=0,
                    antialias=False
                )

    def draw_floating_text(
        self,
        screen: pygame.Surface,
        camera: Camera,
        transform: Transform,
        text_comp: FloatingText,
        screen_w: int,
        screen_h: int
    ):
        font = self._get_font(text_comp.size)
        text_surface = font.render(text_comp.text, True, text_comp.color)

        if text_comp.max_lifetime > 0:
            alpha = int(255 * (text_comp.lifetime / text_comp.max_lifetime))
            alpha = max(0, min(255, alpha))
            text_surface.set_alpha(alpha)

        tex = self.lights_engine.surface_to_texture(text_surface)

        screen_x, screen_y = camera.world_to_screen(
            transform.x, transform.y, screen_w, screen_h
        )
        rect = text_surface.get_rect(center=(int(screen_x), int(screen_y)))

        self.lights_engine.render_texture(
            tex,
            pl2d.FOREGROUND,
            rect,
            pygame.Rect(0, 0, tex.width, tex.height)
        )
        tex.release()
