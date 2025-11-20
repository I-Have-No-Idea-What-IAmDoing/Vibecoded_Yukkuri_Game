import pygame

class Interface:
    def __init__(self, game):
        self.game = game
        # Define UI geometry
        # We rely on game width to know where the panel is
        self.panel_width = 250
        self.sell_button_rect = None # Will be calculated based on layout

    def handle_input(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_1:
                self.game.selected_item_type = "BeanPaste"
                print("Selected: BeanPaste")
            elif event.key == pygame.K_2:
                self.game.selected_item_type = "SweetBun"
                print("Selected: SweetBun")
            elif event.key == pygame.K_3:
                self.game.selected_item_type = "Bed"
                print("Selected: Bed")
            elif event.key == pygame.K_s:
                self.sell_selected()
            elif event.key == pygame.K_SPACE:
                # Spawn debug yukkuri
                self.game.yukkurrium.spawn_yukkuri("Reimu")
            return True # Consumed

        elif event.type == pygame.MOUSEBUTTONDOWN:
            x, y = event.pos
            # Check if click is within the UI Panel area
            if x > self.game.width - self.panel_width:
                # We are in the panel.
                # Check specific buttons if they exist
                if self.game.selected_yukkuri:
                    # Recalculate Sell button rect to match Renderer (Hacky but effective for MVP)
                    # Renderer uses 7 lines * 30 + 20 offset + 20 padding
                    # y = 20 + (7 * 30) + 20 = 250
                    # x = width - 240
                    # w = 100, h = 40
                    sell_rect = pygame.Rect(self.game.width - 240, 250, 100, 40)
                    if sell_rect.collidepoint(x, y):
                        self.sell_selected()

                return True # Consume event so we don't click "through" the UI

        return False # Not consumed

    def sell_selected(self):
        if self.game.selected_yukkuri:
            val = self.game.yukkurrium.sell_yukkuri(self.game.selected_yukkuri)
            print(f"Sold for {val}!")
            self.game.selected_yukkuri = None
