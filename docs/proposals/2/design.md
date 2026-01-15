# Proposal 2: Robust AI Architecture

## 1. The Problem

The current AI system suffers from several critical issues that lead to "weird behaviors" and fragility:

*   **Monolithic Actions**: Classes like `MoveToTarget` are "God Classes" that handle high-level logic (choosing a target), mid-level logic (pathfinding requests), and low-level logic (physics velocity, steering). This makes them incredibly hard to debug and test.
*   **Mixed Paradigms**: The integration between the Utility Selector and the Behavior Tree is implicit and leaky. The Utility Selector modifies `AIState` directly, while behavior nodes often have their own internal state that can get out of sync.
*   **Hidden State**: Crucial state variables (like `path_requesting`, `path_failed`, `drift_threshold`) are buried in unstructured `state_data` dictionaries or private class attributes, making the system opaque and unpredictable.
*   **Performance Bottlenecks**: The system rebuilds the entire decision context every frame in Python, which scales poorly as entity count increases.
*   **Fragile Navigation**: Pathfinding, steering, and movement are tightly coupled. If one fails (e.g., a momentary pathfinding timeout), the entire behavior often breaks or stalls.

## 2. Proposed Architecture

We propose a **Three-Layered Architecture** to separate concerns and increase robustness.

### Layer 1: The Cognitive Layer (Decision Making)
**Responsibility**: "What do I want to do?"
**Mechanism**: Utility AI (Existing but refined) or GOAP.
**Output**: A High-Level **Goal** or **Intent** (e.g., `Goal: SatisfyHunger`, `Intent: FleeThreat`).

*   **Improvements**:
    *   **Context Caching**: Do not rebuild the full context every frame. usage reactive updates or dirty flags.
    *   **Decoupled Logic**: The Cognitive layer does *not* know how to execute the goal. It simply sets the Goal in a component.

### Layer 2: The Tactical Layer (Strategy)
**Responsibility**: "How do I achieve this goal?"
**Mechanism**: Behavior Trees (BT).
**Input**: The **Goal** from the Cognitive Layer.
**Output**: A sequence of atomic **Commands** or **Task Components**.

*   **Structure**:
    *   A root selector switches based on the current active Goal.
    *   Sub-trees implement the specific strategies (e.g., `EatStrategy`: `FindFood` -> `MoveToTarget` -> `Interact`).
    *   **Stateless Nodes**: Behavior nodes should be as stateless as possible. They should read the ECS state and output Commands. They should *not* hold private persistent state like "time since last path request" inside the node instance if possible; this should live in a component.

### Layer 3: The Motor Layer (Execution)
**Responsibility**: "Actuate the physical entity."
**Mechanism**: Pure ECS Systems.
**Input**: **Command Components** (e.g., `MoveCommand`, `InteractCommand`).
**Output**: Physics updates, Animation state changes.

*   **Key Systems**:
    *   **SteeringSystem**: Reads `MoveCommand` (target position). Handles path following, obstacle avoidance, and velocity setting. It essentially replaces the internal loop of `MoveToTarget`.
    *   **NavigationSystem**: Listens for `MoveCommand` changes. If the target is far/blocked, it asynchronously requests a path and updates the `Path` component.
    *   **InteractionSystem**: Process `InteractCommand`.

## 3. Data Flow Example: "Eating"

1.  **Cognitive**:
    *   `UtilitySystem` sees `Hunger` is high.
    *   Sets `GoalComponent(type=EAT)`.

2.  **Tactical (Behavior Tree)**:
    *   `EatSubtree` activates.
    *   `FindFood` node runs. Finds an apple entity. Sets `TargetComponent(target_id=Apple)`.
    *   `MoveToTarget` node runs. Checks distance. If too far -> Adds `MoveCommand(target=ApplePos)`.

3.  **Motor**:
    *   `NavigationSystem` sees `MoveCommand`. Requests path to Apple.
    *   `SteeringSystem` sees `Path` component. Calculates velocity to next waypoint. Applies force to `PhysicsBody`.
    *   Entity moves.

4.  **Completion**:
    *   Entity arrives. `SteeringSystem` removes `MoveCommand` or sets specific generic "AtDestination" flag.
    *   `MoveToTarget` node sees "AtDestination". Returns `SUCCESS`.
    *   `Interact` node runs. Adds `InteractCommand(target=Apple)`.

## 4. Key Benefits

*   **Robustness**: If navigation fails, the `SteeringSystem` can handle it (e.g., stop) without crashing the AI logic. The AI simply sees the command didn't complete and can choose a different strategy (e.g., "Wander").
*   **Testability**: We can unit test the `SteeringSystem` in isolation from the AI. We can test the AI logic without a physics world.
*   **Performant**: The Motor layer can run every tick, while the Cognitive layer can run at a lower frequency (e.g., 5Hz).
*   **Debuggable**: Inspecting an entity shows exactly what it wants (`Goal`), what it's trying to do (`Command`), and its physical state (`Velocity`).

## 5. Migration Strategy

1.  **Create Systems**: Implement `SteeringSystem` and `NavigationSystem` (refactoring `MoveToTarget` logic into these).
2.  **Refactor Actions**: Rewrite `MoveToTarget` behavior node to be a thin wrapper that just sets the `MoveCommand`.
3.  **Update Utility**: Ensure `UtilitySelector` sets the new `GoalComponent` instead of directly manipulating `AIState.current_action` string (or map the string to the component).
