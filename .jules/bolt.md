## 2026-01-13 - [ECS Query Optimization]
**Learning:** `esper.get_components` allows batched retrieval which is ~23x faster than `get_entities_with` + loop `get_component`. Legacy tests mocked implementation details causing brittle tests; tests should verify behavior or mock the new method.
**Action:** Prefer `get_components_tuple` for multi-component iteration. Update mocks when changing ECS query patterns.
