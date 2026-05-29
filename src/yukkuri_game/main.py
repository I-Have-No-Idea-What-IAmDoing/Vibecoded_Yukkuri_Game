"""
Main entry point for the Yukkuri Raising Game.

This module handles command-line argument parsing and initializes the game
application. Logging is configured here, before any other module code runs.
"""

import argparse
from pathlib import Path

from .config import load_config
from .engine.application import Application
from .engine.logging_setup import setup_logging
from .scenes.main_menu import MainMenuScene


def main() -> None:
    """
    The entry point for the application.

    Parses command-line arguments, configures logging, then constructs and
    runs the Application. Logging flags on the CLI always take precedence
    over values in ``data/config.toml``.
    """
    parser = argparse.ArgumentParser(description="Yukkuri Raising Game")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run in headless mode (no window)",
    )
    parser.add_argument(
        "--log-level",
        default=None,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        metavar="LEVEL",
        help=(
            "Console log level (DEBUG/INFO/WARNING/ERROR). "
            "Overrides the value in config.toml."
        ),
    )
    parser.add_argument(
        "--log-file",
        default=None,
        metavar="PATH",
        help=(
            "Path for the log file. "
            "Defaults to logs/game_YYYYMMDD_HHMMSS.log. "
            "Pass an empty string to disable file logging."
        ),
    )
    args = parser.parse_args()

    # Load config early so we can read [debug] defaults.
    game_config = load_config()
    debug_cfg = game_config.debug

    # Resolve effective values: CLI > config
    effective_level = args.log_level or debug_cfg.log_level
    log_to_file = debug_cfg.log_to_file

    resolved_log_file: Path | None = None
    if args.log_file is not None:
        # Empty string explicitly disables file logging
        if args.log_file == "":
            log_to_file = False
        else:
            resolved_log_file = Path(args.log_file)
            log_to_file = True

    setup_logging(
        level=effective_level,
        log_file=resolved_log_file,
        log_to_file=log_to_file,
    )

    app = Application(headless=args.headless)
    app.scene_manager.push(MainMenuScene(app))
    app.run()


if __name__ == "__main__":
    main()
