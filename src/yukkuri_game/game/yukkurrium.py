"""
Module handling the game world view and rendering.
"""
import pygame
from ..engine.ecs import System, World
from .components import Transform, Sprite, Selectable, FloatingText
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
            self.target_zoom += event.y * 0.1
            self.target_zoom = max(self.min_zoom, min(self.max_zoom, self.target_zoom))
        elif event.type == pygame.MOUSEMOTION:
            if pygame.mouse.get_pressed()[1]: # Middle mouse button
                dx, dy = event.rel
                self.camera_x -= dx / self.zoom
                self.camera_y -= dy / self.zoom

    def update(self, dt: float) -> None:
        """
        Updates the camera state (e.g., smooth zoom).

        Args:
            dt (float): Delta time.

        Returns:
            None
        """
        # Smooth zoom
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
        self.font_cache: dict = {}

    def _get_font(self, size: int) -> pygame.font.Font:
        """
        Retrieves a font of the specified size from the cache, or creates it.

        Args:
            size (int): The font size.

        Returns:
            pygame.font.Font: The requested font.
        """
        if size not in self.font_cache:
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
        entities = world.get_entities_with(Transform, Sprite)
        # Sort by Y for depth
        entities.sort(key=lambda e: world.get_component(e, Transform).y) # type: ignore

        sw, sh = self.screen.get_size()

        for ent in entities:
            transform = world.get_component(ent, Transform)
            sprite = world.get_component(ent, Sprite)

            if not transform or not sprite:
                continue

            img = self.rm.load_image(sprite.image_name)

            # Calculate screen position
            screen_x, screen_y = self.yukkurrium.world_to_screen(transform.x, transform.y, sw, sh)

            # Scale
            scale = transform.scale * self.yukkurrium.zoom

            # Handle animation (assume horizontal strip)
            frame_width = sprite.width
            frame_height = sprite.height

            # If the image is a sprite sheet, select the current frame
            # Note: If the image is not a sprite sheet (just a single image),
            # sprite.current_frame should be 0.

            # Check if we need to subsurface
            # This assumes the loaded image contains all frames horizontally
            # We need to make sure we don't go out of bounds if image is just one frame
            # but frame_count > 1 (configuration error) or if width is wrong.

            img_width = img.get_width()
            img_height = img.get_height()

            # Default to full image
            source_rect = pygame.Rect(0, 0, img_width, img_height)

            # If sprite says it has frames and the image is wide enough, crop it
            if sprite.frame_count > 1:
                # Calculate x offset
                sx = sprite.current_frame * sprite.width
                if sx + sprite.width <= img_width:
                     source_rect = pygame.Rect(sx, 0, sprite.width, sprite.height)

            # Now create a subsurface or just use the image if it matches
            # But wait, if we scale, we should scale the cropped part.

            # Optimization: if we don't need to crop, don't subsurface
            if source_rect.width == img_width and source_rect.height == img_height:
                frame_img = img
            else:
                frame_img = img.subsurface(source_rect)

            # Apply flips
            if sprite.flip_x or sprite.flip_y:
                frame_img = pygame.transform.flip(frame_img, sprite.flip_x, sprite.flip_y)

            if scale != 1.0:
                # Simple optimization: check if size is reasonable
                w = int(sprite.width * scale)
                h = int(sprite.height * scale)
                if w <= 0 or h <= 0:
                    continue

                scaled_img = pygame.transform.scale(frame_img, (w, h))
            else:
                scaled_img = frame_img

            # Center the sprite
            rect = scaled_img.get_rect(center=(int(screen_x), int(screen_y)))

            # Culling
            if rect.colliderect(self.screen.get_rect()):
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
