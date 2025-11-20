
import pygame
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.systems.data_loader import DataLoader
from src.core.game import Game
from src.ui.renderer import Renderer
from src.ui.interface import Interface
from src.systems.persistence import Persistence

def main():
    pygame.init()
    pygame.display.set_caption("Yukkuri Raising Game MVP")

    width, height = 1024, 768
    screen = pygame.display.set_mode((width, height))

    # Initialize Systems
    data_loader = DataLoader()
    data_loader.load_all()

    game = Game(data_loader)
    game.width = width
    game.height = height
    game.yukkurrium.width = width
    game.yukkurrium.height = height

    renderer = Renderer(screen, width, height)
    interface = Interface(game)
    persistence = Persistence()

    # Initial Spawn
    game.yukkurrium.spawn_yukkuri("Reimu", 400, 300)
    game.yukkurrium.spawn_yukkuri("Marisa", 500, 300)

    running = True
    while running:
        # Event Loop
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Pass event to Interface first
            handled_by_ui = False
            if event.type in [pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN]:
                handled_by_ui = interface.handle_input(event)

            # Global Keys (Save/Load/Esc)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_F5:
                    persistence.save_game(game)
                elif event.key == pygame.K_F9:
                    persistence.load_game(game)

            # Pass to Game if not handled by UI
            if not handled_by_ui and event.type == pygame.MOUSEBUTTONDOWN:
                game.handle_input(event)

        # Update
        game.update()

        # Render
        renderer.render(game.get_state())
        renderer.render_ui(game.get_state())

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
