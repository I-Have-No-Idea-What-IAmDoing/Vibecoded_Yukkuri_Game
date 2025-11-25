# Yukkuri Movement System Refactoring

## 1. Introduction

The current Yukkuri Movement System, centered around a large `MoveToTarget` Behavior Tree node, has proven difficult to maintain and extend. The tight coupling of pathfinding, steering, and physics logic within a single action node makes it brittle and hard to add character-specific nuances to movement.

This proposal outlines a refactoring—not a complete re-architecture—of the movement system. The goal is to replace the "god object" with a more focused, stateful **`MovementController` component**. This approach will improve clarity, give the AI more direct control, and, most importantly, create a foundation for higher-quality, character-rich movement.

## 2. Problem Statement

The core issue remains the `MoveToTarget` action node. It is responsible for too much:
- High-level goal setting (where to go).
- Mid-level planning (pathfinding, stuck detection).
- Low-level execution (steering forces, physics manipulation).

This monolithic design makes it difficult to debug and prevents the implementation of unique movement styles for different character types. Any change to steering, for example, requires modifying a large, complex class that also contains unrelated pathfinding logic. The goal is to solve this problem without introducing unnecessary architectural complexity.

## 3. Proposed Design

We will move away from a distributed, asynchronous pipeline and instead adopt a concrete, command-driven `MovementController`.

### 3.1. The `MovementController` Component

This new component will be the primary interface for movement. The AI will command it directly, and the controller will be responsible for the entire execution of that command.

```python
# A conceptual implementation of the controller
class MovementController:
    """A stateful component that handles the execution of movement commands."""

    def __init__(self, entity, pathfinder):
        self._entity = entity
        self._pathfinder = pathfinder
        self.path = None
        self.is_moving = False
        # ... other state variables like stuck timers, etc.

    def move_to(self, target_position):
        """Commands the controller to move to a new target."""
        self.path = self._pathfinder.find_path(self._entity.position, target_position)
        if self.path:
            self.is_moving = True
            # ... reset state for a new path
        else:
            self.is_moving = False

    def stop(self):
        """Immediately halts all movement."""
        self.is_moving = False
        # ... clear velocity/forces on the physics body

    def update(self, dt):
        """This method is called every frame by a simple system."""
        if not self.is_moving or not self.path:
            return

        # Core logic resides here:
        # 1. Follow the current path.
        # 2. Calculate steering forces.
        # 3. Apply forces to the physics body.
        # 4. Handle arrival at waypoints and the final destination.
        # 5. Detect if the entity is stuck.
```

### 3.2. AI and Behavior Tree Control

The Behavior Tree's responsibility is simplified to issuing commands and monitoring the controller's state.

-   **New `MoveToTarget` Action Logic**:
    1.  Get the `MovementController` component from the entity.
    2.  On first execution, call `movement_controller.move_to(target)`.
    3.  Monitor `movement_controller.is_moving`.
    4.  Return `RUNNING` while `is_moving` is true.
    5.  Return `SUCCESS` when the controller signals completion.
    6.  Return `FAILURE` if the controller signals the path is unreachable or it gets stuck.

This is simple, predictable, and easy to debug. The entire call stack for a movement decision remains in a single place.

### 3.3. Embracing Character with Inheritance

To create unique movement styles, we will use inheritance. `MovementController` will serve as a base class.

```python
class YukkuriMovementController(MovementController):
    """Implements the specific 'waddle' and 'stumble' of a Yukkuri."""

    def update(self, dt):
        # Override the base update method
        if not self.is_moving:
            return

        # Add logic for waddling motion instead of sterile 'seek' behavior
        self._apply_waddle_force()

        # Add logic for stumbling over small obstacles
        if self._check_for_stumble():
            self._play_stumble_animation()

        # Call the parent's update for basic path following
        super().update(dt)
```
This approach keeps character-specific code with the character, rather than trying to fit it into a generic, one-size-fits-all system.

## 4. Rationale

### 4.1. Clarity and Debuggability
All the logic for *how* an entity moves is now located in one class, the `MovementController`. We are trading a distributed state machine (spread across multiple ECS systems) for a single, stateful object that is easy to inspect and debug.

### 4.2. Direct, Imperative Control
The AI maintains direct control. If a high-priority behavior needs to interrupt movement, it can simply call `movement_controller.stop()`. This is far simpler than canceling a `MovementRequest` and waiting for a distributed pipeline to react.

### 4.3. Prioritizing Quality
This design makes implementing high-quality, characterful movement the primary focus. Instead of abstracting movement into generic behaviors, we provide a clear place—the derived controller—to add the personality that will make the game's creatures feel alive.

### 4.4. Solves the Core Problem
This refactoring successfully breaks up the `MoveToTarget` god object into a smaller, more focused BT node and a cohesive, reusable `MovementController` component, achieving the original goal without the unnecessary complexity.
