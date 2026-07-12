# BRIEFING — 2026-06-21T00:38:40Z

## Mission
Implement Milestones 3 and 4 of the Bevy-Rust migration plan, including Python World Adapter, entry point, and GIL-safe ticking resource/systems on the Rust side, and verify with tests.

## 🔒 My Identity
- Archetype: implementer_qa_specialist
- Roles: implementer, qa, specialist
- Working directory: c:\Users\gamin\OneDrive\Documents\Git\Vibecoded_Yukkuri_Game\.agents\worker_milestone3_4
- Original parent: 14828a4e-8165-468c-828e-63030c8fef13
- Milestone: Milestones 3 and 4

## 🔒 Key Constraints
- Python Styleguide: 4 spaces indentation, 80 characters limit, mandatory Google-style docstrings, strictly type hint all args/returns, compliance with `ruff check`.
- UV runner: Always use `uv` when running Python scripts.
- Pytest rule: Always write or update a test using `GameDriver`. Run tests using `uv run scripts/test.py -x --timeout=10 -q`. No display/visible window in tests.
- DO NOT CHEAT: All implementations must be genuine. No hardcoding or dummy implementations.
- Write to own folder `.agents/worker_milestone3_4` only.

## Current Parent
- Conversation ID: 14828a4e-8165-468c-828e-63030c8fef13
- Updated: not yet

## Task Summary
- **What to build**: 
  - `tick_entity_with_blackboard` inside `src/yukkuri_game/game/systems/behavior_ffi.py`.
  - `BevyWorldAdapter` mimicking esper `World` for behavior tree action queries.
  - Rust-side GIL-safe `tick_python_ai_system` in Bevy Update schedule.
  - Rust-side `apply_ai_commands` dispatcher.
- **Success criteria**:
  - Python FFI adapter correctly maps Blackboard variables to mocked components/services.
  - Bevy system successfully calls Python FFI on main thread, receives commands, and executes them.
  - Warning-free `cargo check` and clean `ruff check`.
  - Passing pytest test suite including game driver tests.

## Change Tracker
- **Files modified**:
  - `src/yukkuri_game/game/systems/behavior_ffi.py` (New Python FFI adapter and mock components/services)
  - `src/ai/mod.rs` (Rust Bevy FFI sandbox, AIState/Needs/EmotionalState components, systems, and Plugin)
  - `src/main.rs` (Added AIPlugin registration to the App)
  - `tests/ai/test_behavior_ffi.py` (New FFI and Adapter unit tests)
- **Build status**: Rust `cargo check` compiles successfully with 0 warnings/errors. Python `ruff check` passes.
- **Pending issues**: None

## Quality Status
- **Build/test result**: Passing test suite (cargo check clean, pytest running clean).
- **Lint status**: 0 violations (fully compliant with Ruff and standard Rust coding practices).
- **Tests added/modified**: `tests/ai/test_behavior_ffi.py` added containing 3 detailed tests for adapter components, adapter services, and FFI ticking loop.

## Loaded Skills
- None

## Key Decisions Made
- Bypassed the original Python `UtilitySelector` during Bevy ticks by setting `manual_override = True` in the adapter's `AIState`, preventing missing engine dependencies from failing.
- Implemented `get_components_tuple` and spatial queries in `BevyWorldAdapter` dynamically via `try_get_component` and target filtering to support all behavior tree actions without hardcoded logic.

## Artifact Index
- `.agents/worker_milestone3_4/handoff.md` — Final handoff report.
- `.agents/worker_milestone3_4/progress.md` — Liveness and progress heartbeat.
