# Improve Pathfinding Robustness

## Goal
Fix issues where entities get stuck on grid edges due to the mismatch between continuous physics and coarse pathfinding grid.

## Steps

1.  **Tune Grid Step (Short-term)**
    -   **File**: `src/yukkuri_game/game/ai/navigation_service.py` (or wherever `find_path` uses the grid).
    -   Locate the grid discretization step (currently likely 50 or implied by map size).
    -   Reduce the step size (e.g., to 25 or 32).
    -   *Note*: This increases the grid size. Ensure performance remains acceptable.

2.  **Implement Raycast/Local Avoidance (Long-term/Robust)**
    -   **File**: `src/yukkuri_game/game/ai/behavior.py` (`MoveToTarget`).
    -   Algorithm:
        -   Before moving directly to the next waypoint, cast a ray (using `pymunk` segment query).
        -   If ray hits an obstacle, use the pathfinding waypoint.
        -   If ray is clear to a further waypoint (string pulling), skip intermediate nodes to smooth path.
        -   **Stuck Check**: Improve `stuck_timer` logic. If stuck, try a small random offset *before* full repath.

3.  **Verification**
    -   **Test**: Create a "maze" or tight corridor scenario in a test.
    -   Spawn Yukkuri. Set target across the maze.
    -   Verify Yukkuri reaches target without getting stuck endlessly.

## Pre-commit
-   Ensure proper testing, verification, review, and reflection are done.
