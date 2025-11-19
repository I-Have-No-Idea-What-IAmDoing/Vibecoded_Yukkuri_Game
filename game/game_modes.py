from __future__ import annotations
import pygame
from typing import TYPE_CHECKING, Optional, Dict, Any

if TYPE_CHECKING:
    from game.app import App

class GameMode:
    def __init__(self, app: App) -> None:
        self.app: App = app

    def handle_input(self, event: pygame.event.Event) -> None:
        pass

    def update(self, delta_time: float) -> None:
        pass

    def render(self, surface: pygame.Surface) -> None:
        pass

class LiveMode(GameMode):
    def __init__(self, app: App) -> None:
        super().__init__(app)

    def update(self, delta_time: float) -> None:
        self.app.dialogue_manager.update(delta_time)
        for agent in self.app.agents:
            agent.update(delta_time, self.app.world, self.app)
        self.app.ui.speech_bubble_manager.update(delta_time)

    def render(self, surface: pygame.Surface) -> None:
        surface.fill((200, 200, 255))
        self._draw_placed_items(surface)
        self._draw_agents(surface)
        self.app.ui.speech_bubble_manager.draw(surface, self.app.modes['placement'].grid_size)
        self.app.ui.draw_agent_hud(surface)

    def _draw_placed_items(self, surface: pygame.Surface) -> None:
        grid_size = self.app.modes['placement'].grid_size
        for item in self.app.world.placed_items:
            footprint = item['def']['footprint']
            rect = pygame.Rect(
                item['x'] * grid_size, item['y'] * grid_size,
                footprint['w'] * grid_size, footprint['h'] * grid_size
            )
            pygame.draw.rect(surface, (100, 100, 100), rect)

    def _draw_agents(self, surface: pygame.Surface) -> None:
        grid_size = self.app.modes['placement'].grid_size
        for agent in self.app.agents:
            pos_x = int(agent.position[0] * grid_size + grid_size / 2)
            pos_y = int(agent.position[1] * grid_size + grid_size / 2)
            pygame.draw.circle(surface, (255, 0, 0), (pos_x, pos_y), int(grid_size / 2))

class PlacementMode(GameMode):
    def __init__(self, app: App) -> None:
        super().__init__(app)
        self.selected_item_def: Optional[Dict[str, Any]] = None
        self.grid_size: int = 32
        self.grid_color: Tuple[int, int, int] = (200, 200, 200)

    def handle_input(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_pos = pygame.mouse.get_pos()

            clicked_on_ui = False
            for rect, item_def in self.app.ui.item_button_rects:
                if rect.collidepoint(mouse_pos):
                    self.selected_item_def = item_def
                    clicked_on_ui = True
                    break

            if not clicked_on_ui and self.selected_item_def:
                grid_x, grid_y = mouse_pos[0] // self.grid_size, mouse_pos[1] // self.grid_size
                if self.app.world.is_valid_placement(self.selected_item_def, grid_x, grid_y):
                    self.app.world.place_item(self.selected_item_def, grid_x, grid_y)

    def render(self, surface: pygame.Surface) -> None:
        surface.fill((220, 220, 200))
        self._draw_grid(surface)
        self._draw_placed_items(surface)
        self._draw_ghost_preview(surface)
        self.app.ui.draw_placement_ui(surface)

    def _draw_grid(self, surface: pygame.Surface) -> None:
        for x in range(0, self.app.screen_width, self.grid_size):
            pygame.draw.line(surface, self.grid_color, (x, 0), (x, self.app.screen_height))
        for y in range(0, self.app.screen_height, self.grid_size):
            pygame.draw.line(surface, self.grid_color, (0, y), (self.app.screen_width, y))

    def _draw_placed_items(self, surface: pygame.Surface) -> None:
        for item in self.app.world.placed_items:
            footprint = item['def']['footprint']
            rect = pygame.Rect(
                item['x'] * self.grid_size, item['y'] * self.grid_size,
                footprint['w'] * self.grid_size, footprint['h'] * self.grid_size
            )
            pygame.draw.rect(surface, (100, 100, 100), rect)

    def _draw_ghost_preview(self, surface: pygame.Surface) -> None:
        if self.selected_item_def:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            grid_x, grid_y = mouse_x // self.grid_size, mouse_y // self.grid_size

            is_valid = self.app.world.is_valid_placement(self.selected_item_def, grid_x, grid_y)
            color = (0, 255, 0, 128) if is_valid else (255, 0, 0, 128)

            footprint = self.selected_item_def['footprint']
            ghost_rect = pygame.Rect(
                grid_x * self.grid_size, grid_y * self.grid_size,
                footprint['w'] * self.grid_size, footprint['h'] * self.grid_size
            )

            s = pygame.Surface((ghost_rect.width, ghost_rect.height), pygame.SRCALPHA)
            s.fill(color)
            surface.blit(s, (ghost_rect.x, ghost_rect.y))
