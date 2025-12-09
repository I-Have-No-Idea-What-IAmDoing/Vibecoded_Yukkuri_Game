"""
Module handling the game world rendering logic.
"""

import pygame
import pygame_light2d as pl2d
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
    ):
        """
        Initializes the WorldRenderer.

        Args:
            screen (pygame.Surface): The target Pygame surface.
            camera (Camera): The world view manager.
            resource_manager (ResourceManager): The resource manager.
            lights_engine (LightingEngine): The lighting engine instance.
        """
        self.screen = screen
        self.camera = camera
        self.rm = resource_manager
        self.font_cache: dict[int, pygame.font.Font] = {}
        self.lights_engine = lights_engine

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
        # Linear interpolate between previous and current position
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
        shadow_radius_x = int(sprite.width * transform.scale * self.camera.zoom * 0.4)
        shadow_radius_y = int(shadow_radius_x * 0.5)

        # --- Draw Sprite ---

        # Calculate screen position
        base_screen_x, base_screen_y = self.camera.world_to_screen(
            interp_x, interp_y, sw, sh
        )

        # Apply vertical offset for hopping effect, scaled by zoom
        screen_y = base_screen_y - (visual_transform.vertical_offset * self.camera.zoom)

        # Scale
        scale = transform.scale * self.camera.zoom

        # If we have a lighting engine, use it
        if self.lights_engine:
            # We use surface_to_texture with the rotated surface to guarantee correctness
            # of transformations (scale, flip, rotation) matching the original renderer exactly.

            img = self.rm.load_image(sprite.image_name)

            # Handle animation
            if sprite.frame_count > 1:
                source_rect = pygame.Rect(0, 0, sprite.width, sprite.height)
                sx = sprite.current_frame * sprite.width
                if sx + sprite.width <= img.get_width():
                    source_rect.x = sx
                if source_rect.right > img.get_width() or source_rect.bottom > img.get_height():
                     if img.get_width() < sprite.width or img.get_height() < sprite.height:
                         frame_img = pygame.transform.scale(img, (sprite.width, sprite.height))
                     else:
                         frame_img = img.subsurface(source_rect.clip(img.get_rect()))
                else:
                    frame_img = img.subsurface(source_rect)
            else:
                if img.get_width() != sprite.width or img.get_height() != sprite.height:
                    frame_img = pygame.transform.scale(img, (sprite.width, sprite.height))
                else:
                    frame_img = img

            if sprite.flip_x or sprite.flip_y:
                frame_img = pygame.transform.flip(frame_img, sprite.flip_x, sprite.flip_y)

            if scale != 1.0:
                w = int(sprite.width * scale)
                h = int(sprite.height * scale)
                if w > 0 and h > 0:
                    scaled_img = pygame.transform.scale(frame_img, (w, h))
                else:
                    return
            else:
                scaled_img = frame_img

            if transform.rotation != 0.0:
                scaled_img = pygame.transform.rotate(scaled_img, transform.rotation)

            # Center the sprite
            rect = scaled_img.get_rect(center=(int(base_screen_x), int(screen_y)))

            # Culling
            if rect.colliderect(self.screen.get_rect()):
                # Shadow
                if shadow_radius_x > 0 and shadow_radius_y > 0:
                    shadow_surface = pygame.Surface(
                        (shadow_radius_x * 2, shadow_radius_y * 2), pygame.SRCALPHA
                    )
                    shadow_color = (0, 0, 0, 100)
                    pygame.draw.ellipse(
                        shadow_surface, shadow_color, shadow_surface.get_rect()
                    )
                    shadow_tex = self.lights_engine.surface_to_texture(shadow_surface)
                    self.lights_engine.render_texture(
                        shadow_tex,
                        pl2d.BACKGROUND,
                        pygame.Rect(shadow_x - shadow_radius_x, shadow_y - shadow_radius_y, shadow_radius_x * 2, shadow_radius_y * 2),
                        pygame.Rect(0, 0, shadow_radius_x * 2, shadow_radius_y * 2)
                    )
                    shadow_tex.release()

                # Main Sprite
                tex = self.lights_engine.surface_to_texture(scaled_img)
                self.lights_engine.render_texture(
                    tex,
                    pl2d.BACKGROUND,
                    rect,
                    pygame.Rect(0, 0, tex.width, tex.height)
                )
                tex.release()

                # Selection highlight
                selectable = world.get_component(ent, Selectable)
                if selectable and selectable.selected:
                    # Draw selection rect to a surface and render
                    sel_surf = pygame.Surface(rect.size, pygame.SRCALPHA)
                    pygame.draw.rect(sel_surf, (255, 255, 0), sel_surf.get_rect(), 2)
                    sel_tex = self.lights_engine.surface_to_texture(sel_surf)
                    self.lights_engine.render_texture(
                        sel_tex,
                        pl2d.BACKGROUND,
                        rect,
                        pygame.Rect(0, 0, sel_tex.width, sel_tex.height)
                    )
                    sel_tex.release()
            return

        # Fallback to original render if no lights_engine (e.g. headless or failed init)
        # --- Draw Sprite ---
        img = self.rm.load_image(sprite.image_name)

        # Calculate screen position
        base_screen_x, base_screen_y = self.camera.world_to_screen(
            interp_x, interp_y, sw, sh
        )

        # Apply vertical offset for hopping effect, scaled by zoom
        screen_y = base_screen_y - (visual_transform.vertical_offset * self.camera.zoom)

        # Scale
        scale = transform.scale * self.camera.zoom

        # Handle animation
        img_width, img_height = img.get_size()

        if sprite.frame_count > 1:
            source_rect = pygame.Rect(0, 0, sprite.width, sprite.height)
            sx = sprite.current_frame * sprite.width
            if sx + sprite.width <= img_width:
                source_rect.x = sx

            # Ensure source_rect is within image bounds
            if source_rect.right > img_width or source_rect.bottom > img_height:
                if img_width < sprite.width or img_height < sprite.height:
                    frame_img = pygame.transform.scale(
                        img, (sprite.width, sprite.height)
                    )
                else:
                    frame_img = img.subsurface(source_rect.clip(img.get_rect()))
            else:
                frame_img = img.subsurface(source_rect)
        else:
            if img_width != sprite.width or img_height != sprite.height:
                frame_img = pygame.transform.scale(img, (sprite.width, sprite.height))
            else:
                frame_img = img

        # Apply flips
        if sprite.flip_x or sprite.flip_y:
            frame_img = pygame.transform.flip(frame_img, sprite.flip_x, sprite.flip_y)

        if scale != 1.0:
            w = int(sprite.width * scale)
            h = int(sprite.height * scale)
            if w <= 0 or h <= 0:
                return
            scaled_img = pygame.transform.scale(frame_img, (w, h))
        else:
            scaled_img = frame_img

        # Apply Rotation
        # We rotate after scaling to ensure best quality (though rotating first might be better for pixel art?)
        # For smooth rotation, we should rotate the original image, but we need scaling too.
        # pygame.transform.rotozoom could be used for combined scale/rotation with filtering.
        # Here we just rotate the scaled image.
        if transform.rotation != 0.0:
            # Note: Pygame rotates counter-clockwise for positive degrees
            scaled_img = pygame.transform.rotate(scaled_img, transform.rotation)

        # Center the sprite
        rect = scaled_img.get_rect(center=(int(base_screen_x), int(screen_y)))

        # Culling
        if rect.colliderect(self.screen.get_rect()):
            if shadow_radius_x > 0 and shadow_radius_y > 0:
                shadow_color = (0, 0, 0, 100)  # RGBA with transparency
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
            # We can draw lines to a surface and render that surface.
            # Or use primitives if we had access.
            # Using surface for simplicity and robustness.
            grid_surf = pygame.Surface((sw, sh), pygame.SRCALPHA)

            for col in range(start_col, end_col):
                x = col * grid_size
                sx, _ = self.camera.world_to_screen(x, 0, sw, sh)
                pygame.draw.line(grid_surf, (50, 50, 50), (int(sx), 0), (int(sx), sh))

            for row in range(start_row, end_row):
                y = row * grid_size
                _, sy = self.camera.world_to_screen(0, y, sw, sh)
                pygame.draw.line(grid_surf, (50, 50, 50), (0, int(sy)), (sw, int(sy)))

            tex = self.lights_engine.surface_to_texture(grid_surf)
            self.lights_engine.render_texture(
                tex,
                pl2d.BACKGROUND,
                pygame.Rect(0, 0, sw, sh),
                pygame.Rect(0, 0, sw, sh)
            )
            tex.release()
        else:
            for col in range(start_col, end_col):
                x = col * grid_size
                sx, _ = self.camera.world_to_screen(x, 0, sw, sh)
                pygame.draw.line(self.screen, (50, 50, 50), (int(sx), 0), (int(sx), sh))

            for row in range(start_row, end_row):
                y = row * grid_size
                _, sy = self.camera.world_to_screen(0, y, sw, sh)
                pygame.draw.line(self.screen, (50, 50, 50), (0, int(sy)), (sw, int(sy)))
