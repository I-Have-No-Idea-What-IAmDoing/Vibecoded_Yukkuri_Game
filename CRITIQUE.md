# Critique of Proposal 4: Deterministic Kinematic Hierarchy

## Overview
This document provides a rigorous and harsh systematic critique of the "Deterministic Kinematic Hierarchy" proposal and its current implementation. The proposal aims to replace standard physics simulation with a "Controller" pattern for precise control, but the implementation introduces significant performance bottlenecks, scalability issues, and gameplay limitations.

## 1. Systemic Flaws

### 1.1 The "Kinematic" Trap (Performance & Complexity)
**Critique:** The proposal replaces the highly optimized C-based solver of Pymunk/Chipmunk with a custom Python-based movement solver (`move_and_slide`).
*   **Performance:** The current implementation performs up to **7 physics queries per entity per frame** (3 in `resolve_penetration`, 4 in `move_and_slide`). For 1000 units, this is 7000 spatial queries/frame in Python. This scales linearly O(N) but with a huge constant factor, severely limiting the maximum unit count compared to native physics.
*   **Complexity:** The "Slide" logic attempts to handle multi-plane collisions manually. While the math is theoretically correct, it is brittle in practice (floating point errors, tunneling at high speeds despite "sweeps" if the iteration count is low).
*   **Redundancy:** We are paying the cost of the physics engine (memory, spatial hashing) but fighting its benefits (solver, island sleeping).

### 1.2 The "Totem Pole" Hierarchy (Gameplay & Logic)
**Critique:** The "Rigid Locking" mechanism and the "Root Collider" approximation are fundamentally flawed for complex composite entities.
*   **The "Giant Sphere" Problem:** To ensure a stack of units (e.g., a train) doesn't clip through walls, the Root entity expands its radius to cover the *entire* stack (`max_dist`). A unit with a long tail effectively becomes a massive circle, making it impossible to navigate narrow corridors that visually fit the width of the train but not its length.
*   **Clipping vs. Blocking:** If we *don't* expand the radius, the children (Sensors) will clip through walls. This breaks immersion and allows exploits (hiding vulnerable children inside walls).
*   **Rotation Locking:** The proposal suggests blocking rotation if it causes a collision. This feels terrible in gameplay ("I can't turn because my rear unit is near a wall").

### 1.3 Time Desynchronization (Determinism)
**Critique:** `KinematicMovementSystem` and `PhysicsSystem` both maintain their own `accumulator` loops.
*   **Race Condition:** There is no guarantee these loops run in sync. Depending on float drift and execution order, one system might step twice while the other steps once.
*   **Broken Determinism:** The movement logic depends on `dt` in `update()` but tries to act like a fixed step. If the physics space steps separately, the state is inconsistent.

### 1.4 Visibility Scalability
**Critique:** `VisibilitySystem` implements a naive O(N*M) loop (filtered by batching).
*   **Brute Force:** It iterates over *all* potential targets for *every* observer. Even with batching (20% per frame), this is disastrous for performance as unit count grows.
*   **Missed Optimization:** It fails to use the Pymunk spatial hash (which is already built and paid for) to find local targets.

### 1.5 Dismount Logic (The "Teleport" Hack)
**Critique:** The `process_dismounts` logic is a band-aid for poor spatial management.
*   **Performance Spike:** The "Spiral Search" performs up to 50 geometric queries *per dismounting entity*. If a group of units dies simultaneously (AOE attack), this causes a massive frame spike.
*   **Gameplay Artifacts:** The `_DISMOUNT_TIMEOUT` leads to units popping into existence or teleporting, which breaks tactical consistency.

## 2. Implementation Specifics

*   **`kinematic_movement_system.py`**:
    *   `resolve_penetration`: Calls `shape_query` 3 times iteratively. This is expensive and arguably redundant if the sweep logic is robust.
    *   `move_and_slide`: 4 iterations of `segment_query`.
    *   **Total Queries:** ~7 queries/entity/frame.
*   **`hierarchy_system.py`**:
    *   `process_structure_update`: Re-indexes shapes potentially every frame if `structure_dirty` is not managed carefully.
    *   `find_free_spot`: Uses a naive spiral instead of a smarter heuristic.
*   **`visibility_system.py`**:
    *   Iterates `targets` list entirely. Python loop overhead will dominate.

## 3. Recommendations

1.  **Sync Time:** Centralize the Fixed Update loop. The Physics System should drive the Kinematic System to ensure they step in lockstep.
2.  **Optimize Queries:**
    *   Reduce `resolve_penetration` iterations (or remove it if `move_and_slide` is improved).
    *   Use spatial queries for Visibility (Broadphase `bb_query`).
3.  **Refactor Hierarchy:**
    *   Accept the limitation of "Ghost" followers (visual clipping) OR implement proper chains using constraints (Joints) which leverage the native solver. Given the proposal insists on "Kinematic Controller", we must at least optimize the "Giant Sphere" calculation or switch to a Convex Hull (though Convex Hull rotation is also expensive).
4.  **Fix Dismount:** Optimize the search (e.g., check random open spots or pre-calculated spawn points) rather than a tight spiral loop.
