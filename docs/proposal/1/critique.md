# Critique of Implementation Plan & Architecture

## General Assessment

The implementation plan (`tasks.md`) and the underlying design document exhibit a dangerous mix of over-engineering and under-specification. While the motivation to decouple the "God Object" `GameManager` is sound, the proposed solution replaces one monolith with a distributed mess of "Managers" and complex infrastructure that YAGNI (You Ain't Gonna Need It) should have killed in the crib.

## Specific Critique of `tasks.md`

### 1. The "Test-Last" Suicide Pact
Phase 3.4 lists "Write unit tests" and "Verify regressions" at the very end of the project.
*   **Harsh Reality**: By Phase 3, you will have rewritten the entire core engine (Application, Scene, Input, Events). If you wait until then to write tests, you will spend weeks debugging a system that doesn't start.
*   **Correction**: Tests must be written *concurrently* with the refactor. Phase 1 must include "Create Test Fixtures for Engine/Scene" and "Port existing logic to new tests".

### 2. Persistence: Over-Engineered & Risky
Phase 3 is a black hole of complexity.
*   **Premature Optimization**: "Implement async background saver" is listed before basic saving works. In Python, true async saving of a mutating game state is a concurrency nightmare (GIL, thread-safety, deep copying costs). This is a solution looking for a problem.
*   **YAGNI Violation**: `MigrationRegistry` and versioned schema transformations are listed as core tasks. Do we even have a save file yet? No. Why are we building a migration engine for a format that doesn't exist?
*   **Boilerplate Factory**: The plan to implement `Scene.INJECTIONS`, `keys.py`, and `SceneManager.hydrate_scene` creates a rigid dependency injection framework that solves a problem simple Python arguments could solve.

### 3. "Refactor Everything" Vagueness
Tasks like "Refactor systems to use direct observers" (1.2) and "Audit Components" (3.3) are open-ended time sinks.
*   **Ambiguity**: Which systems? All of them? "Direct observers" suggests a web of callbacks that is arguably worse than an event bus for debugging.
*   **Scope Creep**: "Audit Components" is not a task; it's a daydream. It needs to be specific: "Move `health` logic from `CombatSystem` to `HealthComponent`".

### 4. Input System Bloat
Phase 2.1 proposes `InputContext`, `ActionMapper`, `InputManager`.
*   **Complexity**: While context-aware input is good, building a generic stack-based priority system for it might be overkill if we only have two contexts (Game, Menu).
*   **Integration**: The plan doesn't explain how this integrates with the new "Phase-Based Event System". Do inputs fire events? Do systems poll the InputManager?

## Specific Critique of Design (Persistence v3)

### 1. The "Boilerplate Injection" Fallacy
The proposal introduces a `MANIFEST` dictionary to declare dependencies, but then requires manual fetching and deserialization in `setup()`.
*   **DRY Violation**: If the Scene declares it needs `Inventory`, the engine should provide `Inventory`. Requiring manual `serializer.deserialize` calls in every scene's setup is tedious and error-prone.

### 2. Migration Logic Pollution
Encapsulating schema migration inside the Component class (`@staticmethod def migrate...`) violates the Single Responsibility Principle.
*   **Pollution**: Clean data classes become dumping grounds for legacy schema hacks.
*   **Type Safety**: It forces developers to write untyped dictionary manipulation code inside typed dataclasses.

### 3. "Stringly" Typed Chaos
Using `keys.py` to define `Final` constants for magic strings (`"player.inventory"`) is a band-aid, not a cure. It separates the key definition from the data definition, leading to "what key does this component use?" confusion.

### 4. Vagueness on "Relevant Components"
The proposal mentions `Persistable` components but fails to define how the serializer interacts with them. Does it scan the whole world? This is a performance trap.

## Conclusion & Recommendations

The plan needs to be **brutally simplified**.

1.  **Kill the Async Saver**: Use synchronous saving first.
2.  **Kill the Migration Registry**: Handle versioning later when we actually have a v2.
3.  **Kill the Dependency Injection Framework**: Pass a simple `GameContext` object to scenes.
4.  **Test First**: Move testing to Phase 0 or integrate it into every step.
5.  **Concrete Refactoring**: Replace "Audit" and "Refactor" with specific migration targets.
