# Proposal 4: The Unified AI Architecture (Final)

## 1. Executive Summary

This proposal synthesizes the best elements of previous proposals into a robust, scalable architecture. It combines **Layered ECS**, **Centralized Perception**, and **Primitive Actions** with advanced **Social Dynamics** and **Physics-based Flight**.

**Goal:** Robustness (decoupling), Performance (LOD + Centralized Sensing), and Maintainability (Tooling).

## 2. The Three-Layer Architecture

### 2.1 Data Flow Pipeline
The architecture follows a strict unidirectional data flow:
`Sensors -> Blackboard -> Utility (Goal) -> Behavior (Command) -> Motor (Physics)`

1.  **Sensors**: Write to `Blackboard` (Visible entities, Threats).
2.  **UtilitySystem**: Reads `Blackboard` + `Needs`. Writes `GoalComponent`.
3.  **BehaviorTreeSystem**: Reads `GoalComponent`. Selects Tree. Writes `CommandComponents`.
4.  **Motor Systems**: Read `CommandComponents`. Write `Velocity`/`WorldState`.
5.  **Event System**: `EventBus` handles interrupts and state changes.

### Layer 1: Cognitive (Decision)
**Responsibility:** "Determine high-level Intent based on Self and Society."
- **System:** `UtilitySystem` (Update Rate: Variable based on LOD).
- **Input:**
    - `NeedsComponent` (Hunger [0-100], Stress [0-100], Energy [0-100]).
    - `PersonalityComponent` (Traits: Arrogance, Kindness).
    - `SocialContext` (Friends, Enemies, Affinity).
    - `Blackboard` (Perceived Threats/Resources).
    - `Memory` (Last known locations).
- **Output:** `GoalComponent` (e.g., `Goal(HUNT, target_id=P1)`, `Goal(SOCIALIZE, target_id=F2)`).
- **Hysteresis:** "Stickiness" score prevents rapid goal switching.
    - *Formula*: `Score = RawScore + (StickinessBonus if CurrentGoal == NewGoal else 0)`.

### Layer 2: Tactical (Strategy)
**Responsibility:** "Plan execution of the Goal."
- **System:** `BehaviorTreeSystem`.
- **Structure:**
    - **Strategies**: Top-level sub-trees selected by `GoalComponent`.
        - *Example*: `Goal.HUNT` -> Selects `PredatorHuntTree`.
    - **Primitives**: Reusable leaf nodes.
        - `ChannelAction(EAT)`: Handles start/update/fail logic for timed actions.
        - `SteerToPosition`: Updates `MoveCommand`.
- **Output:** `CommandComponents` (`MoveCommand`, `InteractCommand`).

### Layer 3: Motor (Execution)
**Responsibility:** "Physically execute commands."
- **System:** `SteeringSystem`, `NavigationSystem`, `InteractionSystem`.
- **Input:** `CommandComponents`.
- **Output:** `Velocity`, `AnimationState`, `WorldState`, `Stamina`.
- **Safety:** `StuckMonitorSystem` detects physics hang-ups.

## 3. Detailed Systems

### 3.1 Event-Driven Architecture (Using Existing Engine)
We leverage the existing `yukkuri_game.engine` Event implementations (`EventBus`, `EventManager`).
*   **Purpose**: Decouple systems and handle interrupts immediately (no polling).
*   **Key Events**:
    *   `DamageTakenEvent`: Triggers `ChannelAction` interrupt.
    *   `GoalFailureEvent`: Triggers re-planning in `Utility.py`.
    *   `StateChangeEvent`: Updates UI/Debug immediately.
*   **Workflow**:
    1.  `DamageSystem` detects hit -> `EventBus.publish(DamageTakenEvent(id=1, amount=10))`.
    2.  `InteractionSystem` listener checks ID -> Cancels current `ChannelComponent`.
    3.  `BehaviorTreeSystem` listener -> Forces "Flee" behavior override.

### 3.2 Failure Cascades & Safety
Defined behaviors for when actions fail, ensuring entities never get "stuck".
1.  **Stuck Monitor**:
    *   Checks: `Velocity > 0` AND `Displacement < Threshold` over 1.0s.
    *   Actions: 1. `Jump` (Unwedge) -> 2. `Repath` (Exclusion Zone) -> 3. `Teleport` (Safe Node).
