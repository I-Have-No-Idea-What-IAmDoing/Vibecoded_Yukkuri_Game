"""
Module handling the game world rendering logic.
"""

import pygame
import pygame_light2d as pl2d
from collections import OrderedDict
from pygame_light2d import LightingEngine
from ..engine.ecs import World
from ..engine.resource_manager import ResourceManager
from .components import (
    Transform,
    Sprite,
    Selectable,
    FloatingText,
    PhysicsBody,
    VisualTransform,
)
from .camera import Camera
from .surface_cache import SurfaceCache


class WorldRenderer:
    """
    Handles the pure drawing logic for the game world.

    Attributes:
        screen (pygame.Surface): The surface to render to.
        camera (Camera): The world view manager.
        rm (ResourceManager): The resource manager for fetching assets.
        font_cache (dict): Cache of pygame fonts.
        lights_engine (LightingEngine): The lighting engine to use for rendering.
    """

    def __init__(
        self,
        screen: pygame.Surface,
        camera: Camera,
        resource_manager: ResourceManager,
        lights_engine: LightingEngine = None,
        texture_cache_max_size: int = 500
    ):
        """
        Initializes the WorldRenderer.

        Args:
            screen (pygame.Surface): The target Pygame surface.
            camera (Camera): The world view manager.
            resource_manager (ResourceManager): The resource manager.
            lights_engine (LightingEngine): The lighting engine instance.
            texture_cache_max_size (int): The maximum number of textures to keep in memory. Defaults to 500.
        """
        self.screen = screen
        self.camera = camera
        self.rm = resource_manager
        self.font_cache: dict[int, pygame.font.Font] = {}
        self.lights_engine = lights_engine
        # Key: (image_name, frame, round(scale, 3), round(rotation, 1), flip_x, flip_y)
        # Or specialized keys for shadows/selection
        self.texture_cache: OrderedDict[tuple, "pl2d.Texture"] = OrderedDict()
        self.texture_cache_max_size = texture_cache_max_size

        # Initialize Surface Cache
        self.surface_cache = SurfaceCache(self.rm)

    def _get_font(self, size: int) -> pygame.font.Font:
        """
        Retrieves a font of the specified size from the cache, or creates it.

        Args:
            size (int): The font size.

        Returns:
            pygame.font.Font: The requested font.
        """
        if size not in self.font_cache:
            # SysFont returns a Font object, but if not found or None, it returns a default font.
            self.font_cache[size] = pygame.font.SysFont(None, size)
        return self.font_cache[size]

    def render(self, world: World, alpha: float = 1.0) -> None:
        """
        Renders the world grid and all visible entities.

        Args:
            world (World): The ECS World.
            alpha (float): Interpolation factor (0.0 to 1.0).

        Returns:
            None
        """
        # Render background grid
        self.draw_grid()

        # Render entities
        entities = world.get_entities_with(
            Transform, Sprite, PhysicsBody, VisualTransform
        )
        # Sort by Y for depth (ground position)
        entities.sort(key=lambda e: getattr(world.get_component(e, Transform), "y", 0))

        sw, sh = self.screen.get_size()

        for ent in entities:
            self._render_entity(world, ent, sw, sh, alpha)

        # Render Floating Text
        self.render_floating_text(world, sw, sh)

    def _get_cached_texture(
        self, key: tuple, surface_generator
    ) -> "pl2d.Texture":
        """
        Retrieves a texture from cache or generates it using the provided generator function.

        Args:
            key (tuple): The unique cache key.
            surface_generator (callable): Function that returns a pygame.Surface.

        Returns:
            pl2d.Texture: The cached or newly created texture.
        """
        if key in self.texture_cache:
            self.texture_cache.move_to_end(key)
            return self.texture_cache[key]

        surface = surface_generator()
        tex = self.lights_engine.surface_to_texture(surface)
        self.texture_cache[key] = tex

        # LRU Eviction for textures
        if len(self.texture_cache) > self.texture_cache_max_size:
            _, old_tex = self.texture_cache.popitem(last=False)
            old_tex.release()

        return tex

    def _render_entity(
        self, world: World, ent: int, sw: int, sh: int, alpha: float
    ) -> None:
        """
        Renders a single entity.
        """
        transform = world.get_component(ent, Transform)
        sprite = world.get_component(ent, Sprite)
        phys_body = world.get_component(ent, PhysicsBody)
        visual_transform = world.get_component(ent, VisualTransform)

        if (
            transform is None
            or sprite is None
            or phys_body is None
            or visual_transform is None
        ):
            return

        # --- Interpolation ---
        curr_x = transform.x
        curr_y = transform.y
        prev_x = getattr(transform, "prev_x", curr_x)
        prev_y = getattr(transform, "prev_y", curr_y)

        interp_x = prev_x + (curr_x - prev_x) * alpha
        interp_y = prev_y + (curr_y - prev_y) * alpha

        shadow_x, shadow_y = self.camera.world_to_screen(
            visual_transform.shadow_position.x,
            visual_transform.shadow_position.y,
            sw,
            sh,
        )

        scale = transform.scale * self.camera.zoom

        # Key: (image_name, frame, scale, rotation, flip_x, flip_y)
        # We need width and height to calculate key for SurfaceCache
        # but SurfaceCache expects them as arguments to get_surface
        # For texture_cache key, we use what we have.

        sprite_key = (
            sprite.image_name,
            sprite.current_frame,
            round(scale, 3),
            round(transform.rotation, 1),
            sprite.flip_x,
            sprite.flip_y
        )

        tex = None
        scaled_img = None

        # Function to generate the surface using SurfaceCache
        def sprite_gen():
            return self.surface_cache.get_surface(
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

        if self.lights_engine:
             if sprite_key in self.texture_cache:
                 tex = self.texture_cache[sprite_key]
                 self.texture_cache.move_to_end(sprite_key)
                 tex_w, tex_h = tex.width, tex.height
             else:
                 # Not in texture cache, get it via generator which uses surface cache
                 # We need to know the size first?
                 # No, we can get texture from cache if present.
                 # If not, we generate it.
                 # But we need dimensions to calculate RECT before rendering/checking visibility?
                 # Yes, usually. But here we can lazily get it if we assume we might render it.
                 # Optimization: Calculate approx size for culling without generating surface.

                 # Approximate dimensions for culling
                 # Note: rotation changes bounding box.
                 # If we want exact, we need surface or math.
                 # Let's trust that getting surface from SurfaceCache is fast enough (it's cached)
                 scaled_img = sprite_gen()
                 if scaled_img is None:
                     return
                 tex_w, tex_h = scaled_img.get_size()
        else:
            # Fallback always needs surface
            scaled_img = sprite_gen()
            if scaled_img is None:
                return
            tex_w, tex_h = scaled_img.get_size()

        shadow_radius_x = int(sprite.width * scale * 0.4)
        shadow_radius_y = int(shadow_radius_x * 0.5)

        # Calculate screen position
        base_screen_x, base_screen_y = self.camera.world_to_screen(
            interp_x, interp_y, sw, sh
        )

        screen_y = base_screen_y - (visual_transform.vertical_offset * self.camera.zoom)

        # Center the sprite (using tex dimensions or surface dimensions)
        rect = pygame.Rect(0, 0, tex_w, tex_h)
        rect.center = (int(base_screen_x), int(screen_y))

        # Culling
        if rect.colliderect(self.screen.get_rect()):
            if self.lights_engine:
                # Shadow
                if shadow_radius_x > 0 and shadow_radius_y > 0:
                    shadow_key = ("shadow", shadow_radius_x, shadow_radius_y)

                    def shadow_gen():
                        surf = pygame.Surface(
                            (shadow_radius_x * 2, shadow_radius_y * 2), pygame.SRCALPHA
                        )
                        shadow_color = (0, 0, 0, 100)
                        pygame.draw.ellipse(
                            surf, shadow_color, surf.get_rect()
                        )
                        return surf

                    shadow_tex = self._get_cached_texture(shadow_key, shadow_gen)
                    self.lights_engine.render_texture(
                        shadow_tex,
                        pl2d.BACKGROUND,
                        pygame.Rect(shadow_x - shadow_radius_x, shadow_y - shadow_radius_y, shadow_radius_x * 2, shadow_radius_y * 2),
                        pygame.Rect(0, 0, shadow_radius_x * 2, shadow_radius_y * 2)
                    )

                # Main Sprite
                if tex is None:
                    # We have scaled_img and generator
                    # But _get_cached_texture takes a generator.
                    # We can pass sprite_gen.
                    tex = self._get_cached_texture(sprite_key, sprite_gen)

                self.lights_engine.render_texture(
                    tex,
                    pl2d.BACKGROUND,
                    rect,
                    pygame.Rect(0, 0, tex.width, tex.height)
                )

                # Selection highlight
                selectable = world.get_component(ent, Selectable)
                if selectable and selectable.selected:
                    bg_layer = self.lights_engine._get_layer(pl2d.BACKGROUND)
                    # Yellow color (255, 255, 0) -> (1.0, 1.0, 0.0)
                    color = (1.0, 1.0, 0.0, 1.0)
                    self.lights_engine.graphics.render_rectangle(
                        bg_layer,
                        color,
                        rect.center,
                        rect.width,
                        rect.height,
                        angle=0, # Rotation already applied to texture/rect dimensions usually, but rect is axis aligned here
                        antialias=False
                    )
            else:
                # Fallback rendering
                if shadow_radius_x > 0 and shadow_radius_y > 0:
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

                # Selection highlight
                selectable = world.get_component(ent, Selectable)
                if selectable and selectable.selected:
                    pygame.draw.rect(self.screen, (255, 255, 0), rect, 2)

    def render_floating_text(self, world: World, screen_w: int, screen_h: int) -> None:
        """
        Renders floating text entities.

        Args:
            world (World): The ECS World.
            screen_w (int): Screen width.
            screen_h (int): Screen height.

        Returns:
            None
        """
        for entity, (transform, text_comp) in world.get_components_tuple(
            Transform, FloatingText
        ):
            font = self._get_font(text_comp.size)

            # Render text surface
            text_surface = font.render(text_comp.text, True, text_comp.color)

            # Fade out based on lifetime
            if text_comp.max_lifetime > 0:
                alpha = int(255 * (text_comp.lifetime / text_comp.max_lifetime))
                alpha = max(0, min(255, alpha))
                text_surface.set_alpha(alpha)

            # Calculate screen position
            screen_x, screen_y = self.camera.world_to_screen(
                transform.x, transform.y, screen_w, screen_h
            )

            # Center text
            rect = text_surface.get_rect(center=(int(screen_x), int(screen_y)))

            if self.lights_engine:
                tex = self.lights_engine.surface_to_texture(text_surface)
                self.lights_engine.render_texture(
                    tex,
                    pl2d.FOREGROUND,
                    rect,
                    pygame.Rect(0, 0, tex.width, tex.height)
                )
                tex.release()
            else:
                self.screen.blit(text_surface, rect)

    def draw_grid(self) -> None:
        """
        Draws a grid on the screen to visualize the world space.

        Returns:
            None
        """
        # Draw a grid to show movement
        grid_size = 100
        sw, sh = self.screen.get_size()

        start_x, start_y = self.camera.screen_to_world(0, 0, sw, sh)
        end_x, end_y = self.camera.screen_to_world(sw, sh, sw, sh)

        start_col = int(start_x // grid_size)
        end_col = int(end_x // grid_size) + 1
        start_row = int(start_y // grid_size)
        end_row = int(end_y // grid_size) + 1

        if self.lights_engine:
            # Use primitives rendering from pygame-render via lights_engine.graphics
            # We need to access the BACKGROUND layer.
            # Note: pygame-light2d BACKGROUND is an enum, we need the layer object.
            # Accessing private _get_layer for now or assuming we can pass the enum if supported.
            # But render_lines takes a Layer object.
            # Using _get_layer since it returns the layer object for the enum.
            bg_layer = self.lights_engine._get_layer(pl2d.BACKGROUND)

            # Prepare vertices for lines
            vertices = []

            # Vertical lines
            for col in range(start_col, end_col):
                x = col * grid_size
                sx, _ = self.camera.world_to_screen(x, 0, sw, sh)
                # render_lines expects list of tuples
                vertices.extend([(sx, 0), (sx, sh)])

            # Horizontal lines
            for row in range(start_row, end_row):
                y = row * grid_size
                _, sy = self.camera.world_to_screen(0, y, sw, sh)
                vertices.extend([(0, sy), (sw, sy)])

            if vertices:
                # Color (50, 50, 50) normalized to 0-1 range
                color = (50/255, 50/255, 50/255, 1.0)
                # render_lines draws connected lines if strip=False (default is False? No, default strip=False usually means separate lines?
                # Let's check docs again: render_lines(..., strip=False)
                # If strip=False, it draws GL_LINES (pairs of vertices).
                # If strip=True, it draws GL_LINE_STRIP.
                # We have pairs, so strip=False is correct.
                self.lights_engine.graphics.render_lines(
                    bg_layer,
                    color,
                    vertices,
                    antialias=False
                )

        else:
            for col in range(start_col, end_col):
                x = col * grid_size
                sx, _ = self.camera.world_to_screen(x, 0, sw, sh)
                pygame.draw.line(self.screen, (50, 50, 50), (int(sx), 0), (int(sx), sh))

            for row in range(start_row, end_row):
                y = row * grid_size
                _, sy = self.camera.world_to_screen(0, y, sw, sh)
                pygame.draw.line(self.screen, (50, 50, 50), (0, int(sy)), (sw, int(sy)))
