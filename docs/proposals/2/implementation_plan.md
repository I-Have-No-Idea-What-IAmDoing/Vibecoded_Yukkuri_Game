# Proposal 2: Standardize Service Access via System.initialize()

## Overview
Currently, ECS systems acquire services (like `EventBus`, `ResourceManager`, etc.) in inconsistent ways: some via constructor arguments, some via `world.services.get()` inside `update()`, and others at module level.

## Motivation
- **Dependency Clarity**: Explicitly fetching dependencies in `initialize()` makes it clear what a system needs to function.
- **Initialization Safety**: Ensures all services are registered and available before the system starts its first `update()`.
- **Cleaner Registry**: Simplifies the `SystemRegistry.register_systems` method by removing the need to pass many arguments to constructors.
- **Testability**: Makes it easier to mock services for unit testing systems in isolation.

## Proposed Changes

### 1. Update `System.initialize()` usage
Ensure every system uses `self.ecs_world.services` within `initialize()` to cache references to required services.

```python
class MySystem(System):
    def initialize(self):
        self.event_bus = self.ecs_world.services.get(EventBus)
        self.rm = self.ecs_world.services.get(ResourceManager)
    
    def update(self, world, dt):
        # Use self.event_bus and self.rm directly
        pass
```

### 2. Refactor existing systems
Systematically update all files in `src/yukkuri_game/game/systems/` to follow this pattern.

### 3. Simplify `SystemRegistry`
Remove service arguments from constructors in `src/yukkuri_game/system_registry.py`.

## Impact
- **Architecture**: Improved dependency injection pattern.
- **Maintainability**: New systems will be easier to write by following a clear template.
- **Breaking Changes**: Minimal, mostly internal to system initialization logic.

## Implementation Phases
1.  **Phase 1**: Audit all current systems and their dependencies.
2.  **Phase 2**: Update the base `System` class documentation/examples.
3.  **Phase 3**: Refactor systems one by one (starting with core systems like `PhysicsSystem` or `SocialSystem`).
4.  **Phase 4**: Update `SystemRegistry` and remove redundant constructor parameters.
