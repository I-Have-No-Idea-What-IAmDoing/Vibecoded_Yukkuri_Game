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

### Headless Testing Limitations
The following areas cannot be reliably tested headless. Note this in PR descriptions and suggest manual verification instead:
- **Audio/sound**: `pygame.mixer` may not initialize without a display
- **pygame_gui UI flows**: Buttons, panels, dialogs don't fully function headless
- **OpenGL/shaders**: `pygame-render`/`moderngl` requires a real GL context
- **Performance/FPS**: `GameDriver` uses fixed `dt`, not real frame timing
- **Visual correctness**: Screenshot comparison is brittle; visual polish needs human eyes

### Tips for Writing Good Tests
- Use `driver.seed_rng()` for deterministic behavior
- Use `driver.run_for(seconds)` to advance simulation time
- Use `driver.get_entities_with(ComponentType)` to query world state
- Use `driver.create_yukkuri(type_id, x, y)` to spawn test entities
- Keep tests fast: most should complete in under 1 second of simulated time
- Check `tests/conftest.py` for existing fixtures before creating new ones
