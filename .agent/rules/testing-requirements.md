---
trigger: always_on
---

## Testing Requirements

When fixing bugs or implementing new features that touch game logic, ECS systems, AI behaviors, physics, or services:
1. Always write or update a test using `GameDriver` from `testing/driver.py`.
2. Run the test suite with `uv run scripts/test.py -x --timeout=10 -q` to verify.
3. Never import `pygame.display` or create a visible window in tests.
4. See `docs/headless_testing.md` for GameDriver usage patterns.
5. If a bug fix doesn't have a regression test, the fix is incomplete.

### Exceptions (testing not required)
- Documentation, config files, or CI/workflow changes
- Pure refactoring that doesn't change behavior (renames, type hints, import reordering)
- Asset-only changes (sprites, sounds, TOML data definitions)
- UI/rendering cosmetics that can only be verified visually
