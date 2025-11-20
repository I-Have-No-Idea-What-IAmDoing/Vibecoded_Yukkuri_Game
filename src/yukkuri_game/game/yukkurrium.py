import pygame
from ..engine.ecs import System, World
from .components import Transform, Sprite, Selectable
from ..engine.resource_manager import ResourceManager

class Yukkurrium:
    def __init__(self, width=2000, height=2000):
        self.width = width
        self.height = height
        # Camera properties
        self.camera_x = 0
        self.camera_y = 0
        self.zoom = 1.0
        self.target_zoom = 1.0

        # Bounds
        self.min_zoom = 0.5
        self.max_zoom = 2.0

    def world_to_screen(self, wx, wy, screen_w, screen_h):
        sx = (wx - self.camera_x) * self.zoom + screen_w / 2
        sy = (wy - self.camera_y) * self.zoom + screen_h / 2
        return sx, sy

    def screen_to_world(self, sx, sy, screen_w, screen_h):
        wx = (sx - screen_w / 2) / self.zoom + self.camera_x
        wy = (sy - screen_h / 2) / self.zoom + self.camera_y
        return wx, wy

    def handle_input(self, event, screen_w, screen_h):
        if event.type == pygame.MOUSEWHEEL:
            self.target_zoom += event.y * 0.1
            self.target_zoom = max(self.min_zoom, min(self.max_zoom, self.target_zoom))
        elif event.type == pygame.MOUSEMOTION:
            if pygame.mouse.get_pressed()[1]: # Middle mouse button
                dx, dy = event.rel
                self.camera_x -= dx / self.zoom
                self.camera_y -= dy / self.zoom

    def update(self, dt):
        # Smooth zoom
        self.zoom += (self.target_zoom - self.zoom) * 5.0 * dt

class RenderSystem(System):
    def __init__(self, screen: pygame.Surface, yukkurrium: Yukkurrium, resource_manager: ResourceManager):
        self.screen = screen
        self.yukkurrium = yukkurrium
        self.rm = resource_manager

    def update(self, world: World, dt: float):
        # Render background grid
        self.draw_grid()

        # Render entities
        entities = world.get_entities_with(Transform, Sprite)
        # Sort by Y for depth
        entities.sort(key=lambda e: world.get_component(e, Transform).y)

        sw, sh = self.screen.get_size()

        for ent in entities:
            transform = world.get_component(ent, Transform)
            sprite = world.get_component(ent, Sprite)

            img = self.rm.load_image(sprite.image_name)

            # Calculate screen position
            screen_x, screen_y = self.yukkurrium.world_to_screen(transform.x, transform.y, sw, sh)

            # Scale
            scale = transform.scale * self.yukkurrium.zoom

            if scale != 1.0:
                # Simple optimization: check if size is reasonable
                w = int(sprite.width * scale)
                h = int(sprite.height * scale)
                if w <= 0 or h <= 0:
                    continue

                scaled_img = pygame.transform.scale(img, (w, h))
            else:
                scaled_img = img

            # Center the sprite
            rect = scaled_img.get_rect(center=(screen_x, screen_y))

            # Culling
            if rect.colliderect(self.screen.get_rect()):
                self.screen.blit(scaled_img, rect)

                # Selection highlight
                selectable = world.get_component(ent, Selectable)
                if selectable and selectable.selected:
                    pygame.draw.rect(self.screen, (255, 255, 0), rect, 2)

    def draw_grid(self):
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
            pygame.draw.line(self.screen, (50, 50, 50), (sx, 0), (sx, sh))

        for row in range(start_row, end_row):
            y = row * grid_size
            _, sy = self.yukkurrium.world_to_screen(0, y, sw, sh)
            pygame.draw.line(self.screen, (50, 50, 50), (0, sy), (sw, sy))

class TimeSystem(System):
    def __init__(self):
        self.total_time = 0.0
        self.game_speed = 1.0

    def update(self, world: World, dt: float):
        self.total_time += dt * self.game_speed
