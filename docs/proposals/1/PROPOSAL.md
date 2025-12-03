### Revised Proposal V4: Kinematic Control & Composite Constraints

**Goal:** Create a robust "Stacking" system where riders become physical extensions of the parent without altering the parent's control feel, while retaining arcade-like movement responsiveness.

## 1\. Smart Dynamic Movement (Refined)

We retain the logic of separating "Input Velocity" from "Knockback Velocity" to allow crisp controls that can still be overpowered by explosions.

### 1.1 Component Changes

Update `MovementController` in `components.py`:

```python
@dataclass
class MovementController:
    target_velocity: Vector2 = field(default_factory=lambda: Vector2(0, 0))
    # ... visual bobs ...
    
    # Physics Control
    knockback_timer: float = 0.0
    knockback_threshold: float = 10.0 # Velocity below which control returns
    is_airborne: bool = False # Visual state for flying
```

### 1.2 MovementSystem Logic

In `MovementSystem.update`:

1.  **State Evaluation:**

      * If `knockback_timer > 0`:
          * Reduce timer by `dt`.
          * Check `body.velocity.length`. If `< knockback_threshold`, force `knockback_timer = 0`.
      * State is `CONTROLLED` if `knockback_timer <= 0`.

2.  **Velocity Application:**

      * **If CONTROLLED:**
          * Directly set `body.velocity = controller.target_velocity`.
          * Set `body.torque = 0` and `body.angular_velocity = 0`.
      * **If KNOCKBACK:**
          * Do **NOT** touch `body.velocity` (let Pymunk handle friction/damping).
          * Allow `body.angle` to change (if we want tumbling), or keep it locked.

## 2\. The Composite Mount System

Instead of a generic parent/child link, we treat mounting as **Shape Grafting**. The Parent is the only active physics agent.

### 2.1 The `Mount` Component

This component lives on the **Rider** (the entity being carried).

```python
@dataclass
class Mount(Component):
    carrier_id: int               # The immediate entity carrying this one
    root_id: int                  # The bottom-most entity (Physical Body owner)
    
    # Relative Positioning
    offset_x: float               # Offset from carrier center
    offset_y: float               # Offset from carrier center
    
    # Pymunk Restoration Data (Saved before grafting)
    original_shape_radius: float
    original_mass: float
    original_filter: pymunk.ShapeFilter
```

### 2.2 MountSystem Architecture

The `MountSystem` handles the lifecycle of grafting shapes.

#### **A. Operation: Mount (Grafting)**

When Entity A (Rider) mounts Entity B (Carrier):

1.  **Resolve Root:**
      * If B has a `Mount` component, `Root = B.Mount.root_id`.
      * Else, `Root = B`.
2.  **Physics Graft:**
      * **Remove** A's `PhysicsBody` from the Pymunk Space and ECS.
      * **Create** a new `pymunk.Circle` (or Poly).
      * **Calculate Offset:** The shape offset must be: `(B_pos - Root_pos) + Desired_Mount_Offset`.
          * *Critical:* Pymunk shape offsets are in local body coordinates.
      * **Attach** this new shape to `Root`'s body.
      * **Add Mass:** `Root.body.mass += A.mass`.
3.  **Component Setup:**
      * Add `Mount` component to A.
      * Tag A with `VisualTransform` logic to sync rendering.

#### **B. Operation: Update (Visual Sync)**

Every frame, `MountSystem` updates the Rider's `Transform` to match the physics simulation, handling Sprite Flipping.

```python
# Pseudo-code for Update Loop
for rider_id, mount in world.get_components(Mount):
    root_trans = world.get_component(mount.root_id, Transform)
    carrier_sprite = world.get_component(mount.carrier_id, Sprite)
    
    # Calculate Flip-Aware Offset
    final_offset_x = mount.offset_x
    if carrier_sprite.flip_x:
        final_offset_x = -mount.offset_x # Flip position relative to carrier
        
    # Apply to Rider
    rider_trans.x = root_trans.x + final_offset_x
    rider_trans.y = root_trans.y + mount.offset_y
    
    # Sync Rider facing direction to Carrier
    rider_sprite.flip_x = carrier_sprite.flip_x
```

#### **C. Operation: Dismount (Reconstruction)**

When A dismounts:

1.  **Remove Shape:** Find and remove the specific shape corresponding to A from `Root`'s body.
2.  **Restore Mass:** `Root.body.mass -= mount.original_mass`.
3.  **Reconstruct Body:** Call `physics_utils.add_physics_body(...)` for A at its current `Transform` position.
4.  **Pop Impulse:** Apply a small velocity impulse to A to prevent immediate re-collision.

## 3\. Edge Case: The "Orphan" Prevention

If the Root entity dies, the physical body is destroyed. We must ensure Riders don't vanish.

**Event Subscription:** `EntityDestroyedEvent`

**Handler Logic:**

1.  Check if the destroyed entity is a `root_id` for any active `Mount` components.
2.  **Iterate backwards** (top of stack down) or simply force dismount all.
3.  Trigger `Dismount` logic for all children *before* the physics space removes the Root body.
4.  Since the Root body is about to disappear, we don't need to clean up shapes/mass, just reconstruct the Riders' individual bodies.

## 4\. Implementation Plan

1.  **Update `MovementSystem`**: Implement `knockback_timer` and velocity thresholding.
2.  **Create `Mount` Component**: Define the data structure in `yukkuri_components.py`.
3.  **Implement `MountSystem`**:
      * `mount(rider, carrier)`: Handles shape grafting.
      * `dismount(rider)`: Handles shape removal and body reconstruction.
      * `update()`: Syncs transforms and handles flipping.
      * `on_entity_destroyed()`: Safety catch for parent death.
4.  **Update `InteractionSystem`**: Add "Ride" interaction which triggers the `MountSystem`.
