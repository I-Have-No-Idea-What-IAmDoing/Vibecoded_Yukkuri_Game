### Revised Proposal V2: Hybrid Kinematic Controller

**Goal:** Implement a movement system that eliminates "floatiness" and provides precise control, while leveraging Pymunk for collision detection and interaction.

## 1. Problem: "Floaty" Physics vs "Arcade" Feel

Pure physics-based movement (adding forces) can feel slippery. Pure kinematic movement (setting position) ignores the environment. We need a hybrid.

## 2. Proposed Solution: Velocity-Based Kinematic Control

Instead of a custom Python solver, we use Pymunk's `Body.KINEMATIC` (or a high-damping Dynamic body) and manage velocity explicitly.

### 2.1 The Hybrid Controller

We maintain the entity as a **Dynamic Body** (to allow it to be pushed by explosions/pistons) but effectively override its behavior during normal movement.

**Movement Logic:**

1.  **Input Phase:**
    *   Calculate desired velocity vector from input.
    *   If input is present, set `body.velocity` directly to this target (or interpolate towards it heavily).
    *   This gives the "snappy" response of a kinematic controller.
2.  **Physics Phase (Pymunk):**
    *   Pymunk resolves collisions. If the character hits a wall, Pymunk stops them. No custom "slide" code needed.
    *   **High Friction/Damping:** Set high friction on the body/shapes so it stops instantly when input stops.
3.  **Interaction Phase:**
    *   If an external large force (Knockback) is detected (e.g., magnitude > threshold), temporarily disable the "Input Override" and let physics take over until velocity settles.

### 2.2 Hierarchical Mounting (Refined)

We adopt the **Constraint System** from Proposal 1, but with a Kinematic Twist.

*   **Vehicles:** Vehicles are Dynamic Bodies.
*   **Passengers:** When a Yukkuri mounts a vehicle, we create a **PivotJoint**.
*   **Control:**
    *   The Passenger sends control inputs to the *Vehicle*.
    *   The Vehicle (Parent) applies the force/velocity.
    *   The Passenger (Child) is dragged along by the joint.

## 3. Implementation Plan

### 3.1 Update `MovementSystem`

```python
def update(self, dt):
    for entity, (body, controller) in components:
        if controller.is_knocked_back:
            # Let physics handle it until slow enough
            if body.velocity.length < 10:
                controller.is_knocked_back = False
        else:
            # Arcade Control
            target_v = controller.input_vector * controller.speed
            
            # Linear Interpolation for subtle smoothness, or direct set for crispness
            body.velocity = body.velocity.interpolate_to(target_v, dt * controller.acceleration)
            
            # Stop rotation
            body.angular_velocity = 0
```

### 3.2 Update `MountSystem`

*   Use `PivotJoint` for attaching entities.
*   **Input Delegation:** If an entity is a child (mounted), its `MovementController` inputs should be redirected to the Parent's `MovementController` (if the mount allows driving).

## 4. Benefits

*   **Simplicity:** No custom collision code.
*   **Robustness:** Pymunk handles all wall sliding, corner cases, and tunneling prevention.
*   **Feel:** Direct velocity manipulation eliminates "drift" while retaining collision response.
