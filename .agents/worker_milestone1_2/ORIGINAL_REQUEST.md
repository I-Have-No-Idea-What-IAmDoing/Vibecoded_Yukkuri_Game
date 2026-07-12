## 2026-06-21T00:08:11Z

Please implement Milestones 1 and 2 of the Bevy-Rust migration plan.

1. Initialize a Cargo binary project in the repository root.
2. Configure Cargo.toml with dependencies:
   - bevy = "0.19.0"
   - avian2d = "0.7.0"
   - pyo3 = { version = "0.23.3", features = ["auto-initialize"] }
   - serde = { version = "1.0", features = ["derive"] }
   - serde_json = "1.0"
   - toml = "0.8"
   - rmp-serde = "1.3"
3. Implement PyO3 FFI boundary structs in Rust:
   - TargetInfo: entity_id (u32), stable_id (u64), type_id (String), growth_stage (String), x (f32), y (f32), distance (f32), affinity (f32), is_threat (bool), is_prey (bool), is_family (bool), tags (HashSet<String>).
   - Blackboard: entity_id (u32), stats (HashMap<String, f32>), x (f32), y (f32), altitude (f32), flight_state (u32), visible_targets (Vec<TargetInfo>), current_action (String), short_term_memory (HashMap<u32, (f32, f32, f32)>), type_id (String), growth_stage (String).
   - CommandType: Enum containing MoveTo, Flee, Speak, PlayAnimation, Attack, Interact, ModifyStat.
   - Command: cmd_type (CommandType), entity_id (u32), payload (HashMap<String, String>).
   - Handle Y-axis coordinate conversion at the FFI boundary between Pygame's Y-down and Bevy's Y-up system using: Python y = World Height - Bevy y.
4. Expose these structs and enums to Python using #[pyclass] and #[pymethods]. Make sure Command has a #[new] constructor that Python can call.
5. Create a basic game loop structure in src/main.rs.
6. Verify your implementation compiles cleanly using cargo check/build.
7. Write your progress and handoff report to '.agents/worker_milestone1_2/handoff.md'.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
