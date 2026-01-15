# Implementation Plan - Proposal 4: Unified AI Architecture

## 1. Research & Analysis

### Goal
Implement a robust, scalable AI architecture that decouples decision-making (Brain) from execution (Body) and supports Level of Detail (LOD) for performance.

### Existing Architecture Analysis
*   **ECS**: Uses `esper`. No native support for System priorities or Tiers.
*   **AI**: Hybrid Utility/Behavior Tree. `BehaviorRegistry` exists but behaviors are hardcoded Python classes.
*   **Navigation**: `NavigationService` supports async HPA*, but `MoveToTarget` action node mixes path logic with steering logic.
*   **Data**: `components.py` has `SteeringComponent` but it is underutilized.

### Technical Solutions & Ranking

#### A. AI Definition (Archetypes)
*   **Option 1: Hardcoded Classes (Current)**: Define `PredatorYukkuri`, `PreyYukkuri` classes.
    *   *Pros*: Full control, type safety.
    *   *Cons*: Rigid, requires code changes to tweak parameters (e.g., bravery).
*   **Option 2: Data-Driven Hybrid (Recommended)**: Use TOML to define "Archetypes" (Goals, Priorities, Personality) which map to reusable Python Logic Blocks.
    *   *Pros*: Fast tuning, flexible, robust.
    *   *Cons*: Need to write a Loader/Validator.
*   **Option 3: Full Visual Scripting**: JSON/XML based tree definition.
    *   *Pros*: No code needed for logic.
    *   *Cons*: Complex parser, hard to debug.

**Rank**: Option 2 (Hybrid) > Option 1 > Option 3.

#### B. Steering & Locomotion
*   **Option 1: Action-Driven (Current)**: `MoveToTarget` calculates velocity directly.
    *   *Pros*: Simple for simple movement.
    *   *Cons*: Duplicates physics logic, hard to blend behaviors (e.g. wander + flee).
*   **Option 2: System-Driven (Recommended)**: `Action` sets `Command` (Target Pos). `SteeringSystem` calculates Forces. `PhysicsSystem` applies Velocity.
    *   *Pros*: Decoupled, supports stacking forces (Seperation + Cohesion).
    *   *Cons*: More components (`SteeringComponent`, `MoveCommand`).

**Rank**: Option 2 > Option 1.

#### C. Perception (Sensing)
*   **Option 1: Per-Agent Query**: Each agent queries `world.get_entities` every frame.
    *   *Pros*: Simple.
    *   *Cons*: O(N^2) complexity. Lags with many agents.
*   **Option 2: Centralized Blackboard (Recommended)**: `PerceptionSystem` runs spatial hash queries once per frame (throttled) and populates individual `Blackboards`.
    *   *Pros*: Optimized, easy to debug (view blackboard).
    *   *Cons*: Global state management.

**Rank**: Option 2 > Option 1.

---

## 2. Implementation Steps

### Phase 1: Core Types & Event Subsystem (Completed)
**Goal:** Establish the data structures and event flow.
1.  **Refactor Components**:
    *   [x] Update `GoalComponent`, `Blackboard`, and `Memories`.
    *   [x] Create `ArchetypeConfig` data class for TOML loading.
2.  **Event Schema**:
    *   [x] Define `AIEvent`, `DamageTakenEvent`, `GoalFailureEvent`, `StateChangeEvent` in `events.py`.
3.  **Global Event Bus**:
    *   [x] Ensure `EventBus` works for system-to-system communication (already verified in `loader.py`).

### Phase 2: The "Driver" (Steering & Physics) (Completed)
**Goal:** Entities move fluidly without AI micro-management.
1.  **Steering System Upgrade**:
    *   [x] Update `SteeringSystem` to handle `Flight` physics (altitude, stamina).
    *   [x] Implement `Arrive`, `Seek`, `Wander`, `Separation` as force providers.
2.  **Navigation Integration**:
    *   [x] Modify `NavigationService` to output paths to `MovementController` / `SteeringComponent`.
    *   [x] Remove direct velocity setting from `MoveToTarget`. It should only set `SteeringComponent.target`.

### Phase 3: The "Senses" (Perception) (Completed)
**Goal:** Agents know what is around them efficiently.
1.  **PerceptionSystem**:
    *   [x] Implement spatial hashing (or use `pymunk` spatial query).
    *   [x] Populate `Blackboard.visible_targets` based on `Vision` component.
2.  **Social Context**:
    *   [x] Implement the "Relation Table" logic (Predator/Prey/Friend/Enemy).

### Phase 4: The "Brain" (Utility & Behavior)
**Goal:** Agents make smart decisions.
1.  **Archetype Loader**:
    *   Implement TOML loader in `entity_factory.py`.
2.  **Refactor Utility AI**:
    *   Update `UtilityScorer` to use `Blackboard` data instead of raw world queries.
3.  **Refactor Behavior Tree**:
    *   Update `MoveToTarget`, `Interact`, etc. to be "Command Issuers" rather than "Executors".

### Phase 5: Verification & Tooling
1.  **Debug Overlay**:
    *   Create `AIDebugSystem` to draw lines to targets, anxiety circles, and paths.
2.  **Stress Test**:
    *   Scenario with 50 Predators vs 50 Prey.

---

## 3. Verification Plan

### Automated Tests
Run via `pytest`.

1.  **Test Archetype Loading**:
    *   Create `data/archetypes/test_archetype.toml`.
    *   `test_entity_factory.py`: Verify entity connects to correct `GoalComponent` priorities.
2.  **Test Perception**:
    *   `test_perception_system.py`: Spawn A and B. Move B into A's range. Assert B in A's `Blackboard`.
3.  **Test Steering**:
    *   `test_steering.py`: Verify `Seek` produces velocity vector towards target.
    *   Verify `Flight` drains `Stamina`.

### Manual Verification
1.  **Visual Debugging**:
    *   Enable Debug Mode (F3).
    *   Observe lines connecting Predators to Prey.
    *   Verify text labels change state (IDLE -> HUNTING -> EATING).
2.  **Performance Check**:
    *   Spawn 100 entities. Check FPS (Target: >30 FPS on Tier 1 machine).

### New Test Cases
*   `tests/unit/game/ai/test_perception.py`: Validates visibility logic.
*   `tests/unit/game/systems/test_steering_system.py`: Validates force calculations.
