#!/usr/bin/env python3
"""Run linting and type checking for the project.

Usage:
    uv run scripts/lint.py
"""

import subprocess
import sys


def main() -> int:
    """Run ruff and ty."""
    print("=" * 60)
    print("Running Ruff (linter and formatter check)...")
    print("=" * 60)
    ruff_result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "src/"],
        check=False,
    )

    print()
    print("=" * 60)
    print("Running ty (type checker)...")
    print("=" * 60)
    ty_result = subprocess.run(
        [sys.executable, "-m", "ty", "check", "src/"],
        check=False,
    )

    # Return non-zero if any tool failed
    if ruff_result.returncode != 0 or ty_result.returncode != 0:
        print()
        print("=" * 60)
        print("Lint checks FAILED. Please fix the above issues.")
        print("=" * 60)
        return 1

    print()
    print("=" * 60)
    print("All lint checks PASSED!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
