# ECS Guide (Entity Component System)

The Yukkuri Game Engine uses a custom wrapper around the [Esper](https://github.com/benmoran56/esper) library. This wrapper (`engine/ecs.py`) adds strong typing, context management, and a service locator pattern.

## Core Components

### 1. World (`engine.ecs.World`)
The `World` class is the central manager. It differs from standard Esper validation in that it supports **Multiple Worlds** (though typically one is active per Scene).

#### Key Features:
- **Context Management**: Use `with world.context():` to ensure operations apply to this specific world instance.
- **Service Locator**: `world.services` allows systems to find global providers (Audio, Physics) without hard dependencies.
- **Stable IDs**: `get_next_stable_id()` provides IDs that persist across save/load cycles, unlike runtime Entity IDs.

### 2. Components (`Component`)
Components are data containers. While Esper allows any Python object, we use `dataclasses` for performance and readability.

```python
@dataclass
class Health(Component):
    current: float = 100.0
    max: float = 100.0
```

### 3. Systems (`System`)
Systems contain the logic. They must inherit from `System` and implement `update`.

```python
class HealthSystem(System):
    def update(self, world: World, dt: float):
        # Efficiently iterate over entities with Health components
        for ent, health in world.get_component(Health):
            if health.current <= 0:
                world.destroy_entity(ent)
```

## Common Operations

### Creating an Entity
```python
player = world.create_entity(
    Transform(x=100, y=100),
    Health(100),
    Sprite(texture="yukkuri.png")
)
```

### Querying Entities
```python
# Get single component
transform = world.get_component(entity_id, Transform)

# Check existence
if world.has_component(entity_id, Health):
    pass

# Get all entities with specific components (Fastest)
for ent, (trans, sprite) in world.get_components_tuple(Transform, Sprite):
    render(trans, sprite)
```

## Best Practices
1.  **Keep Components Dumb**: Components should only store data. Logic belongs in Systems.
2.  **Use `get_components_tuple`**: It is significantly faster than querying components individually inside a loop.
3.  **Context Safety**: If you are writing a script that might run outside the main loop, always wrap ECS calls in `with world.context():`.
