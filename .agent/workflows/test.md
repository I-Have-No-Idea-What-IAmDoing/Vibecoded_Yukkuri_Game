---
description: How to run the test suite
---

// turbo-all

1. Run all tests with:
```bash
uv run scripts/test.py -x --timeout=10 -q
```

2. To run a specific test file:
```bash
uv run scripts/test.py tests/path/to/test_file.py -x --timeout=10 -q
```
