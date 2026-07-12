# BRIEFING — 2026-06-29T22:02:15Z

## Mission
Implement and verify Bevy-based need decay, metabolism, and waste simulation systems.

## 🔒 My Identity
- Archetype: worker
- Roles: implementer, qa, specialist
- Working directory: c:\Users\gamin\OneDrive\Documents\Git\Vibecoded_Yukkuri_Game\.agents\worker_1
- Original parent: cee1a69a-a6cc-4df6-80c0-afef4ffb07e3
- Milestone: Milestone 1: Need Decay, Metabolism, and Waste Simulation

## 🔒 Key Constraints
- Main Thread Execution for Python updates, single-threaded/exclusive system.
- GIL acquired once per frame.
- Coordinate border translation: Python y = World Height - Bevy y.
- Update adapter's blackboard in-place or traverse BT nodes to update `world` reference.
- Avian 2D v0.7 & Bevy 0.19 API integration: `MoveAndSlide::intersections` accepts third `Entity` parameter.
- Bevy 0.19 ECS Query & API Design Rules (disjoint queries, messages instead of events, hierarchy despawning, PyO3 0.23 string arguments).
- Keep agent metadata only in `.agents/`.
- No cheats, no facade/dummy implementation.

## Change Tracker
- **Files modified**: None yet
- **Build status**: [TBD]
- **Pending issues**: None

## Quality Status
- **Build/test result**: [TBD]
- **Lint status**: [TBD]
- **Tests added/modified**: None yet

## Loaded Skills
- None

## Current Parent
- Conversation ID: cee1a69a-a6cc-4df6-80c0-afef4ffb07e3
- Updated: not yet

## Task Summary
- **What to build**: Rust need decay, poop spawning, cleanliness decay from proximity, poop cleaning message, mouse clean system, plugins.
- **Success criteria**: All systems implemented, integrated, and passing new Rust integration tests (and existing tests passing).
- **Interface contracts**: `PROJECT.md` / `SCOPE.md` if any.
- **Code layout**: src/simulation/needs.rs, src/simulation/mod.rs, tests/simulation_tests.rs.

## Key Decisions Made
- [TBD]

## Artifact Index
- None
