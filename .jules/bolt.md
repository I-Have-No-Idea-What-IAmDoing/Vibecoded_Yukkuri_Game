## 2026-01-13 - [ECS Query Optimization]
**Learning:** `esper.get_components` allows batched retrieval which is ~23x faster than `get_entities_with` + loop `get_component`. Legacy tests mocked implementation details causing brittle tests; tests should verify behavior or mock the new method.
**Action:** Prefer `get_components_tuple` for multi-component iteration. Update mocks when changing ECS query patterns.

## 2025-05-21 - [Sector System Optimization]
**Learning:** `SectorSystem` was rebuilding the spatial map for every entity every frame, consuming ~13ms for 5000 static entities. Adding a simple dirty check (`x != prev_x`) reduced this to ~4ms (3x speedup).
**Action:** Always check for state changes before performing expensive spatial updates, especially for systems iterating over all entities.

## 2026-10-24 - [Render System Optimization]
**Learning:** `RenderSystem` was iterating all `FloatingText` entities every frame, regardless of visibility. By using the pre-calculated `visible_entities` list from `SectorMap`, we reduced checks from O(Total) to O(Visible).
**Action:** Use `visible_entities` for all renderable components, not just Sprites.

## 2026-10-25 - [Perception Throttling & Cache Identity]
**Learning:** `VisibilitySystem` was creating new `set` objects even on cache hits, preventing consumers like `PerceptionSystem` from efficiently detecting changes via `id()` checks. By returning the cached `set` object directly, downstream systems can skip processing with O(1) checks.
**Action:** When caching collections, reuse the collection object itself on cache hits to enable identity-based dirty checks in dependent systems.
