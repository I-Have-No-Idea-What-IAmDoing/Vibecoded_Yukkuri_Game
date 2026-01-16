# Unified AI Architecture

The Yukkuri Game uses a **Unified AI Architecture** that decouples decision-making (Brain), perception (Senses), and movement (Motor). This modular approach supports complex, data-driven behaviors while maintaining high performance.

## Architecture Layers

### 1. Perception Layer ("The Senses")
*   **System**: `PerceptionSystem`
*   **Data**: `Blackboard`
*   **Function**:
    *   Scans the environment using spatial hashing (via `VisibilitySystem`).
    *   Populates the **Blackboard** with visible targets (`TargetInfo`).
    *   Resolves **Social Context** (Friendly, Hostile, Neutral) based on:
        *   **Species interactions**: Predator vs Prey tags.
        *   **Family ties**: Parents/Children are friendly.
        *   **Individual relationships**: Affinity scores in `RelationshipRegistry`.
    *   Maintains **Short-Term Memory** of entities that leave the field of view.

### 2. Cognitive Layer ("The Brain")
*   **System**: `BehaviorSystem`, `UtilitySelector`
*   **Data**: `ArchetypeConfig`, `actions.toml`, `yukkuri.toml` (Archetypes)
*   **Function**:
    *   **Archetypes**: Defines personality bias, goals, and fears via TOML configuration (`data/archetypes/*.toml`).
    *   **Utility AI**: `UtilitySelector` reads the `Blackboard` and entity stats (Hunger, Stress) to score potential actions.
    *   **Behavior Tree**: Executes the chosen action (e.g., `MoveToTarget`, `Interact`) as a sequence of leaf nodes.

### 2a. Predator & Prey Dynamics
*   **Predator Component**: Defines `prey_tags` (what it eats) and `hunger_threshold`.
*   **Hunting Loop**:
    1.  **FindPrey**: Scans `Blackboard` for entities with matching tags.
    2.  **Chase**: Issues `MoveCommand` to interception point.
    3.  **Attack/Eat**: Damages prey upon contact (`dps`); consumes it to restore hunger.
*   **Prey Response**:
    *   **Fear**: Sees entities with `Predator` component or `predator_tags` as Threats.
    *   **Flee**: `UtilitySelector` prioritizes `FLEE` goal when threats are near.

### 2b. Flight AI
*   **Flight Component**: Manages `altitude`, `stamina`, and `FlightState`.
*   **Navigation**:
    *   **Takeoff**: Ascends to `max_altitude` before traveling.
    *   **Cruising**: Moves at `max_altitude` to ignore ground obstacles (mostly).
    *   **Landing**: Descends when reaching destination or `stamina` is critical.
    *   **Swooping**: Attacks drop altitude temporarily.

### 3. Motor Layer ("The Driver")
*   **System**: `SteeringSystem`
*   **Data**: `MoveCommand`, `SteeringComponent`
*   **Function**:
    *   **Decoupled Movement**: Cognitive layer issues high-level **MoveCommands** (e.g., "Go to (100, 200) with priority 2").
    *   **Force-Based Steering**: Calculates physics forces for:
        *   **Seek/Arrival**: Moving towards target.
        *   **Separation**: Avoiding crowding with neighbors.
        *   **Obstacle Avoidance**: Steering around static geometry.
    *   **Physics Integration**: Applies final velocity to `PhysicsBody`.

---

## Key Components

| Component | Description |
| :--- | :--- |
| `GoalComponent` | Stores the current high-level goal (e.g., EAT, SLEEP) and queue. |
| `Blackboard` | Per-agent storage for perception results (visible targets, memory). |
| `MoveCommand` | Transient component representing a movement request. Consumed by `SteeringSystem`. |
| `ArchetypeConfig` | Static configuration loaded from TOML, defining personality and tags. |

---

## Configuration

### 1. Actions (`data/ai/actions.toml`)
Defines the available actions and their utility scoring curves.
```toml
[actions.Eat]
weight = 2.0
[[actions.Eat.considerations]]
input = "hunger"
curve = "linear"
```

### 2. Archetypes (`data/archetypes/*.toml`)
Defines personality profiles for different Yukkuri types.
```toml
archetype_id = "predator"
[priorities]
list = ["HUNT", "EAT", "SLEEP"]
[prey_tags]
tags = ["Food", "PreyType"]
```

## Adding New Behaviors

### 1. Define the Action (`data/ai/actions.toml`)
Add your new action entry here. This defines how the Utility AI scores it.

```toml
[actions.Dance]
weight = 1.5
endpoint = "Dance"  # Matches the Action class name or registered ID
cooldown = 10.0

[[actions.Dance.considerations]]
input = "happiness"
curve = "logistic"  # Happy yukkuris dance!
slope = 1.0
exponent = 1.0
```

### 2. Implement Logic (`game/ai/behavior.py`)
Create a class that inherits from `Action` (or `BaseAction`).

```python
class Dance(Action):
    def on_enter(self, entity: EntityID, blackboard: Blackboard) -> None:
        # Start animation, set state
        self.animator.play(entity, "dance")
        
    def update(self, entity: EntityID, dt: float, blackboard: Blackboard) -> Status:
        # Return RUNNING while active, SUCCESS when done
        if self.timer > 5.0:
            return Status.SUCCESS
        return Status.RUNNING
```

### 3. Register the Action
Ensure your action class is registered in the factory or `BehaviorRegistry` so the system can instantiate it by name.

### 4. Update Archetypes (`data/archetypes/*.toml`)
If this action should only be available to certain types (e.g., "Flying"), add it to their allowed actions list if your system restricts actions by archetype.

---

## AI Debugging

The **AI Debug Renderer** visualizes the internal state of the AI for debugging purposes.

### Enabling It
Toggle the debug renderer (typically bound to `F3` or a specific debug key in `InputSystem`).

### Visual Legend
| Visual | Color | Meaning |
| :--- | :--- | :--- |
| **Line to Entity** | **Yellow** | The AI's current `target_id`. |
| **Line/Path** | **Cyan** | The current movement path or `MoveCommand` destination. |
| **Line to Friend** | **Green** | Friendly social relationship detected. |
| **Line to Enemy** | **Red** | Hostile/Prey/Threat relationship detected. |
| **Line to Neutral** | **Gray** | Neutral entity in perception range. |
