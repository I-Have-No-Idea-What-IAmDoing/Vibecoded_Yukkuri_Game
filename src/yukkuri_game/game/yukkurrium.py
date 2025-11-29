"""
Module handling the game world view and rendering.
"""
import pygame
from loguru import logger
from ..engine.ecs import System, World
from .components import Transform, Sprite, Selectable, FloatingText, PhysicsBody, VisualTransform
from ..engine.resource_manager import ResourceManager
from ..config import WorldSettings
from .services import InputService
from typing import Tuple

class Yukkurrium:
    """
    Manages the game world view, including coordinate conversion and camera control.

    Attributes:
        width (int): The total width of the game world.
        height (int): The total height of the game world.
        camera_x (float): The x-coordinate of the camera focus point.
        camera_y (float): The y-coordinate of the camera focus point.
        zoom (float): The current zoom level.
        target_zoom (float): The target zoom level for smooth transitions.
        min_zoom (float): Minimum allowed zoom level.
        max_zoom (float): Maximum allowed zoom level.
    """

    def __init__(self, settings: WorldSettings | None = None):
        """
        Initializes the Yukkurrium.

        Args:
            settings (WorldSettings | None): World settings configuration.
        """
        _settings = settings if settings is not None else WorldSettings()
        self.width = _settings.width
        self.height = _settings.height
        # Camera properties
        self.camera_x = 0.0
        self.camera_y = 0.0
        self.zoom = 1.0
        self.target_zoom = 1.0

        # Bounds
        self.min_zoom = 0.5
        self.max_zoom = 2.0

    def world_to_screen(self, wx: float, wy: float, screen_w: int, screen_h: int) -> tuple[float, float]:
        """
        Converts world coordinates to screen coordinates.

        Formula: screen = (world - camera) * zoom + screen_center

        Args:
            wx (float): World x-coordinate.
            wy (float): World y-coordinate.
            screen_w (int): Screen width.
            screen_h (int): Screen height.

        Returns:
            tuple[float, float]: (screen_x, screen_y)
        """
        sx = (wx - self.camera_x) * self.zoom + screen_w / 2
        sy = (wy - self.camera_y) * self.zoom + screen_h / 2
        return sx, sy

    def screen_to_world(self, sx: float, sy: float, screen_w: int, screen_h: int) -> tuple[float, float]:
        """
        Converts screen coordinates to world coordinates.
        Inverse of world_to_screen.

        Formula: world = (screen - screen_center) / zoom + camera

        Args:
            sx (float): Screen x-coordinate.
            sy (float): Screen y-coordinate.
            screen_w (int): Screen width.
            screen_h (int): Screen height.

        Returns:
            tuple[float, float]: (world_x, world_y)
        """
        wx = (sx - screen_w / 2) / self.zoom + self.camera_x
        wy = (sy - screen_h / 2) / self.zoom + self.camera_y
        return wx, wy

    def handle_input(self, event: pygame.event.Event, screen_w: int, screen_h: int) -> None:
        """
        Handles input for camera control (zoom and pan).

        Args:
            event (pygame.event.Event): The Pygame event.
            screen_w (int): Screen width.
            screen_h (int): Screen height.

        Returns:
            None
        """
        if event.type == pygame.MOUSEWHEEL:
            # Zoom in/out based on wheel movement
            self.target_zoom += event.y * 0.1
            self.target_zoom = max(self.min_zoom, min(self.max_zoom, self.target_zoom))
        elif event.type == pygame.MOUSEMOTION:
            if pygame.mouse.get_pressed()[1]: # Middle mouse button
                # Pan the camera
                dx, dy = event.rel
                # Adjust panning speed by zoom so it feels natural at all levels
                self.camera_x -= dx / self.zoom
                self.camera_y -= dy / self.zoom
        elif event.type == pygame.KEYDOWN:
            mods = pygame.key.get_mods()
            if mods & pygame.KMOD_CTRL:
                if event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS:
                    # Zoom In with Keyboard
                    self.target_zoom += 0.1
                    self.target_zoom = max(self.min_zoom, min(self.max_zoom, self.target_zoom))
                elif event.key == pygame.K_MINUS:
                    # Zoom Out with Keyboard
                    self.target_zoom -= 0.1
                    self.target_zoom = max(self.min_zoom, min(self.max_zoom, self.target_zoom))

    def update(self, dt: float) -> None:
        """
        Updates the camera state (e.g., smooth zoom).

        Args:
            dt (float): Delta time.

        Returns:
            None
        """
        # Handle continuous camera movement via keyboard
        keys = pygame.key.get_pressed()
        speed = 500.0 * dt / self.zoom  # Adjust speed based on zoom so movement is consistent relative to screen

        if keys[pygame.K_w] or keys[pygame.K_UP]:
            self.camera_y -= speed
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            self.camera_y += speed
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            self.camera_x -= speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            self.camera_x += speed

        # Smooth zoom interpolation
        # Using linear interpolation (Lerp) with a factor of 5.0 for smooth transition
        self.zoom += (self.target_zoom - self.zoom) * 5.0 * dt

