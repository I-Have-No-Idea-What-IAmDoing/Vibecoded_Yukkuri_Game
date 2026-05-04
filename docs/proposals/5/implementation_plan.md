# Proposal 5: Declarative Component Persistence

## Overview
The current persistence system relies on the `Persistable` marker component and manual logic in the `WorldSerializer` to determine which components should be saved.

## Motivation
- **Developer Experience**: Adding a new component to the save system should be as simple as adding a decorator.
- **Robustness**: Reduces the chance of forgetting to include a component in the save logic.
- **Granularity**: Allows marking specific fields within a component as non-persistent (e.g., temporary caches).

## Proposed Changes

### 1. Introduce `@persistent` decorator
Create a decorator (or a base class field) to mark components for persistence.

```python
@persistent
@dataclass
class YukkuriStats:
    hunger: float
    happiness: float
    _cached_value: float = field(metadata={"persistent": False})
```

### 2. Update `WorldSerializer`
Refactor the serializer to use reflection (inspecting types and metadata) to automatically identify and serialize persistent components and their fields.

### 3. Replace `Persistable` marker
The entity-level `Persistable` component can remain to indicate *which entities* to save, but the *which components* logic will be handled by the decorators.

## Impact
- **Maintainability**: New components automatically integrate with the save system.
- **Safety**: Prevents saving of volatile state that should be re-initialized on load (like timers or animation state).

## Implementation Phases
1.  **Phase 1**: Implement the `@persistent` decorator and field metadata parsing.
2.  **Phase 2**: Update `WorldSerializer` to use the new metadata.
3.  **Phase 3**: Audit all existing components and apply the decorator where appropriate.
4.  **Phase 4**: Remove legacy manual serialization logic.
