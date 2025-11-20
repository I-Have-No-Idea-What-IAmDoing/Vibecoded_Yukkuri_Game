from src.utils.loader import game_data
from src.engine.game import Game

def main():
    print("Yukkuri Raising Game - Initializing...")

    # Load data
    game_data.load_all()

    if not game_data.configs:
        print("Failed to load configs. Exiting.")
        return

    game = Game()
    game.run()

if __name__ == "__main__":
    main()
