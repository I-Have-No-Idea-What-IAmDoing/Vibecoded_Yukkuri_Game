import pygame
from src.core.yukkurrium import Yukkurrium
from src.ai.utility_ai import UtilityAIEngine

class Game:
    def __init__(self, data_loader):
        self.data_loader = data_loader
        self.width = 800
        self.height = 600
        self.yukkurrium = Yukkurrium(self.width, self.height, data_loader)
        self.ai_engine = UtilityAIEngine(data_loader)
        self.running = True
        self.clock = pygame.time.Clock()
        self.selected_yukkuri = None
        self.selected_item_type = None # For placement

    def update(self):
        dt = self.clock.tick(60) / 1000.0 # Delta time in seconds

        # Update AI and Physics
        for yukkuri in self.yukkurrium.yukkuris:
            self.ai_engine.update(yukkuri, self.yukkurrium, dt)

        self.yukkurrium.update(dt)

    def handle_input(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            x, y = event.pos
            if event.button == 1: # Left click
                # Check for yukkuri selection
                clicked_yukkuri = None
                for yuk in self.yukkurrium.yukkuris:
                    dist = ((yuk.position[0] - x)**2 + (yuk.position[1] - y)**2)**0.5
                    if dist < 20: # Hitbox
                        clicked_yukkuri = yuk
                        break

                if clicked_yukkuri:
                    self.selected_yukkuri = clicked_yukkuri
                    print(f"Selected: {clicked_yukkuri.type_name} (Health: {clicked_yukkuri.stats['health']:.1f})")
                elif self.selected_item_type:
                     # Place item
                     self.yukkurrium.place_item(self.selected_item_type, x, y)

    def get_state(self):
        # Return state for rendering
        return {
            'yukkuris': self.yukkurrium.yukkuris,
            'items': self.yukkurrium.items,
            'money': self.yukkurrium.money,
            'selected_yukkuri': self.selected_yukkuri
        }
