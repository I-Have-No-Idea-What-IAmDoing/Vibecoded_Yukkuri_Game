## 2026-06-21T00:38:22Z
Please implement Milestones 3 and 4 of the Bevy-Rust migration plan.

1. **Python World Adapter (`BevyWorldAdapter`) & Entry Point**:
   - Implement `tick_entity_with_blackboard(blackboard) -> list[Command]` inside `src/yukkuri_game/game/systems/behavior_ffi.py`.
   - Implement `BevyWorldAdapter` to mock the esper `World` interface. Intercept behavior tree action queries:
     - `self.world.try_get_component` and `self.world.has_component` for components:
       - `Transform` (with `x`, `y` attributes mapped from `blackboard.x`, `blackboard.y`).
       - `Needs` (with `health`, `hunger`, `social`, `energy`, `cleanliness`, `bladder`, `easiness`, `max_health` mapped from `blackboard.stats`).
       - `YukkuriStats` (with `name`, `type_id`, `growth_stage` mapped from `blackboard.stats` or `blackboard.type_id`/`blackboard.growth_stage`).
       - `AIState` (persist a dictionary `_ai_states: dict[int, AIState]` in python memory mapping `entity_id` to its persistent `AIState` component).
       - `Blackboard` (mock to return target stats like `visible_targets` and `short_term_memory`).
       - `MovementController` and `Flight` (mapped to `blackboard.flight_state`).
       - `EmotionalState` (mapped to `blackboard.stats` keys `happiness`, `stress`).
     - `self.world.services.try_get` for services:
       - `NavigationService`: Mock `request_path` to immediately set the entity's `path = [end]` and set `path_requesting = False` so trees don't block.
       - `GameService`: Mock `find_best_item` to search `blackboard.visible_targets` and return the closest matching item ID.
       - `TimeService`: Mock time fields like `time_elapsed`, `game_speed`, etc.
       - `ISpatialService`: Mock `get_nearest_entity` to search `blackboard.visible_targets` and return the closest entity matching the component class name.
       - `CommandQueue`: Use the existing `CommandQueue` class, collect commands, and convert them to PyO3 `Command` objects.

2. **GIL-Safe Ticking Resource/System (Rust side)**:
   - Implement the `tick_python_ai_system` in Bevy. Run it exclusively on the main thread (GIL-safe) in Bevy's `Update` schedule.
   - For each ticked entity, construct the `Blackboard` struct, convert Y coordinate (`Python y = World Height - Bevy y`), pass to `tick_entity_with_blackboard` via PyO3, and receive `Vec<Command>`.
   - Implement `apply_ai_commands` (the command dispatcher system):
     - `MoveTo`: Insert a `MoveTarget` component on the entity with converted target coordinates (`Bevy y = World Height - Python y`) and acceptance radius.
     - `Flee`: Adjust LinearVelocity directly on the entity's rigid body.
     - `ModifyStat`: Adjust the agent's stats inside `YukkuriAgent` or components.

3. **Verify and Compile**:
   - Verify that your Rust changes compile cleanly and warning-free with `cargo check`.
   - Write your progress and handoff report to `.agents/worker_milestone3_4/handoff.md`.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
