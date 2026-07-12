# BRIEFING — 2026-06-29T17:42:00-05:00

## Mission
Verify, compile, and fix Rust integration tests for Milestone 1.

## 🔒 My Identity
- Archetype: worker
- Roles: implementer, qa, specialist
- Working directory: c:\Users\gamin\OneDrive\Documents\Git\Vibecoded_Yukkuri_Game\.agents\worker_2
- Original parent: cee1a69a-a6cc-4df6-80c0-afef4ffb07e3
- Milestone: Milestone 1: Need Decay, Metabolism, and Waste Simulation

## 🔒 Key Constraints
- CODE_ONLY network mode: no external web access, no curl/wget/etc.
- Main Thread Execution for PyO3, Acquire GIL Once Per Frame.
- Coordinate Border Translation: Python y = World Height - Bevy y.
- Update world references / blackboards in-place rather than fresh adapters.
- Avian 2D v0.7 & Bevy 0.19 API Integration.
- Bevy 0.19 ECS Query & API Design Rules (disjoint queries, messages, despawning, CStr for eval/run).

## Current Parent
- Conversation ID: cee1a69a-a6cc-4df6-80c0-afef4ffb07e3
- Updated: not yet

## Task Summary
- **What to build**: Fix compilation and runtime issues in `tests/simulation_tests.rs`.
- **Success criteria**: Rust tests compile and pass successfully, Python tests pass too.
- **Interface contracts**: PROJECT.md or existing tests.
- **Code layout**: src/ and tests/.

## Key Decisions Made
- [TBD]

## Artifact Index
- [TBD]

## Change Tracker
- **Files modified**: None
- **Build status**: [TBD]
- **Pending issues**: [TBD]

## Quality Status
- **Build/test result**: [TBD]
- **Lint status**: [TBD]
- **Tests added/modified**: None

## Loaded Skills
None
