## 2026-06-29T22:41:59Z
You are the Worker subagent for Milestone 1: Need Decay, Metabolism, and Waste Simulation.
Your task is to run the integration test suite and check if there are any compilation errors or failures:

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT
hardcode test results, create dummy/facade implementations, or
circumvent the intended task. A Forensic Auditor will independently
verify your work. Integrity violations WILL be detected and your
work WILL be rejected.

Please execute these steps precisely:
1. Run the cargo test command to check if tests compile and pass:
   `cargo test --test simulation_tests`
2. If there are any compilation errors (e.g. in tests/simulation_tests.rs), fix them. Pay attention to Bevy 0.19 message/event API rules (e.g. using `MessageWriter`, `MessageReader`, `writer.write(...)`, `reader.read()`, etc.).
3. Once all tests compile and pass, verify that all other cargo tests also pass by running `cargo test`.
4. Document the test results and write your handoff report to `.agents/worker_3/handoff.md` and reply with a summary.
Your working directory is: c:\Users\gamin\OneDrive\Documents\Git\Vibecoded_Yukkuri_Game\.agents\worker_3
