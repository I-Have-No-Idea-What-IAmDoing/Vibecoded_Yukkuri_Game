# Rationale for Architecture Redesign

## Motivation

The current architecture works for smaller scopes but exhibits signs of coupling that will hinder future growth. The `GameManager` acts as a God Object, and hardcoded entity creation limits moddability and rapid iteration.

## Benefits

### 1. Decoupling and Modularity
By introducing a `SceneManager` and `Application` class, we separate the engine lifecycle from the game logic. This makes it easier to add new game modes (e.g., a Sandbox mode or a Tutorial) without cluttering the main loop.

### 2. Developer Ergonomics (Pythonic Prefabs)
Using Python for prefabs instead of YAML/TOML allows us to leverage the full power of the language (loops, conditionals, inheritance) for entity definition, providing better tooling support (IDE autocompletion, linting) and reducing context switching.

### 3. Debuggability and Determinism
The Phase-Based Event System and Typed Events reduce the chaos of asynchronous event chains. Knowing exactly *when* an event is processed (e.g., PostUpdate) and *what* data it carries (Type Hints) makes debugging significantly easier.

### 4. Pragmatic Flexibility
Relaxing strict ECS dogmas allows for more intuitive code. Helper methods on components prevent logic duplication (e.g., repeatedly calculating "is alive" checks) without violating the core principle of separation of data and global logic.

### 5. Context-Aware Input
Handling different input contexts (Menu, Gameplay, Inventory) explicitly prevents common bugs like "jumping while typing in chat" and simplifies the implementation of complex UI interactions.

## Trade-offs

### 1. Complexity
The new architecture introduces more layers (SceneManager, Input Contexts). This increases the initial learning curve for new contributors compared to a simple "check key everywhere" approach.

### 2. Migration Effort
Refactoring the existing `GameManager`, `EntityFactory`, and Input handling will require significant effort. Moving from "God Object" to specialized managers requires careful planning to avoid regression.

## Conclusion
The long-term benefits of a clean, modular, yet pragmatic architecture outweigh the initial cost of refactoring. This proposal sets a solid foundation for the Yukkuri Game to grow in complexity while keeping the codebase accessible and maintainable.
