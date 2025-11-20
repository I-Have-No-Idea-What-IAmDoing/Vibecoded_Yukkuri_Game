import pygame
from typing import Any
from src.engine.ecs import EntityManager, Entity
from src.engine.components import Transform, Identity, ItemComponent

class Renderer:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.font = pygame.font.SysFont("Arial", 14)

    def render_game(self, ecs: EntityManager, state: Any):
        # Handle Camera
        camera_x = state.camera_x
        camera_y = state.camera_y
        zoom = state.zoom

        # Render Entities
        # Sort by Y for crude depth sorting
        entities = sorted(ecs.entities, key=lambda e: e.get_component(Transform).y if e.get_component(Transform) else 0)

        for entity in entities:
            transform = entity.get_component(Transform)
            identity = entity.get_component(Identity)
            item = entity.get_component(ItemComponent)

            if not transform:
                continue

            # World to Screen transform
            screen_x = int((transform.x - camera_x) * zoom)
            screen_y = int((transform.y - camera_y) * zoom)
            width = int(transform.width * zoom)
            height = int(transform.height * zoom)

            # Skip if off screen
            if screen_x + width < 0 or screen_x > self.screen.get_width():
                continue
            if screen_y + height < 0 or screen_y > self.screen.get_height():
                continue

            # Draw shape
            color = (255, 255, 255)
            if identity:
                color = identity.color
            elif item:
                 # Fallback for items if not in identity
                 # But items should also have Identity probably?
                 # For now let's check item data or component
                 pass

            # Highlight if selected
            if state.selected_entity_id == entity.id:
                pygame.draw.rect(self.screen, (255, 255, 0), (screen_x - 2, screen_y - 2, width + 4, height + 4), 2)

            if item:
                # Draw item (Circle)
                cx = screen_x + width // 2
                cy = screen_y + height // 2
                pygame.draw.circle(self.screen, color, (cx, cy), width // 2)
            else:
                # Draw Yukkuri (Rect)
                pygame.draw.rect(self.screen, color, (screen_x, screen_y, width, height))

            # Draw Name
            if identity:
                text = self.font.render(identity.name, True, (255, 255, 255))
                self.screen.blit(text, (screen_x, screen_y - 20))
