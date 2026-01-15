# Proposal 4: The Unified AI Architecture (Final)

## 1. Executive Summary

This proposal synthesizes the best elements of previous proposals into a robust, scalable architecture. It combines **Layered ECS**, **Centralized Perception**, and **Primitive Actions**.

**Goal:** Robustness (decoupling), Performance (LOD + Centralized Sensing), and Maintainability (Tooling).

## 2. The Three-Layer Architecture

### Layer 1: Cognitive (Decision)
**Responsibility:** "Determine high-level Intent."
- **System:** `UtilitySystem` (Update Rate: Variable based on LOD).
- **Input:** `NeedsComponent`, `Blackboard`, `Memory`.
- **Output:** `GoalComponent` (e.g., `Goal(HUNT, target_id=P1)`).
- **Hysteresis:** "Stickiness" score prevents rapid goal switching.

### Layer 2: Tactical (Strategy)
**Responsibility:** "Plan execution of the Goal."
- **System:** `BehaviorTreeSystem` (Update Rate: Variable).
- **Structure:**
    - **Strategies**: Top-level sub-trees selected by `GoalComponent`.
    - **Primitives**: Reusable leaf nodes (e.g., `SetMoveTarget`, `InvestigateLocation`).
- **Output:** `CommandComponents` (`MoveCommand`, `InteractCommand`).

### Layer 3: Motor (Execution)
**Responsibility:** "Physically execute commands."
- **System:** `SteeringSystem`, `NavigationSystem`, `InteractionSystem` (Update Rate: Every Frame).
- **Input:** `CommandComponents`.
- **Output:** `Velocity`, `Animation`, `WorldState`.

## 3. Detailed Systems

### 3.1 Perception & Memory (The "Senses")
*   **PerceptionSystem**:
    *   *Throttled*: Updates are time-sliced.
    *   *Filtering*: Uses Tags (Predator/Prey) and Spatial Hashing.
*   **Memory Integration**:
    *   When an entity leaves `Blackboard.visible_entities`, its last known position is cached in `MemoryComponent`.
    *   *Benefit*: Allows "Investigate" behaviors when line-of-sight is broken.

### 3.2 Steering System (The "Driver")
Translates `MoveCommand` into physics forces.
*   **Locomotion Modes**:
    *   *Grounded*: Adheres to terrain, uses friction.
    *   *Flying*: Uses `MoveCommand.altitude`. Ignores ground collision. Scales shadow size.
*   **Force Blending**: `Sum(Seek + Separation + ObstacleAvoidance)`.

### 3.3 LOD System (The "Scaler")
Entities interact with systems based on specific Tiers to save CPU.

| Tier | Distance | Behavior | Physics | Sensing |
|------|----------|----------|---------|---------|
| **0 (Hero)** | < Screen | 10Hz | 60Hz (Full) | 10Hz |
| **1 (Near)** | < 500px | 5Hz | 30Hz (Interp) | 5Hz |
| **2 (Far)** | < 2000px | 1Hz | Frozen | 1Hz |
| **3 (Dormant)** | > 2000px | Paused | Disabled | Disabled |

### 3.4 Debug Tooling
A dedicated `AIDebugSystem` render overlay is required.
*   **Visuals**:
    *   *Goal Text*: Floating text above head (e.g., "HUNTING P:0.8").
    *   *Vectors*: Cyan line for `SteeringForce`, Red line for `Velocity`.
    *   *Perception*: Wireframe circle showing sensory range.
    *   *Path*: Dotted line showing current path nodes.

## 4. Key Components

```python
@dataclass
class Blackboard:
    visible_targets: Dict[EntityID, TargetInfo]
    # Memory allows smart persistence
    short_term_memory: Dict[EntityID, LastKnownPosition]

@dataclass
class GoalComponent:
    goal_type: GoalType
    priority: float
    target_id: Optional[EntityID]
    stickiness: float

@dataclass
class MoveCommand:
    target_pos: Vec2d
    speed: float
    altitude: float  # Supported by FlyingLocomotion
    status: CommandStatus
```

## 5. Migration Strategy

1.  **Foundation**: Config, Components, and the `AIDebugSystem` (crucial for validating the rest).
2.  **Motor**: Implement `SteeringSystem` & `Locomotion`. Verify with `MoveToTargetV1` proxy.
3.  **Sensing**: Implement `PerceptionSystem` with LOD throttling hooks.
4.  **Brain**: Refactor `UtilitySelector` & `BehaviorTrees` to use new structure.
