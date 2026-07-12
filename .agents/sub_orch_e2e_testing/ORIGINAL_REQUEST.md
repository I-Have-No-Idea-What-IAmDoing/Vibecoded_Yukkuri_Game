# Original User Request

## 2026-06-29T21:56:43Z

You are the E2E Testing Orchestrator. Your mission is to design a comprehensive opaque-box test suite for the biological, social, and environmental simulation systems.
Follow the E2E Testing Track requirements from PROJECT.md.
Your working directory is: c:\Users\gamin\OneDrive\Documents\Git\Vibecoded_Yukkuri_Game\.agents\sub_orch_e2e_testing
You must:
1. Design the test cases following the 4-tier approach for the 8 features.
2. Implement the E2E test cases under tests/ and test runner.
3. Write TEST_INFRA.md and TEST_READY.md when all tests are ready and pass.
4. Use standard subagents (Explorer, Worker, Reviewer, Challenger, Auditor) to verify everything.
5. Report completion by sending a message back to the parent (conversation ID: cbb26b4c-c5c1-44df-a3be-0b1124553a9f).

## 2026-06-29T22:02:45Z

You are the E2E Test Suite Developer. Your task is to implement a comprehensive opaque-box E2E test suite in Python that covers the biological, social, and environmental simulation systems in `tests/integration/test_e2e.py`.
The test suite must test the following 8 features:
1. Need Decay & Metabolism (health, hunger, energy, cleanliness, bladder, social)
2. Waste & Cleanliness (poop spawning, area cleanliness decay, cleanup command)
3. Lifecycle & Growth (aging, Baby -> Child -> Adult transition, scale/collider resizing)
4. Breeding & Reproduction (Adult breeding checks, energy/happiness drop, spiral search baby spawning)
5. Proximity & Relationships (proximity detection, proximity benefits for happiness/stress, parent/child/mate relationship registration)
6. Opinion & Gossip (witnessing events, relationship updates, gossip transmission/priority queues, memories/headlines)
7. Traits & Skills (traits modifying decays/BT choices, athletics/scavenging level-up and XP gain)
8. Time, Environment & Feedback (virtual clock, day/night cycles, cursor light, darkness stress, feedback text/sound)

You must structure the tests using a 4-tier approach as described in the E2E testing guidelines:
- Tier 1: Feature Coverage (>=5 test cases per feature = 40+ total tests)
- Tier 2: Boundary & Corner Cases (>=5 test cases per feature = 40+ total tests)
- Tier 3: Cross-Feature Combinations (>=1 test case per feature pair/combination = 8+ total tests)
- Tier 4: Real-world Application Scenarios (>=5 application-level tests)

Please use `pytest.mark.parametrize` or define individual test functions in `tests/integration/test_e2e.py` to cleanly achieve the 93+ test cases total. Use the `GameDriver` fixture and its fluent API (`yukkuri_builder`, `item_builder`, `expect_entity`, etc.) as much as possible. Make sure all tests are headless-compatible, do not import `pygame.display` or create a visible window, and run quickly.

Ensure you verify that your implemented test suite passes by running `uv run scripts/test.py tests/integration/test_e2e.py` (or similar) and report the exact results in your handoff report.

DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
