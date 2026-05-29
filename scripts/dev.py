#!/usr/bin/env python3
"""Run the game in development mode.

Usage:
    uv run scripts/dev.py [args...]

Examples:
    uv run scripts/dev.py             # Run in graphical mode
    uv run scripts/dev.py --headless  # Run in headless mode
"""

import argparse
from datetime import datetime
import os
from pathlib import Path
import subprocess
import sys


def main() -> int:
    """Run the game with development features and optional profiling/debugging.

    Returns:
        int: The process exit code.
    """
    parser = argparse.ArgumentParser(
        description="Development wrapper for Yukkuri Raising Game",
        add_help=False,
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug log level in the game.",
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Run game under cProfile and save profiling data.",
    )

    args, unknown_args = parser.parse_known_args()

    # Build command to run
    game_args = list(unknown_args)
    if args.debug:
        # Check if user already provided --log-level to avoid duplication
        if not any(arg.startswith("--log-level") for arg in game_args):
            game_args.extend(["--log-level", "DEBUG"])

    # Prepare environment with PYTHONFAULTHANDLER
    env = os.environ.copy()
    env["PYTHONFAULTHANDLER"] = "1"

    print("=" * 60)
    print("Starting Yukkuri Raising Game in development mode...")
    print("PYTHONFAULTHANDLER enabled.")
    if args.debug:
        print("Debug logging enabled.")
    print("=" * 60)

    prof_path = None
    if args.profile:
        print("Running under cProfile...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = Path("logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        prof_path = log_dir / f"profile_{timestamp}.prof"

        cmd = [
            sys.executable,
            "-m",
            "cProfile",
            "-o",
            str(prof_path),
            "-m",
            "src.yukkuri_game.main",
        ] + game_args
    else:
        cmd = [sys.executable, "-m", "src.yukkuri_game.main"] + game_args

    try:
        result = subprocess.run(cmd, env=env, check=False)
        returncode = result.returncode
    except KeyboardInterrupt:
        print("\nDevelopment run interrupted by user.")
        returncode = 0

    if args.profile and prof_path:
        print("=" * 60)
        print(f"Profile saved to: {prof_path.resolve()}")
        print("=" * 60)

    return returncode


if __name__ == "__main__":
    sys.exit(main())
