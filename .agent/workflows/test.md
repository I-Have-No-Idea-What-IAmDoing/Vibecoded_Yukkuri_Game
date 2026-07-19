---
description: How to run the test suite (Python & Rust)
---

// turbo-all

### 1. Python Simulation Tests
Run Python integration & E2E tests:
```bash
uv run scripts/test.py -x --timeout=10 -q
```

### 2. Rust Unit & Integration Tests
Run Rust tests using `cargo nextest` (or fallback to `cargo test`):
```bash
cargo nextest run
```

To run Rust doc-tests:
```bash
cargo test --doc
```
