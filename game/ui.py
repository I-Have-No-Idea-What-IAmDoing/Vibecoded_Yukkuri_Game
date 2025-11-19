from __future__ import annotations
import pygame
from typing import List, Tuple, Dict, Any, TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from game.app import App
    from simulation.agent import Agent

class SpeechBubble:
    def __init__(self, text: str, agent: Agent, duration: float = 3.0) -> None:
        self.text: str = text
        self.agent: Agent = agent
        self.timer: float = duration

class SpeechBubbleManager:
    def __init__(self) -> None:
        self.bubbles: List[SpeechBubble] = []
        self.font: pygame.font.Font = pygame.font.Font(None, 20)

    def add_bubble(self, data: Dict[str, Any]) -> None:
        agent: Agent = data['agent']
        text: str = data['text']
        self.bubbles = [b for b in self.bubbles if b.agent != agent]
        self.bubbles.append(SpeechBubble(text, agent))

    def update(self, delta_time: float) -> None:
        for bubble in self.bubbles:
            bubble.timer -= delta_time
        self.bubbles = [b for b in self.bubbles if b.timer > 0]

    def draw(self, surface: pygame.Surface, grid_size: int) -> None:
        for bubble in self.bubbles:
            pos_x = int(bubble.agent.position[0] * grid_size + grid_size / 2)
            pos_y = int(bubble.agent.position[1] * grid_size - 10)

            text_surf = self.font.render(bubble.text, True, (0, 0, 0))
            text_rect = text_surf.get_rect(center=(pos_x, pos_y))

            bubble_rect = text_rect.inflate(10, 10)
            pygame.draw.rect(surface, (255, 255, 255), bubble_rect, border_radius=5)
            pygame.draw.rect(surface, (0, 0, 0), bubble_rect, 1, border_radius=5)

            surface.blit(text_surf, text_rect)

class UI:
    def __init__(self, app: App) -> None:
        self.app: App = app
        self.font: pygame.font.Font = pygame.font.Font(None, 24)
        self.hud_font: pygame.font.Font = pygame.font.Font(None, 18)
        self.inventory_panel_rect: pygame.Rect = pygame.Rect(
            self.app.screen_width - 200, 0, 200, self.app.screen_height
        )
        self.item_button_rects: List[Tuple[pygame.Rect, Dict[str, Any]]] = []
        self.speech_bubble_manager: SpeechBubbleManager = SpeechBubbleManager()

    def draw_placement_ui(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, (50, 50, 50), self.inventory_panel_rect)

        y_offset = 10
        self.item_button_rects = []
        for i, item_def in enumerate(self.app.world.inventory):
            item_text = f"{i+1}. {item_def['display_name']}"
            text_surf = self.font.render(item_text, True, (255, 255, 255))

            button_rect = pygame.Rect(
                self.inventory_panel_rect.x + 10, y_offset, self.inventory_panel_rect.width - 20, 30
            )
            self.item_button_rects.append((button_rect, item_def))

            placement_mode = self.app.modes['placement']
            if placement_mode.selected_item_def and placement_mode.selected_item_def['id'] == item_def['id']:
                 pygame.draw.rect(surface, (100, 100, 0), button_rect)

            surface.blit(text_surf, (button_rect.x + 5, button_rect.y + 5))
            y_offset += 40

    def draw_agent_hud(self, surface: pygame.Surface) -> None:
        """Draws a simple HUD for each agent showing their name and top need."""
        grid_size = self.app.modes['placement'].grid_size
        for agent in self.app.agents:
            # Find the most urgent need
            top_need: Optional[str] = None
            min_value = float('inf')
            for need in agent.needs.values():
                if need.value < min_value:
                    min_value = need.value
                    top_need = need.name

            # Display text below the agent
            if top_need:
                hud_text = f"{agent.display_name} ({top_need})"
                text_surf = self.hud_font.render(hud_text, True, (0, 0, 0))
                pos_x = int(agent.position[0] * grid_size + grid_size / 2)
                pos_y = int(agent.position[1] * grid_size + grid_size + 10)
                text_rect = text_surf.get_rect(center=(pos_x, pos_y))
                surface.blit(text_surf, text_rect)
