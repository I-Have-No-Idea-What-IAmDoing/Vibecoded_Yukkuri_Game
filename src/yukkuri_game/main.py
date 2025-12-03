"""
Main entry point for the Yukkuri Raising Game.
"""

import argparse
from .engine.application import Application
from .scenes.main_menu import MainMenuScene


def main() -> None:
    """
    The entry point for the application.

    Parses command-line arguments and starts the game loop.

    Returns:
        None
    """
    parser = argparse.ArgumentParser(description="Yukkuri Raising Game")
    parser.add_argument(
        "--headless", action="store_true", help="Run in headless mode (no window)"
    )
    args = parser.parse_args()

    app = Application(headless=args.headless)
    app.scene_manager.push(MainMenuScene(app))
    app.run()


if __name__ == "__main__":
    main()
