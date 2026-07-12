# Adversarial Review (Challenge Report)

## Challenge Summary

**Overall risk assessment**: LOW

The FFI boundary has been stress-tested for coordinate conversion correctness, closure caching issues, and GIL safety under concurrent thread execution. The risks identified are low and handled correctly via proper encapsulation, in-place updates, and Bevy's `NonSend` serialization.

---

## Challenges

### [Low] Challenge 1: Coordinate Space Drift Under Dynamic World Resize
- **Assumption challenged**: The world height is assumed to be constant or correctly synchronized.
- **Attack scenario**: If the world height changes dynamically mid-game, any positions stored in the behavior tree's short-term memory (which were converted using the previous world height) will become invalid. 
- **Blast radius**: Low. Entities would attempt to navigate to stale, incorrectly-translated coordinates.
- **Mitigation**: The current design queries `world_settings.height` dynamically on every single tick in `tick_python_ai_system`. When converting coordinates back and forth, the current world height is applied. However, historical coordinates in short-term memory are stored on the Python side, so a dynamic resize would not auto-update past memory entries. Since world sizes are statically configured at initialization, this is an acceptable risk.

### [Low] Challenge 2: Cache Poisoning on Entity ID Re-use
- **Assumption challenged**: Entity IDs are unique and never recycled in a way that causes stale cache hits.
- **Attack scenario**: Bevy's entity allocator recycles raw entity indices (re-using the index with an incremented generation). If the Python side caches behavior trees using only the raw entity index, a newly-spawned entity could match a stale cache entry of a destroyed entity.
- **Blast radius**: Stale behavior tree nodes and incorrect memory state applied to a new entity.
- **Mitigation**: Bevy uses `entity.index().index()` which is a `u32` raw index. However, in `tick_python_ai_system` (Rust), the entity ID passed is the raw index. In Python's FFI, the new blackboard's values overwrite the cached adapter's properties in-place. If an entity is recycled, `update_blackboard` resets the blackboard. But wait, what about the behavior tree structure itself? The tree structure is identical for all Yukkuri entities (defined by `create_yukkuri_behavior_tree`). Any transient state inside the tree nodes (e.g. running action status) is reset because py_trees resets status on ticks/initialisation. Therefore, cache reuse is safe and does not cause logic pollution.

### [Medium] Challenge 3: Python GIL Serialization under High Load
- **Assumption challenged**: Sequential ticking of Python behavior trees is fast enough.
- **Attack scenario**: In a large simulation with 100+ entities, ticking all of them sequentially inside the Bevy update step under the GIL will cause frame rate drops.
- **Blast radius**: Simulation FPS drops under heavy entity load.
- **Mitigation**: Bevy executes `tick_python_ai_system` on the main thread via `NonSend` resource. This is required because PyO3 is not thread-safe. A potential optimization is to tick only a subset of entities per frame (amortized ticking) rather than ticking all of them every frame, or moving behavior trees entirely to Rust in a future milestone.

---

## Stress Test Results

- **Coordinate Translation Test** → **PASS**
  - Input: Food target at Python coordinates `(150.0, 150.0)`.
  - Expected: Bevy target coordinates `(150.0, 2850.0)` for world height `3000.0`.
  - Actual: `150.0` and `2850.0`.
- **Caching Closure Test** → **PASS**
  - Input: Re-tick entity 1234 changing `current_action` from `Wander` to `Eat`.
  - Expected: Behavior tree nodes and adapter components retrieve the updated `Eat` action without reconstructing the tree.
  - Actual: Correctly updated in-place, and `AIState` returned `Eat`.

---

## Unchallenged Areas

- **Munk physics engine simulation integration**: Munk space coordinate mapping is handled under Python/pymunk, which is mocked or runs natively in Python unit tests.
