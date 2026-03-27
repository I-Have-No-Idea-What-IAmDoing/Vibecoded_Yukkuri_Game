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

## 2026-10-29 - [Renderer Pipeline Double-Sort]
**Learning:** `Renderer` was sorting commands by `(layer, z_index)` and `PygameBackend` was buffering and sorting them *again*. Removing the backend buffer and sorting, and using immediate rendering with bucketed layers in `Renderer` eliminated the double-sort and list overhead, yielding a ~7% frame time improvement.
**Action:** Use "immediate mode" for backends where possible. Organize render queues by layer (buckets) to avoid expensive global sorting and allow faster per-layer sorts (using `attrgetter`).

## 2026-02-02 - [Perception System Component Lookups]
**Learning:** `PerceptionSystem` was performing O(Observers * Targets) component lookups via `world.try_get_component` which incurs significant function call and wrapper overhead. Pre-fetching component maps (`world.get_components`) at the start of the frame reduced tick time by ~28% (from 154ms to 110ms for 500 observers).
**Action:** When a system iterates O(N*M) times over entities, pre-fetch component maps into dictionaries to replace O(K) lookup overhead with O(1) dict access.

## 2026-02-05 - [Perception System Throttling]
**Learning:** `PerceptionSystem` was paying the cost of building O(N) component maps every frame, even though entities are throttled to update only 10 times/second (often resulting in 0 updates per frame). By checking if any entity actually needs updating *before* building the maps, we saved significant overhead (frame time reduced by ~50%).
**Action:** When a system processes a subset of entities (throttled/conditional), perform the condition check first and gather the work list before performing expensive setup steps like bulk component fetching.

## 2026-02-12 - [Render Cache Thrashing]
**Learning:** `PygameBackend` shadow cache was growing unbounded due to continuous altitude changes causing unique shadow keys (rx, ry, alpha). Additionally, `SurfaceCache` (max 200) was thrashing with 300+ rotating entities.
**Action:** Quantize continuous rendering parameters (like altitude-based shadow size) to improve cache hit rates. Use bounded caches (clear-on-full or LRU) for dynamic assets to prevent memory leaks. Increased `SurfaceCache` to 2000 to handle larger scenes.

## 2026-10-31 - [ECS Query Iteration Optimization]
**Learning:** `world.get_entities_with` does a `esper.get_components` query, extracts just the entity ID via a list comprehension, and discards the component references. The caller then typically iterates those entity IDs and calls `world.get_component(eid, ...)` inside a loop. `try_get_component` and `get_component` inside a loop is extremely slow in python compared to just iterating the components returned from `get_components_tuple`. Using `world.get_components_tuple(...)` is ~50x faster.
**Action:** Never use `world.get_entities_with` followed by `world.get_component` in a loop. Always use `world.get_components_tuple` to retrieve the entity ID and all requested components in a single, fast iteration.
