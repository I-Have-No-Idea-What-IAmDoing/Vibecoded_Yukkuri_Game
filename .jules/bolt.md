## 2026-01-13 - [ECS Query Optimization]
**Learning:** `esper.get_components` allows batched retrieval which is ~23x faster than `get_entities_with` + loop `get_component`. Legacy tests mocked implementation details causing brittle tests; tests should verify behavior or mock the new method.
**Action:** Prefer `get_components_tuple` for multi-component iteration. Update mocks when changing ECS query patterns.

## 2025-05-21 - [Sector System Optimization]
**Learning:** `SectorSystem` was rebuilding the spatial map for every entity every frame, consuming ~13ms for 5000 static entities. Adding a simple dirty check (`x != prev_x`) reduced this to ~4ms (3x speedup).
**Action:** Always check for state changes before performing expensive spatial updates, especially for systems iterating over all entities.
