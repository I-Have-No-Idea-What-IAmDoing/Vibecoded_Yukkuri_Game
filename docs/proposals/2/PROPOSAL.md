# Proposal: Kinematic Movement & Hierarchical Mounting System

## 1\. Problem Statement

The current Pymunk-driven movement system treats entities like billiard balls. This causes several issues for a simulation game:

  * **"Floaty" Movement:** Entities drift and overshoot targets.
  * **Complex Interactions:** Stacking entities (e.g., a Yukkuri riding a Roomba) requires complex physics constraints (PinJoints, DampedSprings) which are unstable and bug-prone.
  * **Overhead:** Solving physics manifolds for simple walking logic is unnecessary computation.

## 2\. Proposed Solution

We will transition to a **Kinematic Movement System**.

1.  **Movement:** Position is updated directly based on velocity (`pos += vel * dt`).
2.  **Collision:** Physics is used **only** for detection. If a movement vector intersects a wall, we slide against it.
3.  **Hierarchy (Mounting):** We introduce a parent-child relationship system.
      * **Root Entities:** Move based on their own AI/Input.
      * **Child Entities:** Position is locked to the Parent's position + an offset.
      * This unifies logic for **Riding** (Child on Parent) and **Carrying** (Parent holding Child).

-----

## 3\. New Data Structures

### 3.1 New Component: `Mount`

This component manages the hierarchy. It replaces complex physics joints.

```python
# src/yukkuri_game/game/components.py

@dataclass
class Mount:
    """
    Component for handling entity hierarchy (Riding, Carrying, Vehicles).
    """
    # If not None, this entity is attached to another (The Parent)
    parent_id: int = -1
    
    # List of entities attached to this one (The Children)
    children_ids: List[int] = field(default_factory=list)
    
    # Where children attach relative to this entity's center
    # key: 'default', 'mouth', 'back', etc. value: (x, y) offset
    mount_points: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    
    # Which mount point on the parent is this entity occupying?
    occupied_slot: str = "default"
```

### 3.2 Modified Component: `MovementController`

We strip out physics-specific tuning and add kinematic flags.

```python
@dataclass
class MovementController:
    target_velocity: Vector2 = field(default_factory=lambda: Vector2(0, 0))
    current_speed: float = 0.0
    max_speed: float = 100.0
    
    # If True, this entity does not process its own movement logic
    # (Used when being carried or riding)
    is_mounted: bool = False 
```

-----

## 4\. Implementation Plan

### Phase 1: Decoupling Physics

**Goal:** Stop `PhysicsSystem` from writing to `Transform`. Make `PhysicsBody` kinematic (sensor only).

1.  **Modify `PhysicsSystem`**:

      * Change Pymunk body type to `pymunk.Body.KINEMATIC`.
      * Stop the automatic sync of `Body.position -> Transform`.
      * Instead, we will sync `Transform -> Body.position` so the collision shape follows the visual sprite.

2.  **Update `create_yukkuri` / `create_item` prefabs**:

      * Set body type to `KINEMATIC` during creation.

### Phase 2: The Kinematic Movement System

**Goal:** Implement "Slide" movement logic.

Create `src/yukkuri_game/game/systems/kinematic_movement_system.py`.

```python
class KinematicMovementSystem(System):
    def update(self, world, dt):
        physics_system = world.services.get(PhysicsSystem)
        
        for entity, (trans, move, body) in world.get_components_tuple(Transform, MovementController, PhysicsBody):
            # 1. Skip if mounted (Parent handles movement)
            if move.is_mounted:
                continue

            # 2. Calculate Desired Move
            velocity = move.target_velocity
            if velocity.length < 0.1:
                continue
                
            desired_pos = (trans.x + velocity.x * dt, trans.y + velocity.y * dt)
            
            # 3. Collision Check (Sweep Test)
            # Use Pymunk shape query to see if desired_pos overlaps a WALL
            # If overlap, project velocity along the wall (slide)
            
            # (Simplified Logic)
            if not self.check_collision(physics_system, desired_pos, body):
                trans.x = desired_pos[0]
                trans.y = desired_pos[1]
            else:
                # Handle Wall Slide (Try moving X only, then Y only)
                ...
            
            # 4. Sync Transform to Physics Body (for next frame collision checks)
            body.body.position = (trans.x, trans.y)
```

