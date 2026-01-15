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
1.  **Define Action**: Add entry to `actions.toml`.
2.  **Define Logic**: Create Action class in `behavior.py`.
3.  **Register**: Add to `BehaviorRegistry`.
4.  **Movement**: Ensure implementation uses `MoveCommand` for movement, not direct velocity control.
