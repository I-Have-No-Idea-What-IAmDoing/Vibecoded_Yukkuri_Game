## 2026-06-21T04:57:00Z

Please execute the following tasks to fix the behavior tree caching closure bug and verify the Rust Bevy-Python FFI migration:

1. Run the integration test using `cargo test --test migration_test` to verify if it compiles and see if there are any failures or hangs.
2. In `src/yukkuri_game/game/systems/behavior_ffi.py`, locate the `tick_entity_with_blackboard` FFI entry point.
3. Observe how behavior trees are cached:
   ```python
   if entity_id not in _behavior_trees:
       world_adapter = BevyWorldAdapter(blackboard)
       # ...
       _behavior_trees[entity_id] = tree
   else:
       world_adapter = BevyWorldAdapter(blackboard)
       for node in _behavior_trees[entity_id].root.iterate():
           if hasattr(node, "world"):
               node.world = world_adapter
   ```
4. Address the behavior tree caching closure bug:
   - When the behavior tree is first created, functions like `check_goal` and `check_target_exists` capture the local `world_adapter` reference lexically. Re-creating `world_adapter` on subsequent ticks does not update these closures, causing them to query a stale snapshot.
   - Solve this by caching the `world_adapter` instance itself (e.g. in a global dictionary `_world_adapters`) and updating it in-place.
   - Define a method `update_blackboard(self, blackboard)` on `BevyWorldAdapter` to update `self.blackboard`.
   - In `tick_entity_with_blackboard`, retrieve the cached `world_adapter` for the `entity_id` and update its blackboard in-place, instead of creating a new `BevyWorldAdapter` and trying to patch individual node attributes.
5. Ensure code-style-guide compliance:
   - The file `behavior_ffi.py` must pass `uvx ruff check .` without errors. Keep variables/methods clean and typed.
6. Re-run `cargo test --test migration_test` and make sure it passes.
7. Write a detailed handoff report in your folder `.agents/worker_verification_1/handoff.md` summarizing the changes, the tests run, and the outcomes.

## 2026-06-21T05:00:14Z

Please fix the behavior tree caching closure bug in the FFI module and verify the integration tests.

1. **Bug Investigation**:
   - Examine `src/yukkuri_game/game/systems/behavior_ffi.py` and `src/yukkuri_game/game/ai/behaviors/trees.py`.
   - The closures `check_goal` and `check_target_exists` created during `create_yukkuri_behavior_tree` capture the `world` (adapter) reference at construction time. Because the FFI ticking system originally constructed a new `BevyWorldAdapter` on each tick, the closures continued referencing the stale first adapter instance with outdated blackboard data.

2. **Implement the Fix**:
   - In `src/yukkuri_game/game/systems/behavior_ffi.py`, add a global registry for world adapters: `_world_adapters: dict[int, BevyWorldAdapter] = {}`.
   - Add a method to `BevyWorldAdapter` to update its blackboard and state dynamically:
     ```python
     def update_blackboard(self, blackboard: Any) -> None:
         self.blackboard = blackboard
         self.time = blackboard.stats.get("game_time", 0.0)
         self.targets = {t.entity_id: t for t in blackboard.visible_targets}
         # Ensure command queue is cleared or re-initialized for the new tick
         self.command_queue.clear()
     ```
     *(Make sure you also add a `clear` method to the mocked `CommandQueue` if it doesn't already have one, or re-instantiate it).*
   - Update `tick_entity_with_blackboard` to fetch the cached `BevyWorldAdapter` from `_world_adapters`, call `update_blackboard` on it, and update the nodes' `world` reference to this adapter.

3. **Verify and Test**:
   - Run python behavior FFI tests: `uv run pytest tests/ai/test_behavior_ffi.py -v`.
   - Run the Rust integration test to ensure all compile and pass: `cargo test --test migration_test`. (On Windows, ensure you prepend the Python DLL directory to PATH if needed).
   - Write your handoff and results to `.agents/worker_verification_1/handoff.md`.

