#!/usr/bin/env python3
"""Run the project test suite with smart parallel execution."""

import importlib.util
import os
import subprocess
import sys


def main() -> int:
    """Run pytest with auto-parallelization and user opt-outs.

    Returns:
        int: The process exit code.
    """
    # Parse arguments
    extra_args = sys.argv[1:]

    # Check for single-threaded opt-outs
    single_threaded = False
    if "--single-threaded" in extra_args:
        single_threaded = True
        extra_args.remove("--single-threaded")

    env_single = os.environ.get("PYTEST_SINGLE_THREADED", "").strip()
    if env_single in ("1", "true", "TRUE"):
        single_threaded = True

    # Check if a specific file/test is targeted (to avoid xdist spawn overhead)
    is_specific_test = any(".py" in arg for arg in extra_args)

    # Check if pytest-xdist is installed
    has_xdist = importlib.util.find_spec("xdist") is not None

    # Check if user passed process count explicitly
    has_n_flag = any(
        arg == "-n" or arg.startswith("--numprocesses")
        for arg in extra_args
    )

    # Determine command
    cmd = [sys.executable, "-m", "pytest"]
    parallel_mode = False

    if (
        has_xdist
        and not single_threaded
        and not is_specific_test
        and not has_n_flag
    ):
        parallel_mode = True
        cmd.extend(["-n", "auto"])

    cmd.extend(extra_args)

    print("=" * 60)
    mode_str = "parallel (xdist)" if parallel_mode else "sequential"
    print(f"Running: pytest {' '.join(cmd[3:])} [{mode_str}]")
    print("=" * 60)

    result = subprocess.run(cmd, check=False)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
