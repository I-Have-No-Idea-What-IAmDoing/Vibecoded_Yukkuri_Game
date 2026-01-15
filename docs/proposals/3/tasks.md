# Tasks: Modular AI 2.0 Implementation

This document outlines the actionable steps required to implement the redesigned AI system.

## Phase 1: Infrastructure & Services
- [ ] Create `PerceptionSystem` to handle partitioned sensing workloads.
- [ ] Implement `Blackboard` component for structured data sharing between sensors and BT nodes.
- [ ] Refactor `NavigationService` to support stateful `MoveRequests` with status callbacks (PENDING, MOVING, REACHED, FAILED).
- [ ] Introduce basic Steering Behaviors (Seek, Flee, Arrival) into the `PhysicsSystem` or a new `SteeringSystem`.

## Phase 2: Action Refactor
- [ ] Create `BaseAction` with explicit `on_start`, `on_update`, and `on_stop` lifecycles.
- [ ] Rewrite `MoveToTarget` to be a thin wrapper around the `NavigationService`.
- [ ] Implement `Sensor` modules for Hunger, Social, and Threat detection.

## Phase 3: Behavior Tree Overhaul
- [ ] Implement `UtilitySelector` node that can be placed as a composite or decorator.
- [ ] Refactor `BehaviorRegistry` to support the new modular tree building pattern.
- [ ] Build the "Modular AI 2.0" root tree with Emergency and Decision branches.

## Phase 4: Migration & Optimization
- [ ] Migrate `actions.toml` definitions to use the new Utility Scorer nodes.
- [ ] Implement "Throttled Thinking" where agents only update their high-level utility every N frames (spread across agents).
- [ ] Add debug visualizations for AI Blackboard state and Steering paths.

## Phase 5: Verification
- [ ] Create integration tests for "Interruption Recovery" (e.g., predator interrupts eating).
- [ ] Benchmark AI performance with 100+ agents vs. current implementation.
- [ ] Verify social interaction stability (no more target "fighting" or overlapping).