2.  **MoveToTarget Fail** (PathBlocked):
    *   *Retry (1x)*: Re-request path.
    *   *Fallback*: `Wander(radius=50)` (Unstick).
    *   *Final*: `Blackboard.mark_unreachable(target_id)`. Drop Goal.
2.  **Interact Fail** (Target moved):
    *   *Retry*: `SteerToPosition` (Update target pos).
    *   *Final*: Drop Goal.

### 3.3 Data-Driven Archetypes
Move hardcoded AI logic to TOML configuration.
*   **Config Structure**:
    ```toml
    [archetype.predator]
    priorities = ["HUNT", "SLEEP", "PATROL"]
    prey_tags = ["prey", "weak"]
    stamina_regen = 15.0
    personality_bias = { arrogance = 0.8, kindness = -0.5 }

    [archetype.prey]
    priorities = ["FLEE", "FORAGE", "SOCIALIZE"]
    predator_tags = ["predator"]
    stamina_regen = 10.0
    personality_bias = { arrogance = -0.2, kindness = 0.5 }
    ```
    ```
*   **Benefit**: Easy creation of "Scavengers", "Queens", "Babies" without code changes.

### 3.4 Configuration Validation
To prevent crashes from typos or bad math in TOML:
*   **Schema Validator**: Run on startup.
    *   *Checks*:
        *   `Range Check`: `hunger_decay` must be positive. `prob` must be 0-1.
        *   `Enum Check`: `priorities` must match `GoalType` enum.
        *   `Required Fields`: Error if `stamina_regen` missing.
*   **Safe Loader**:
    *   If a value is invalid, log **Error** but use **Hardcoded Default**.
    *   *Example*: `stamina_regen = -5` (Invalid) -> Log Warning -> Set to `10.0` (Default).

### 3.4 Perception & Social Awareness
*   **PerceptionSystem**:
    *   *Throttled*: Updates are time-sliced.
    *   *Filtering*: Uses Tags and Spatial Hashing.
    *   *Vision Bonuses*: Flying entities gain increased view radius (+50%).
*   **Social Context Resolution Table**:
    | Subject Type | Target Type | Relation Data | Result |
    |--------------|-------------|---------------|--------|
    | Predator     | Prey        | Any           | **Enemy** (Prey) |
    | Prey         | Predator    | Any           | **Enemy** (Threat) |
    | Any          | Any         | Affinity > 50 | **Friend** |
    | Any          | Any         | Affinity < -10| **Enemy** |
    | Any          | Any         | FamilyID Match| **Friend** |
    | **Default**  |             |               | **Neutral** |

    *   **Personality Integration**:
        *   Traits modify utility scores. Example: High `Arrogance` increases score for `DemandFood` and decreases `BegForFood`.
*   **Memory Integration**:
    *   When an entity leaves `Blackboard.visible_entities`, its last known position is cached in `MemoryComponent`.

### 3.5 Flight & Steering (The "Driver")
Translates `MoveCommand` into physics forces.
*   **Global Navigation**: A* requests for long-distance paths (> 500px).
    *   **AsyncPathfindingManager**:
        *   **Budget**: Max 5 path requests per frame. Priority Queue (Tier 0 > 1 > 2).
        *   **Fallback**: High load -> Use `Steering Seek` immediately, calculate A* later.
*   **Local Steering**: Force blending (`Seek + Separation + ObstacleAvoidance`) for immediate movement.
    *   *Separation*: `Force = Sum(Normalize(SelfPos - NeighborPos) / Distance^2)`
*   **Flight Mechanics**:
    *   **States**:
        1.  `Grounded`: Altitude = 0. Can transition to `Takeoff`.
        2.  `Takeoff`: Vertical velocity +Y. Transitions to `Flying` at MinAltitude.
        3.  `Flying`: Altitude > MinAltitude. Drains Stamina (`5/sec`).
        4.  `Landing`: Vertical velocity -Y. Transitions to `Grounded` at Altitude 0.
    *   **Stamina System** (Generalized):
        *   Used for **Flight**, **Sprinting**, and **Fleeing**.
        *   `MaxStamina`: 100.
        *   `Recovery`: +10/sec when Idle/Walking.
        *   `Drain`: -5/sec (Flying), -8/sec (Sprinting/Fleeing), -10/sec (Swooping).
        *   *Failure*: If Stamina <= 0 while Flying -> Force `Landing`. If running -> Force `Walk`. Apply `Fatigue` (No exertion for 5s).

### 3.6 Interaction Mechanics
*   **Channeling State Machine**:
    *   **Start**: `InteractCommand` received. Check range/conditions.
    *   **Channel**: Timer starts. `Defense` = 0.
        *   *Interruption*: If `DamageTakenEvent` received, state -> `Fail`.
    *   **Complete**: Timer finishes. Effect applied (e.g., `Hunger - 20`).
    *   **Fail**: Reset timer. Apply cooldown.
*   **Eating**:
    *   Channeling for 2-3s.
    *   On completion: Restoration applied, Target marked `Dead` or `Digesting`.

### 3.7 LOD System (The "Scaler")
Entities interact with systems based on specific Tiers to save CPU.

| Tier | Distance | Behavior | Physics | Sensing |
|------|----------|----------|---------|---------|
| **0 (Hero)** | < Screen | 10Hz    | Exact Collision | Full Raycast |
| **1 (Near)** | < 500px  | 5Hz     | Simple Box      | Cone Check |
| **2 (Far)** | < 2000px | 1Hz     | Frozen          | Distance Only |
| **2 (Far)** | < 2000px | 1Hz     | Frozen          | Distance Only |
| **3 (Dormant)**| > 2000px | Paused  | Disabled        | Disabled |

*   **Wakeup Mechanism**:
    *   Since Tier 3 has "Sensing: Disabled", a global `ProximityManager` (Spatial Hash) runs at 1Hz to check distance from Player to *all* entities.
    *   If `Distance < 2000px`, force transition Tier 3 -> Tier 2.

### 3.8 Debug Tooling
A dedicated `AIDebugSystem` render overlay is required.
*   **Visuals**:
    *   *Goal Text*: Floating text (e.g., "HUNTING P:0.8").
    *   *Social*: Lines to friends (Green) and enemies (Red).
    *   *Steering*: Vectors for Velocity (Cyan) and Force (Magenta).
    *   *Senses*: Wireframe circle (Radius scales with Altitude).

### 3.9 System Watchdogs
*   **StateValidationSystem**:
    *   Runs at low frequency (1Hz). Enforces invariants.
    *   *Examples*:
        *   `if Altitude <= 0` and `State == Flying` -> Force `State = Grounded`.
        *   `if Channeling.time > limit` -> Force `Interrupt`.
        *   `if Hunger < 0` -> Clamp to 0.


## 4. Key Components

```python
@dataclass
class Blackboard:
    visible_targets: Dict[EntityID, TargetInfo]
    # Memory for persistence
    short_term_memory: Dict[EntityID, LastKnownPosition]

