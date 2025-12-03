### Revised Proposal V5: Constraint-Based Stacking & Force-Driven Movement

**Goal:** Create a robust "Stacking" system where riders are physically linked to the parent using physics constraints, maintaining separate bodies for stability and ease of simulation. Ensure movement controls feel responsive but respect the physics engine.

## 1. Force-Driven Movement

Instead of manually setting velocity (which fights physics), we use forces to drive the character. This allows natural interaction with the environment (friction, collisions, external forces).

### 1.1 Component Changes

Update `MovementController` in `components.py`:

```python
@dataclass
class MovementController:
    move_input: Vector2 = field(default_factory=lambda: Vector2(0, 0)) # Normalized input direction
    speed: float = 500.0 # Force magnitude
    damping: float = 15.0 # Damping factor to stop movement when no input
    max_velocity: float = 200.0 # Cap for movement-induced velocity (not external)
```

### 1.2 MovementSystem Logic

In `MovementSystem.update`:

1.  **Apply Damping:**
    *   Apply a damping force opposing velocity to simulate friction/air resistance.
    *   `force -= body.velocity * controller.damping`
2.  **Apply Input Force:**
    *   If `move_input` is non-zero:
        *   `force += move_input * controller.speed`
    *   Limit the *contribution* of this force if velocity exceeds `max_velocity` (optional, for tighter control).

## 2. The Constraint Mount System

We use Pymunk's `PivotJoint` (or similar constraints) to attach the Rider's body to the Carrier's body.

### 2.1 The `Mount` Component

This component lives on the **Rider**.

```python
@dataclass
class Mount(Component):
    carrier_id: int               # The entity carrying this one
    joint: Optional[pymunk.Constraint] = None # The physical connection
    offset: Vector2 = field(default_factory=lambda: Vector2(0, 0))
```

### 2.2 MountSystem Architecture

#### **A. Operation: Mount**

When Entity A (Rider) mounts Entity B (Carrier):

1.  **Positioning:**
    *   Move A's body to `B.position + offset`.
2.  **Create Joint:**
    *   Create a `pymunk.PivotJoint(B.body, A.body, anchor_point)`.
    *   Add the joint to the Pymunk Space.
    *   Store the joint in `A.Mount.joint`.
3.  **Disable Collisions (Optional):**
    *   Use `pymunk.ShapeFilter` to ignore collisions between A and B, or let them stack naturally if shapes don't overlap.
    *   Ideally, use collision groups to prevent A and B from colliding with each other while mounted.

#### **B. Operation: Update**

The physics engine handles position and velocity automatically.
*   **Visual Sync:** No manual transform syncing is needed for position. `PhysicsSystem` already syncs `Transform` from the Body.
*   **Flipping:** `MountSystem` still checks `B.Sprite.flip_x` to update `A.Sprite.flip_x` and potentially adjust the joint anchor if the offset is asymmetric.

#### **C. Operation: Dismount**

When A dismounts:

1.  **Remove Joint:** Remove `A.Mount.joint` from the Space.
2.  **Cleanup:** Remove `Mount` component from A.
3.  **Momentum:** A naturally retains its velocity from the movement. We can apply a small impulse if we want a "jump off" effect.

## 3. Edge Case: The "Orphan" Prevention

If the Carrier entity dies:

**Event Subscription:** `EntityDestroyedEvent`

**Handler Logic:**

1.  Check if the destroyed entity is a `carrier_id` for any active `Mount` components.
2.  For each attached Rider:
    *   Remove the joint from the space.
    *   Remove the `Mount` component.
    *   (Optional) Apply a small "tumble" impulse.
3.  The Rider is now a free-floating independent body.

## 4. Implementation Plan

1.  **Refactor `MovementSystem`**: Switch from velocity-setting to force-application.
2.  **Create `Mount` Component**: Define data structure.
3.  **Implement `MountSystem`**:
    *   Handle `MountEvent` to create joints.
    *   Handle `DismountEvent` to remove joints.
    *   Handle `EntityDestroyedEvent` to safely detach riders.
4.  **Collision Filtering**: Ensure riders and carriers don't jitter-collide (use `ShapeFilter` groups).
