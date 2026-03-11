---
description: How to lint and typecheck the project
---

// turbo-all

1. Run the full lint + typecheck pipeline:
```bash
uv run scripts/lint.py
```

This runs Ruff (linter) and Ty (type checker) against `src/`.
