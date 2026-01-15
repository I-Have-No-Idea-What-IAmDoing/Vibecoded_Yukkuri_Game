# Robustness Review: Proposal 4

To achieve "bulletproof" reliability, we need to handle worst-case scenarios and engine constraints.

## 1. Stuck Agent Monitor (The "Watchdog")
*   **Problem**: `MoveToTarget` failure cascades handle *pathfinding* errors, but not *physics* hang-ups (e.g., getting wedged between two rocks where pathfinding says "it's clear" but collision says "no").
*   **Solution**: `StuckMonitorSystem`.
    *   Tracks `Position` history over 1-2 seconds.
    *   If `Velocity > 0` AND `Displacement < Threshold`:
        1.  Trigger `Jump/Unwedge` force (small vertical hop).
        2.  If still stuck: Force `Repath` with `exclusion_zone` around current spot.
        3.  If still stuck: Teleport to nearest valid node (Last Resort).

## 2. Resource Budgeting (The "Traffic Control")
*   **Problem**: If 100 Yukkuris all get scared at once, 100 A* requests spike the CPU.
*   **Solution**: `AsyncPathfindingManager` with a **Budget**.
    *   Limit: Max 5 high-cost paths per frame.
    *   Queue: Priority Queue (Tier 0 > Tier 1 > Tier 2).
    *   Fallback: If queue full, use `Steering Seek` (dumber but instant) temporarily.

## 3. State Sanitization
*   **Problem**: Logic bugs can leave components in invalid states (e.g., `Flying` state but `Altitude = 0`, or `Channeling` forever because the completion event fired before the listener was ready).
*   **Solution**: `StateValidationSystem` (Runs every 60 frames / 1sec).
    *   Checks invariants:
        *   `if Altitude <= 0.1` -> Force `State = Grounded`.
        *   `if Channeling.time > Channeling.total + 1.0s` -> Force `Interrupt`.
        *   `if Hunger < 0` -> Clamp to 0.

## 4. Blackboard Expiration
*   **Problem**: A threat is detected, but the sensor stops seeing it (maybe it teleported). The Blackboard might retain "stale" ghost data.
*   **Solution**: All Blackboard entries must have a `timestamp`.
    *   `Blackboard.clean(stale_threshold=5.0s)` runs periodically to remove old memories.

## 5. Defensive Coding in Utility
*   **Problem**: `UtilityScorer` divides by zero or returns NaN.
*   **Solution**: Wrap all scoring in `safe_score()`:
    *   `try { score = calc() } catch { return 0.0 }`
    *   Clamp all output 0.0 to 1.0.