### Phase 3: The Mounting System (Riding & Carrying)

**Goal:** Update child positions based on parent positions.

Create `src/yukkuri_game/game/systems/mount_system.py`.

```python
class MountSystem(System):
    def update(self, world, dt):
        # Iterate over all entities that have children
        for parent_id, (trans, mount) in world.get_components_tuple(Transform, Mount):
            if not mount.children_ids:
                continue
                
            for child_id in mount.children_ids:
                child_trans = world.get_component(child_id, Transform)
                child_move = world.get_component(child_id, MovementController)
                
                if child_trans and child_move:
                    # 1. Disable child's own movement
                    child_move.is_mounted = True
                    child_move.target_velocity = (0, 0)
                    
                    # 2. Calculate offset
                    # E.g., Riding on head: offset (0, -20)
                    # E.g., Being carried in mouth: offset (10, 0) based on facing
                    offset = mount.mount_points.get("default", (0,0))
                    
                    # 3. Update Child Position
                    child_trans.x = trans.x + offset[0]
                    child_trans.y = trans.y + offset[1]
                    
                    # 4. Update Child Z-Index (Layering)
                    # Riders should be drawn *after* parent
                    # Carried items might be *before* or *after* depending on facing
```

### Phase 4: AI Actions for Mounting

We need new Actions in `data/ai/actions.toml` and implementations in `behavior.py`.

1.  **Action: `RideVehicle`**

      * Find `Item` with `is_vehicle=True`.
      * Move to it.
      * Interact -\> Triggers `Mount` logic.

2.  **Action: `CarryItem`**

      * Find `Item` with `is_portable=True`.
      * Move to it.
      * Interact -\> Triggers `Mount` logic (Item becomes child of Yukkuri).

3.  **Code Logic (`Interact` Action update)**:

    ```python
    # In Interact.update or a new MountAction.update
    if action == "Mount":
        mount_component = world.get_component(target_id, Mount)
        mount_component.children_ids.append(self.entity_id)
        
        my_mount = world.get_component(self.entity_id, Mount)
        my_mount.parent_id = target_id
        
        # Disable physics/collision for the child so they don't collide with the parent
        # Set child pymunk filter to ignore parent
    ```

-----

## 5\. Migration Checklist

1.  **Refactor `components.py`**: Add `Mount`, update `MovementController`.
2.  **Refactor `prefabs/`**: Ensure all entities initialize with `Mount` component and `KINEMATIC` bodies.
3.  **Remove `MovementSystem.py`**: Delete the old physics-force-applier.
4.  **Add `KinematicMovementSystem.py`**: Implement sliding movement.
5.  **Add `MountSystem.py`**: Implement hierarchical position updates.
6.  **Update `SystemRegistry`**: Register the new systems in the correct order:
    1.  `BehaviorSystem` (Decides logic)
    2.  `KinematicMovementSystem` (Moves roots)
    3.  `MountSystem` (Moves children relative to roots)
    4.  `PhysicsSystem` (Syncs bodies for queries)
    5.  `RenderSystem` (Draws result)

## 6\. Benefits of this approach

  * **Vehicles:** A "Cart" entity is just a standard entity with a `Mount` component. When a Yukkuri mounts it, the Yukkuri becomes the child. The Cart moves (via external force or Yukkuri pushing it), and the Yukkuri stays locked to it.
  * **Carrying:** A Yukkuri picks up a "Cookie". The Cookie becomes a child of the Yukkuri. The Cookie's physics body moves with the Yukkuri automatically.
  * **Stacks:** You can have a Yukkuri carrying a Cookie, while riding a Roomba. (Roomba -\> Yukkuri -\> Cookie). The `MountSystem` handles this recursion naturally.

This plan removes the instability of physics joints while keeping the robustness of physics-based collision detection.
