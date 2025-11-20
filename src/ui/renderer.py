import pygame

class Renderer:
    def __init__(self, screen, width, height):
        self.screen = screen
        self.width = width
        self.height = height
        self.font = pygame.font.SysFont(None, 24)

    def render(self, game_state):
        self.screen.fill((20, 20, 40)) # Dark background

        # Draw Items
        for item in game_state['items']:
            rect = pygame.Rect(item.position[0] - 10, item.position[1] - 10, 20, 20)
            pygame.draw.rect(self.screen, item.color, rect)
            # Label
            # text = self.font.render(item.name[0], True, (255, 255, 255))
            # self.screen.blit(text, (item.position[0]-5, item.position[1]-5))

        # Draw Yukkuris
        for yukkuri in game_state['yukkuris']:
            pos = (int(yukkuri.position[0]), int(yukkuri.position[1]))
            color = yukkuri.color

            # Highlight selection
            if game_state['selected_yukkuri'] == yukkuri:
                pygame.draw.circle(self.screen, (255, 255, 255), pos, 22, 2)

            pygame.draw.circle(self.screen, color, pos, 20)

            # Status indicator (Hunger)
            hunger_pct = yukkuri.stats['hunger'] / yukkuri.max_stats['hunger']
            bar_color = (0, 255, 0) if hunger_pct > 0.5 else (255, 0, 0)
            pygame.draw.rect(self.screen, (50, 50, 50), (pos[0]-20, pos[1]-30, 40, 5))
            pygame.draw.rect(self.screen, bar_color, (pos[0]-20, pos[1]-30, 40 * hunger_pct, 5))

    def render_ui(self, game_state):
        # Top Bar: Money
        text = self.font.render(f"Money: ${game_state['money']}", True, (255, 255, 255))
        self.screen.blit(text, (10, 10))

        # Selection Panel
        sel = game_state['selected_yukkuri']
        if sel:
            panel_rect = pygame.Rect(self.width - 250, 0, 250, self.height)
            pygame.draw.rect(self.screen, (50, 50, 60), panel_rect)

            y_off = 20
            lines = [
                f"Type: {sel.type_name}",
                f"Health: {sel.stats['health']:.1f}",
                f"Hunger: {sel.stats['hunger']:.1f}",
                f"Happiness: {sel.stats['happiness']:.1f}",
                f"Energy: {sel.stats['energy']:.1f}",
                f"Action: {sel.current_action}",
                f"Quality: {sel.quality_score:.1f}"
            ]

            for line in lines:
                t = self.font.render(line, True, (255, 255, 255))
                self.screen.blit(t, (self.width - 240, y_off))
                y_off += 30

            # Sell Button (Visual only, handled in UI logic)
            sell_rect = pygame.Rect(self.width - 240, y_off + 20, 100, 40)
            pygame.draw.rect(self.screen, (0, 150, 0), sell_rect)
            t = self.font.render("SELL", True, (255, 255, 255))
            self.screen.blit(t, (self.width - 220, y_off + 30))

        # Instructions
        inst = self.font.render("1: BeanPaste ($10) | 2: SweetBun ($25) | 3: Bed ($100) | S: Sell Selected", True, (200, 200, 200))
        self.screen.blit(inst, (10, self.height - 30))
