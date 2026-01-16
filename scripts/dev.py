#!/usr/bin/env python3
"""Run the game in development mode.

Usage:
    uv run scripts/dev.py [args...]

Examples:
    uv run scripts/dev.py             # Run in graphical mode
    uv run scripts/dev.py --headless  # Run in headless mode
"""

import subprocess
import sys


def main() -> int:
    """Run the game."""
    extra_args = sys.argv[1:]

    cmd = [sys.executable, "-m", "src.yukkuri_game.main"] + extra_args

    print("=" * 60)
    print("Starting Yukkuri Raising Game...")
    print("=" * 60)

    result = subprocess.run(cmd, check=False)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
