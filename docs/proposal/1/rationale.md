# Rationale for Architecture Redesign

## Motivation

The current architecture works for smaller scopes but exhibits signs of coupling that will hinder future growth. The `GameManager` acts as a God Object, and hardcoded entity creation limits moddability and rapid iteration.

## Benefits

### 1. Decoupling and Modularity
By introducing a `SceneManager` and `Application` class, we separate the engine lifecycle from the game logic. This makes it easier to add new game modes (e.g., a Sandbox mode or a Tutorial) without cluttering the main loop.

### 2. Moddability and Data-Driven Design
Moving entity definitions to external files (Prefabs) allows designers to tweak gameplay values (health, speed, initial stats) without touching the code. This is a crucial step towards supporting user-generated content and mods.

### 3. Maintainability
The Input Abstraction Layer ensures that changing input schemes (e.g., adding Gamepad support) only requires updating the mapping configuration, not every single system that checks for input.

### 4. Robustness
A queued Event System prevents "event cascades" where one event triggers another, leading to deep recursion or unpredictable state changes within a single frame. Deferred processing ensures a stable state during event handling.

### 5. Testability
Strict separation of Components (data) and Systems (logic) makes unit testing easier. We can instantiate a Component with specific data and run a System on it to verify the outcome without needing to spin up the entire engine.

## Trade-offs

### 1. Complexity
The new architecture introduces more layers (SceneManager, ActionMapper). This increases the initial learning curve for new contributors.

### 2. Boilerplate
Defining Prefabs in YAML/TOML and mapping inputs requires more setup than simply writing `if key == 'A'` or hardcoding an entity in Python.

### 3. Migration Effort
Refactoring the existing `GameManager` and `EntityFactory` will require significant effort and careful regression testing to ensure existing gameplay features remain functional.

## Conclusion
The long-term benefits of a clean, data-driven, and modular architecture outweigh the initial cost of refactoring. This proposal sets a solid foundation for the Yukkuri Game to grow in complexity and content.