@dataclass
class GoalComponent:
    goal_type: GoalType
    priority: float
    target_id: Optional[EntityID]
    stickiness: float = 10.0  # Bonus added if staying on same goal

@dataclass
class MoveCommand:
    target_pos: Vec2d
    speed: float
    altitude: float  # Supported by FlyingLocomotion
    # Navigation integration
    path: Optional[List[Vec2d]] = None
    expiration: float = 0.0  # Timestamp when command expires


@dataclass
class StaminaComponent:
    current: float = 100.0
    max_value: float = 100.0
    regen_rate: float = 10.0
    drain_rate_flight: float = 5.0
    drain_rate_run: float = 8.0
    is_fatigued: bool = False

@dataclass
class PersonalityComponent:
    arrogance: float = 0.0  # -1.0 to 1.0
    kindness: float = 0.0
    bravery: float = 0.0


@dataclass
class ChannelComponent:
    is_channeling: bool
    current_time: float
    total_time: float
    action_type: ActionType
```

## 5. Migration Strategy

1.  **Foundation**: Config (TOML Archetypes), Components, and Debug System.
2.  **Events**: Define `AIEvent` subclasses in `events.py`.
3.  **Motor**: `SteeringSystem` with Flight/Stamina logic. Verify `MoveTo` works.
4.  **Sensing**: `PerceptionSystem` + `SocialContext` resolver.
5.  **Brain**: Refactor `Utility` with new Inputs. Build `Strategies`.
