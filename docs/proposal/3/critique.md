# Critique of Implementation Plan for Proposal 3

This document provides a critical analysis of the implementation plan for the kinematic movement system. While the plan correctly identifies the major phases of work, it suffers from several critical flaws in its details, verification strategy, and overall robustness.

## 1. Flawed System Logic

-   **Responsibility for Stopping:** The plan incorrectly assigns the responsibility of stopping the entity to the `MovementSystem` by having it reset `target_velocity` to zero every frame. This is a significant design flaw that creates a race condition with the AI systems. The correct approach, consistent with the design's philosophy of direct AI control, is to make the AI responsible for setting velocity to zero when it wants the entity to stop.
-   **Incorrect Visual Timer Calculation:** The plan specifies that `visual_bob_timer` should be incremented by a constant `dt` when moving. This contradicts the design document, which correctly states that the timer should be scaled by the entity's velocity (`dt * physics_body.velocity.length()`). The plan's version would result in a static-speed bounce that looks unnatural and disconnected from the entity's actual speed.

## 2. Inadequate Verification and Testing

-   **Lack of Automated Tests:** The plan completely relies on manual "playtesting" for verification. This is unacceptable for a core system like movement. There is no mention of writing unit tests for the AI's velocity calculations or integration tests for the `MovementSystem`. Without automated tests, we cannot prevent regressions or efficiently verify the correctness of individual components.
-   **Trivial Verification Steps:** The verification steps listed are superficial (e.g., "The component can be added to an entity"). They do not test the actual functionality or the intended outcomes of the implementation steps.

## 3. Poor Task Breakdown and Sequencing

-   **Monolithic Cleanup Step:** The "Remove All Deprecated Code" step is a massive, high-risk task that is vaguely defined. Deleting a large number of core components and systems at once is a recipe for a broken build and difficult debugging. Cleanup should be done incrementally as old systems are successfully replaced.
-   **Tuning as an Afterthought:** The plan treats tuning the visual parameters as a final step. However, the mechanism for tuning is not considered. Hardcoding values like `bob_height` and `bob_speed` is inflexible. The plan should include a task to externalize these parameters into a configuration file or data asset to allow for easy iteration by designers or developers.

## 4. Conclusion

In its current state, the implementation plan is a high-level sketch that, if followed, would likely lead to a buggy, untestable, and difficult-to-maintain system. It introduces logical flaws not present in the original design document and fails to incorporate modern development best practices like automated testing and incremental refactoring. It requires a significant revision to be considered a viable path to implementation.
