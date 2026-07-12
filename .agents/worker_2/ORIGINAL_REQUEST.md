## 2026-06-29T22:40:30Z
You are the replacement Worker subagent for Milestone 1: Need Decay, Metabolism, and Waste Simulation.
Your predecessor (worker_1) failed to execute due to a connection error.
Your task is to compile the Rust project, verify the test suite, and apply any required fixes to tests/simulation_tests.rs:

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT
hardcode test results, create dummy/facade implementations, or
circumvent the intended task. A Forensic Auditor will independently
verify your work. Integrity violations WILL be detected and your
work WILL be rejected.

Please execute these steps precisely:
1. Compile and run the Rust test suite to verify if tests/simulation_tests.rs compiles:
   `cargo test --test simulation_tests`
2. If tests/simulation_tests.rs fails to compile, apply the following fixes:
   - Replace any `.send(...)` method call on `Messages<T>` or `Events<T>` with `.write(...)`.
   - Replace any `.get_reader()` method call on `Messages<T>` or `Events<T>` with `.get_cursor()`.
   - Change `let world = app.world();` to `let world = app.world_mut();` when calling `query_filtered` or mutating the world state in tests.
3. Run `cargo test` and verify that all integration tests compile and pass successfully.
4. If there are python tests in the workspace that are relevant, verify that they pass as well.
5. Write your handoff report to `.agents/worker_2/handoff.md`.

Your working directory is: c:\Users\gamin\OneDrive\Documents\Git\Vibecoded_Yukkuri_Game\.agents\worker_2
