#!/usr/bin/env python3
"""Run linting and type checking for the project.

Usage:
    uv run scripts/lint.py
"""

import subprocess
import sys


def check_absolute_imports() -> bool:
    """Scan src/yukkuri_game/ for absolute package imports.

    Returns:
        bool: True if clean, False if errors are found.
    """
    import os
    import re
    from pathlib import Path

    print("=" * 60)
    print("Running Absolute Imports Check...")
    print("=" * 60)

    absolute_import_pat = re.compile(
        r"^\s*(from|import)\s+(src\.)?yukkuri_game\b"
    )
    failed = False
    src_dir = Path(__file__).parent.parent / "src" / "yukkuri_game"

    for root, _, files in os.walk(src_dir):
        for file in files:
            if not file.endswith(".py"):
                continue
            file_path = Path(root) / file

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
                continue

            for line_no, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                code_part = stripped.split("#")[0].strip()
                if absolute_import_pat.match(code_part):
                    rel = file_path.relative_to(src_dir.parent.parent)
                    print(
                        f"Error in {rel}:{line_no}: "
                        f"Absolute import of yukkuri_game package is banned "
                        f"inside src/yukkuri_game. Use relative imports "
                        f"instead: '{line.strip()}'"
                    )
                    failed = True

    if failed:
        print()
        print("Absolute imports check FAILED!")
        return False

    print("Absolute imports check PASSED!")
    return True


def main() -> int:
    """Run ruff, ty, and custom absolute import check."""
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

    print()
    imports_clean = check_absolute_imports()

    # Return non-zero if any tool failed
    if ruff_result.returncode != 0 or ty_result.returncode != 0 or not imports_clean:
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
