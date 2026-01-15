# Implementation Plan: Unified AI Architecture (Final)

## Phase 1: Foundation & Tooling
- [ ] **Data & Config**
    - [ ] Create `ai_config.toml`.
    - [ ] Define `GoalComponent`, `Blackboard`, `MoveCommand`, `MemoryComponent`.
- [ ] **Debug System** (High Priority)
    - [ ] Create `AIDebugSystem`.
    - [ ] Implement `render_goal_text`, `render_steering_vectors`, `render_perception_gizmos`.
    - [ ] Add `toggle_debug_overlay` keybind.

## Phase 2: The Motor Layer
- [ ] **Steering System**
    - [ ] Implement `SteeringSystem` with Force Blending.
    - [ ] Implement `FlyingLocomotion` (Altitude, pure 3D distance check).
    - [ ] Implement `GroundedLocomotion`.

## Phase 3: Perception, Memory & LOD
- [ ] **Perception**
    - [ ] Implement `PerceptionSystem` with Spatial Hashing.
    - [ ] Implement `Memory` logic: Cache last known pos on visibility loss.
- [ ] **LOD Manager**
    - [ ] Create `LODSystem` that assigns Tiers based on distance to Camera.
    - [ ] Update Systems to respect `LODTier` (skip updates for distant entities).

## Phase 4: Strategy & Decision
- [ ] **Primitives**
    - [ ] `InvestigateLocation` (Go to Memory pos).
    - [ ] `SetMoveCommand` (Standard move).
- [ ] **Strategies**
    - [ ] `HuntStrategy`: Swoop -> Attack -> Eat.
    - [ ] `SearchStrategy`: Wander -> Investigate Memory.
- [ ] **Utility**
    - [ ] Implement `UtilitySystem` with Hysteresis (Stickiness).

## Phase 5: Cleanup
- [ ] Remove legacy `behavior.py` classes.
- [ ] Run Performance Benchmark (100 vs 500 entities).
