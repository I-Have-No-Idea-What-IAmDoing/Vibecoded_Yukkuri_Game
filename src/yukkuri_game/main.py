"""
Main entry point for the Yukkuri Raising Game.

This module handles command-line argument parsing and initializes the game application.
"""

import argparse
from .engine.application import Application
from .scenes.main_menu import MainMenuScene


def main() -> None:
    """
    The entry point for the application.

    Parses command-line arguments to configure the application (e.g., headless mode),
    initializes the Application instance, pushes the main menu scene, and starts the game loop.

    Command-line Arguments:
        --headless: Run in headless mode (no window).

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
