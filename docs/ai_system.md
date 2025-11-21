# Utility-Based AI System

The Yukkuri Game now uses a Utility-Based AI system to determine entity behaviors. This system replaces static decision logic with a dynamic, data-driven approach where actions are scored based on current world state and entity statistics.

## Overview

The core of the system involves:
1.  **Actions**: High-level goals an entity can pursue (e.g., Eat, Sleep, Play, Wander).
2.  **Considerations**: Factors that influence the desire to perform an action (e.g., Hunger level increases the desire to Eat).
3.  **Utility Engine**: A system that calculates a score (0.0 to 1.0) for each action based on its considerations and selects the highest-scoring one.
4.  **Behavior Tree Integration**: A specialized `UtilitySelector` node in the Behavior Tree executes the selected action.

## Configuration: `actions.toml`

AI actions are defined in `data/ai/actions.toml`. This allows game designers to tweak behavior without changing code.

### Structure

```toml
[actions.Eat]
weight = 2.0  # Base multiplier for the score

[actions.Eat.effects]
type = "interact_item"
target_stat = "nutrition"
consume = true
stat_changes = { hunger = -20.0, happiness = 5.0 }

[[actions.Eat.considerations]]
name = "Hunger"
input = "hunger"      # The stat to evaluate
curve = "linear"      # The response curve type
params = { m = 1.0, b = 0.0 }
```

### Considerations

Considerations map an input value (usually a stat normalized to 0-100) to a score (0.0-1.0).

*   **Inputs**:
    *   `hunger`, `hunger_inv` (100 - hunger)
    *   `energy`, `energy_inv` (100 - energy)
    *   `happiness`, `happiness_inv` (100 - happiness)
    *   `cleanliness`
    *   `constant_100`, `constant_0`

*   **Curves**:
    *   `linear`: `m * x + b`
    *   `inverse_linear`: `1.0 - x` (where x is normalized 0-1)
    *   `logit`: S-curve, useful for thresholds. Params: `k` (steepness), `x0` (midpoint).
    *   `threshold`: Returns 1.0 if x >= threshold, else 0.0.

## Adding New Actions

1.  **Define the Action** in `data/ai/actions.toml`.
2.  **Implement the Behavior** in `src/yukkuri_game/game/ai/behavior.py` if it's a new type of behavior.
    *   Register the behavior builder using `BehaviorRegistry.register_goal("ActionName", builder_function)`.
    *   Ensure the `ActionName` matches the key in `actions.toml`.

## Architecture

*   **`UtilityAIEngine`** (`src/yukkuri_game/game/ai/utility.py`): Loads actions and calculates scores.
*   **`UtilitySelector`** (`src/yukkuri_game/game/ai/utility_selector.py`): A Behavior Tree node that queries the engine and updates `AIState.current_action`.
*   **`BehaviorSystem`** (`src/yukkuri_game/game/systems/behavior.py`): Manages the Behavior Trees for all entities.

The Behavior Tree root is a `Sequence` that first runs the `UtilitySelector`, then runs an `ExecutionSelector` which executes the specific subtree for the chosen action.