class WorldRenderer:
    """
    Handles the pure drawing logic for the game world.

    Attributes:
        screen (pygame.Surface): The surface to render to.
        yukkurrium (Yukkurrium): The world view manager.
        rm (ResourceManager): The resource manager for fetching assets.
        font_cache (dict): Cache of pygame fonts.
    """

    def __init__(self, screen: pygame.Surface, yukkurrium: Yukkurrium, resource_manager: ResourceManager):
        """
        Initializes the WorldRenderer.

        Args:
            screen (pygame.Surface): The target Pygame surface.
            yukkurrium (Yukkurrium): The world view manager.
            resource_manager (ResourceManager): The resource manager.
        """
        self.screen = screen
        self.yukkurrium = yukkurrium
        self.rm = resource_manager
        self.font_cache: dict[int, pygame.font.Font] = {}

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
            # However, SysFont implementation in pygame-ce might return Font or SysFont (which wraps Font).
            # The type hint in stubs for SysFont returns Font.
            self.font_cache[size] = pygame.font.SysFont(None, size)
        return self.font_cache[size]

    def render(self, world: World) -> None:
        """
        Renders the world grid and all visible entities.

        Args:
            world (World): The ECS World.

        Returns:
            None
        """
        # Render background grid
        self.draw_grid()

        # Render entities
        entities = world.get_entities_with(Transform, Sprite, PhysicsBody, VisualTransform)
        # Sort by Y for depth (ground position)
        # Handle cases where component might be missing (though get_entities_with should ensure it)
        # We use a default value if not found, but it should be found.
        entities.sort(key=lambda e: getattr(world.get_component(e, Transform), 'y', 0))

        sw, sh = self.screen.get_size()

        for ent in entities:
            transform = world.get_component(ent, Transform)
            sprite = world.get_component(ent, Sprite)
            phys_body = world.get_component(ent, PhysicsBody)
            visual_transform = world.get_component(ent, VisualTransform)

            if transform is None or sprite is None or phys_body is None or visual_transform is None:
                # logger.warning(f"Entity {ent} is missing one or more required components for rendering.")
                continue

            # --- Draw Shadow ---
            shadow_x, shadow_y = self.yukkurrium.world_to_screen(
                visual_transform.shadow_position.x,
                visual_transform.shadow_position.y,
                sw, sh
            )
            shadow_radius_x = int(sprite.width * transform.scale * self.yukkurrium.zoom * 0.4)
            shadow_radius_y = int(shadow_radius_x * 0.5)

            # --- Draw Sprite ---
            img = self.rm.load_image(sprite.image_name)

            # Calculate screen position
            base_screen_x, base_screen_y = self.yukkurrium.world_to_screen(transform.x, transform.y, sw, sh)

            # Apply vertical offset for hopping effect, scaled by zoom
            screen_y = base_screen_y - (visual_transform.vertical_offset * self.yukkurrium.zoom)

            # Scale
            scale = transform.scale * self.yukkurrium.zoom

            # Handle animation
            img_width, img_height = img.get_size()

            if sprite.frame_count > 1:
                source_rect = pygame.Rect(0, 0, sprite.width, sprite.height)
                sx = sprite.current_frame * sprite.width
                if sx + sprite.width <= img_width:
                    source_rect.x = sx

                # Ensure source_rect is within image bounds
                if source_rect.right > img_width or source_rect.bottom > img_height:
                    # If image is smaller than expected (e.g. placeholder), scale it or clip
                    # For placeholder (which is usually small), we just use the whole image
                    if img_width < sprite.width or img_height < sprite.height:
                        frame_img = pygame.transform.scale(img, (sprite.width, sprite.height))
                    else:
                        frame_img = img.subsurface(source_rect.clip(img.get_rect()))
                else:
                    frame_img = img.subsurface(source_rect)
            else:
                # Single frame: if dimensions don't match, we assume we want to scale
                # to fit the target sprite size (e.g., high-res asset for smaller item).
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
                    continue
                scaled_img = pygame.transform.scale(frame_img, (w, h))
            else:
                scaled_img = frame_img

            # Center the sprite
            rect = scaled_img.get_rect(center=(int(base_screen_x), int(screen_y)))

            # Culling
            if rect.colliderect(self.screen.get_rect()):
                if shadow_radius_x > 0 and shadow_radius_y > 0:
                    shadow_color = (0, 0, 0, 100) # RGBA with transparency
                    shadow_surface = pygame.Surface((shadow_radius_x * 2, shadow_radius_y * 2), pygame.SRCALPHA)
                    pygame.draw.ellipse(shadow_surface, shadow_color, shadow_surface.get_rect())
                    self.screen.blit(shadow_surface, (shadow_x - shadow_radius_x, shadow_y - shadow_radius_y))
                self.screen.blit(scaled_img, rect)

                # Selection highlight
                selectable = world.get_component(ent, Selectable)
                if selectable and selectable.selected:
                    pygame.draw.rect(self.screen, (255, 255, 0), rect, 2)

        # Render Floating Text
        self.render_floating_text(world, sw, sh)

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
        for entity, (transform, text_comp) in world.get_components_tuple(Transform, FloatingText):
            font = self._get_font(text_comp.size)

            # Render text surface
            text_surface = font.render(text_comp.text, True, text_comp.color)

            # Fade out based on lifetime
            if text_comp.max_lifetime > 0:
                alpha = int(255 * (text_comp.lifetime / text_comp.max_lifetime))
                alpha = max(0, min(255, alpha))
                text_surface.set_alpha(alpha)

            # Calculate screen position
            screen_x, screen_y = self.yukkurrium.world_to_screen(transform.x, transform.y, screen_w, screen_h)

            # Center text
            rect = text_surface.get_rect(center=(int(screen_x), int(screen_y)))

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

        start_x, start_y = self.yukkurrium.screen_to_world(0, 0, sw, sh)
        end_x, end_y = self.yukkurrium.screen_to_world(sw, sh, sw, sh)

        start_col = int(start_x // grid_size)
        end_col = int(end_x // grid_size) + 1
        start_row = int(start_y // grid_size)
        end_row = int(end_y // grid_size) + 1

        for col in range(start_col, end_col):
            x = col * grid_size
            sx, _ = self.yukkurrium.world_to_screen(x, 0, sw, sh)
            pygame.draw.line(self.screen, (50, 50, 50), (int(sx), 0), (int(sx), sh))

        for row in range(start_row, end_row):
            y = row * grid_size
            _, sy = self.yukkurrium.world_to_screen(0, y, sw, sh)
            pygame.draw.line(self.screen, (50, 50, 50), (0, int(sy)), (sw, int(sy)))

class RenderSystem(System):
    """
    System responsible for rendering the game world and entities.

    Attributes:
        renderer (WorldRenderer): The world renderer.
    """

    def __init__(self, screen: pygame.Surface, world: World):
        """
        Initializes the RenderSystem.

        Args:
            screen (pygame.Surface): The target Pygame surface.
            world (World): The ECS World instance (used to locate services).
        """
        yukkurrium = world.services.get(Yukkurrium)
        rm = world.services.get(ResourceManager)
        self.renderer = WorldRenderer(screen, yukkurrium, rm)

    def update(self, world: World, dt: float) -> None:
        """
        Renders the world grid and all visible entities.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.

        Returns:
            None
        """
        self.renderer.render(world)

class TimeSystem(System):
    """
    System that tracks the total elapsed game time.

    Attributes:
        total_time (float): The total accumulated time.
        game_speed (float): The speed multiplier for time.
    """

    def __init__(self) -> None:
        """Initializes the TimeSystem."""
        self.total_time = 0.0
        self.game_speed = 1.0

    def update(self, world: World, dt: float) -> None:
        """
        Updates the total time.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.

        Returns:
            None
        """
        self.total_time += dt * self.game_speed
