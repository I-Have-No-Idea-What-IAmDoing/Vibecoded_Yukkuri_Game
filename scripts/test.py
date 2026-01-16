#!/usr/bin/env python3
"""Run the project test suite.

Usage:
    uv run scripts/test.py [pytest_args...]

Examples:
    uv run scripts/test.py               # Run all tests
    uv run scripts/test.py tests/unit    # Run only unit tests
    uv run scripts/test.py -v -x         # Verbose, stop on first failure
"""

import subprocess
import sys


def main() -> int:
    """Run pytest with any additional arguments passed through."""
    # Pass through any extra arguments to pytest
    extra_args = sys.argv[1:]

    cmd = [sys.executable, "-m", "pytest"] + extra_args

    print("=" * 60)
    print(f"Running: pytest {' '.join(extra_args)}")
    print("=" * 60)

    result = subprocess.run(cmd, check=False)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
