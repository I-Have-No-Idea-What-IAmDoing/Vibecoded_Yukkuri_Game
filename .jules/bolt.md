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

## 2026-10-26 - [Pygame Renderer Optimization]
**Learning:** `PygameBackend` was performing `surface.copy()` for every transparent sprite and `font.render()` for every text label every frame. This created massive GC pressure and CPU overhead.
**Action:** Use `set_alpha` toggling (apply alpha, blit, restore alpha) instead of copying surfaces. Always cache rendered text surfaces using an LRU cache.

## 2026-10-27 - [Physics System Optimization]
**Learning:** `PhysicsSystem` was syncing `Transform` components for every entity every frame, even for static objects. Enabling Pymunk's `sleep_time_threshold` allows skipping physics steps for resting bodies, and we can skip the Python-side sync for `is_sleeping` bodies. This reduced tick time from ~20ms to ~4ms (5.3x speedup) for 5000 static entities.
**Action:** Enable physics engine sleeping and skip component synchronization for sleeping bodies to avoid O(N) overhead on static scenes.

## 2026-10-28 - [Render Cache Invalidation Optimization]
**Learning:** `RenderSystem` background cache was invalidating on every pixel of camera movement, effectively disabling the cache during scrolling. Adding a margin-based invalidation check (rebuild only when offset > margin) restores caching benefits while scrolling.
**Action:** When implementing spatial caches (grids, terrain), implement "loose" invalidation with a safe margin to avoid rebuilding on every frame of movement.
