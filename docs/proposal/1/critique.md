# Critique of Data Persistence Proposal (v3)

## Section 7: Data Persistence & State Transfer

While the latest revision correctly identifies the dangers of vendor lock-in and manual dirty flags, the proposed solution introduces new forms of boilerplate, architectural coupling, and vagueness. The design feels like a reaction to previous failures rather than a coherent, forward-looking system.

### 1. The "Boilerplate Injection" Fallacy

The proposal introduces a `MANIFEST` dictionary to declare dependencies, which is good metadata. However, it then immediately renders that metadata redundant by requiring manual boilerplate in `setup()`:

```python
# Why do I have to write this if I already declared it in MANIFEST?
inv_data = initial_state.get("player.inventory")
inv = self.serializer.deserialize(inv_data, target_type=Inventory)
player.add(inv)
```

This violates the DRY (Don't Repeat Yourself) principle. If the `SceneManager` knows a scene requires `"player.inventory"` and it knows the target component is `Inventory` (which should be part of the contract), it should inject it automatically. Requiring the developer to manually fetch, deserialize, and attach components for every single piece of persistent data is tedious, error-prone, and scales poorly.

### 2. Migration Logic Pollution

Encapsulating schema migration inside the Component class (`@staticmethod def migrate...`) is a violation of the Single Responsibility Principle.

*   **Pollution**: It forces a clean Data Object (Component) to carry the baggage of every legacy version of its schema. Over time, your clean `Inventory` class will contain 90% migration logic for v1, v2, v3... and 10% actual data definition.
*   **Type Safety Violation**: The `migrate` method operates on raw `dict` objects (`data['items']`). This forces developers to write untyped, fragile dictionary manipulation code directly inside their otherwise type-safe dataclasses.
*   **Solution**: Migrations should be handled by separate `MigrationStrategy` classes or functions, keeping the Component definition pure.

### 3. Indecisiveness ("Option A vs Option B")

A design document exists to make decisions. Presenting "Option A (Snapshot)" and "Option B (Proxies)" as valid paths without committing to one is architectural procrastination.

*   **The Problem with Proxies (Option B)**: Implementing transparent dirty-tracking proxies in Python is notoriously difficult, especially for nested mutable structures (e.g., a `list` inside a `dataclass`). It adds runtime overhead and debugging complexity.
*   **The Problem with Snapshots (Option A)**: While safer, it risks data loss if the game crashes between checkpoints.
*   **Critique**: The proposal must pick a lane. If "Option A" is preferred, explicitly reject Option B and define how Option A mitigates data loss (e.g., autosaves, crash recovery), rather than leaving a "optimization" loophole that undermines the whole system's consistency.

### 4. "Stringly" Typed Chaos

Replacing a global Enum with magic strings (`"player.inventory"`) swings the pendulum from "Centralized Bottleneck" to "Unmanageable Chaos".

*   **Fragility**: A typo in the string (`"player.invantory"`) will silently fail or cause runtime errors that are hard to debug.
*   **Discovery**: There is no easy way to know what keys are available or used across the project without grepping the codebase.
*   **Correction**: While we shouldn't have a monolithic file, we need *some* structured way to define keys (e.g., constant files per module) rather than encouraging raw string literals scattered throughout Scene files.

### 5. Vagueness on "Relevant Components"

The proposal states: *"The PersistenceSystem gathers data from relevant components."*

This is hand-waving. How does it know what is relevant?
*   Does it iterate every entity in the world? (Slow)
*   Do components register themselves? (Complexity)
*   Is there a `Persistable` marker interface?
The mechanism for identifying *what* to save is just as important as *how* to save it, and it is currently undefined.
