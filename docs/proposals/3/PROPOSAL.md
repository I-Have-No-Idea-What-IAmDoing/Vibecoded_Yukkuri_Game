# Revised Proposal 3: Deterministic Kinematic Controller (The "Controller" Pattern)

## 1. Goal: "Pixel-Perfect" Arcade Movement

We aim for movement that is **responsive, predictable, and crisp**. The player's input should translate directly to position changes, not forces. Physics should be used purely for collision detection, not simulation.

## 2. Core Mechanic: Axis-Separated Kinematic Movement

We replace the physics solver with a custom **Kinematic Controller** that utilizes Pymunk for collision queries.

### 2.1 The Algorithm

For every moving Root entity (per frame):

1.  **Calculate Velocity:**
    *   `Input Velocity` = Input Vector * Speed.
    *   `External Velocity` = Knockback Vector (decays over time).
    *   `Total Velocity` = Input Velocity + External Velocity.

2.  **Move X:**
    *   Calculate `dx = Total Velocity.x * dt`.
    *   **Propose Position:** `new_x = current_x + dx`.
    *   **Collision Check:** Query Pymunk: "Does my shape overlap anything at `(new_x, current_y)`?"
    *   **Resolution:**
        *   If **No Hit**: Commit `current_x = new_x`.
        *   If **Hit**: Move as close as possible to the obstacle (using a binary search or Pymunk's contact info) and stop. Set `Total Velocity.x = 0`.

3.  **Move Y:**
    *   Calculate `dy = Total Velocity.y * dt`.
    *   **Propose Position:** `new_y = current_y + dy`.
    *   **Collision Check:** Query Pymunk: "Does my shape overlap anything at `(current_x, new_y)`?"
    *   **Resolution:**
        *   If **No Hit**: Commit `current_y = new_y`.
        *   If **Hit**: Move as close as possible and stop. Set `Total Velocity.y = 0`.

4.  **Update Pymunk:**
    *   Manually update the Pymunk Body position to match the new `(current_x, current_y)`.
    *   Call `space.reindex_shapes_for_body(body)` to ensure next frame's queries are accurate.

### 2.2 Why Axis-Separated?
*   **Corner Sliding:** Automatically handles sliding against walls. If you move diagonally into a wall, the X-check might fail (stop X movement), but the Y-check succeeds, resulting in a perfect slide.
*   **Robustness:** Prevents getting stuck in corners better than arbitrary vector sliding.

## 3. The Hierarchy: Rigid Transform Parenting

Since we control the position manually, we can implement a rock-solid parenting system.

### 3.1 `Mount` Component
```python
@dataclass
class Mount(Component):
    parent_id: int = -1 # If set, I am a child.
    children_ids: List[int] = field(default_factory=list) # If set, I am a parent.
    offset: Vector2 = Vector2(0, 0)
    disable_collision: bool = True # Typically true for riders
```

### 3.2 The `MountSystem`
Runs **after** `KinematicMovementSystem`.

1.  **Iterate Roots:** Find all entities with `Mount` that have *no* `parent_id` (Roots).
2.  **Recursive Update:**
    *   For each child:
        *   `Child.Position = Parent.Position + Child.Offset` (Account for Parent Flip/Rotation if needed).
        *   `Child.Body.position = Child.Position` (Sync physics body).
        *   `space.reindex_shapes_for_body(Child.Body)`.
    *   Recurse to grandchildren.

### 3.3 Collision Handling for Stacks
*   **Composite Hitbox:** The Root entity's collision check must account for the *entire stack*.
*   **Implementation:**
    *   When checking collisions (Step 2.1), the controller iterates through all children in the stack.
    *   It performs the check for the Root shape *and* all Child shapes at the proposed offset.
    *   If *any* shape in the stack hits a wall, the movement is blocked for the *entire stack*.
    *   This prevents children from clipping through walls ("Ghost Child" problem) and ensures the stack moves as a single solid unit.

## 4. Implementation Steps

1.  **Physics Setup:** Configure Pymunk bodies as `KINEMATIC` so the solver doesn't touch them.
2.  **`KinematicMovementSystem`:** Implement the Axis-Separated movement loop.
    *   *Optimization:* Instead of full `shape_query` sweeps, use `space.point_query` for simple checks or `bb_query` for broadphase first.
    *   *Stack Check:* Modify the collision predicate to loop through `Mount.children_ids` and check their transformed shapes as well.
3.  **`MountSystem`:** Implement the recursive transform sync.
4.  **`InteractionSystem`:** Add logic to link/unlink entities (populating the `Mount` component).

## 5. Summary
This proposal delivers the tightest control scheme. It trades the "emergent behavior" of a physics engine for the "reliability" of a custom controller. By treating the stack as a **Composite Kinetic Body**, we solve the clipping issues while maintaining pixel-perfect precision.
