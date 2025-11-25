# Critique: Hybrid Impulse-Based Movement System (Proposal 3)

This proposal presents itself as a pragmatic compromise, but it is, in reality, a collection of clever-sounding hacks that mask a deep-seated confusion about its own goals. It avoids the obvious pitfalls of the previous proposals but introduces more subtle, insidious problems that will make the system difficult to tune, debug, and extend.

## 1. "Cyclic Drag" is Physics Gibberish
The core of this design, the "cyclic drag" model, is a black box of arbitrary physics manipulation. The proposal hand-waves this critical component as a simple three-phase cycle ("Push", "Glide", "Land"). This is not a physical model; it's a magic trick. How is this cycle timed? Is it based on distance, time, or something else? How do you tune the drag and force curves to feel like a "hop" instead of a bizarre, rhythmic pulsing? You have replaced a predictable (if flawed) ballistic model with an ad-hoc, untunable system that will feel jerky and unnatural. It's a hack, and it will feel like one.

## 2. You've Hidden the State Machine, Not Removed It
The proposal boasts of simplifying the architecture by collapsing everything into a single `LocomotionSystem`. This is a sleight of hand. You haven't removed the complexity of the multi-stage movement pipeline from Proposal 1; you've just stuffed it all into one giant function. The logic still has to manage multiple states (pushing, gliding, landing), but now it's an implicit, timer-based state machine, which is famously difficult to debug. When a Yukkuri gets stuck, you won't have a clean state like "PATH_UNREACHABLE" to inspect; you'll have a `hop_timer` at `0.342` and a velocity of `(1.2, -4.5)`, and you'll have no idea why.

## 3. The `StatSyncSystem` is Pointless Middleware
The claim of "decoupling stats from physics" via a `StatSyncSystem` is architectural theater. All you've done is add a superfluous middleman. The flow of data is still `Stats -> System -> Physics`. This extra layer only introduces the potential for latency and desynchronization bugs. A tired Yukkuri might move at full speed for up to a second before the `StatSyncSystem` gets around to updating its `Locomotion` parameters. This isn't decoupling; it's just delayed, asynchronous coupling, which is strictly worse.

## 4. Pathfinding is Still an Unsolved Problem
The proposal dismisses pathfinding with a single sentence: "The `MovementRequest` is simply updated to the *next waypoint*." This completely ignores the fundamental interaction between the movement model and waypoint following. A system based on rhythmic pulses of force is inherently ill-suited for precise waypoint navigation. It will constantly overshoot and then have to clumsily correct itself, leading to a wobbly, inefficient path. The "solution" to the overshooting problem of Proposal 2 is to... ignore it.

---

# Revise

The core insight—separating the *illusion* of hopping from the *reality* of 2D movement—is correct. The implementation, however, is still trying to be too clever. Simplify further.

## 1. Embrace Kinematics. Control the Illusion.
Stop trying to simulate a "hop" with physics forces. A Yukkuri's movement across the ground should be simple, predictable, and kinematic. The AI decides on a target velocity, and the physics body is set to that velocity. This is the **ground truth** of its movement. It is easy to debug, easy to pathfind with, and gives you precise control.

The "hop" is a **purely visual effect**. It is a combination of two things:
-   **Vertical Bobbing**: The sprite's render position is offset by a sine wave based on its movement speed. Fast movement = higher, faster bobs.
-   **Horizontal Variance**: The *actual* ground speed is not constant. It should follow a curve, perhaps also a sine wave. The Yukkuri accelerates into the "hop" and decelerates at the "landing," but its *average* speed over the cycle is exactly what the AI requested.

## 2. The AI is the Conductor
The AI is the single source of truth for movement intent. There is no `LocomotionSystem` and no `StatSyncSystem`. The process is simple:
1.  The Behavior Tree (e.g., `MoveToTarget` node) runs.
2.  It looks at `YukkuriStats` (energy, weight, etc.).
3.  It calculates a `target_velocity` for this frame.
4.  It passes this `target_velocity` to a simple `MovementController` component.

The `MovementController` is not a complex state machine. Its entire job is to apply the requested velocity to the `PhysicsBody` and to update the timer for the visual bobbing effect.

```python
# In the Behavior Tree:
speed_modifier = calculate_speed_from_stats(stats)
target_velocity = (target_pos - current_pos).normalized() * max_speed * speed_modifier
get_component(entity, MovementController).set_velocity(target_velocity)

# In the MovementController's system update:
body.velocity = self.requested_velocity
self.visual_bob_timer += dt * body.velocity.length()
```

## 3. One Component to Rule Them All
Combine `MovementRequest` and `Locomotion` into a single `MovementController` component. This component holds the target velocity, the tuning parameters for the visual bob (bob height, speed variance curve), and the current state of the visual animation (the bob timer). This keeps all movement-related data in one place. An external `StatSystem` can periodically update the tuning parameters on this component if needed, but the frame-to-frame control comes directly and imperatively from the AI.

This revised approach achieves all the goals—bouncy feel, stat integration, AI-driven intent—with a fraction of the complexity. It uses the physics engine for what it's good at (collision) and handles the aesthetics in a simple, controllable, and decoupled visual layer.
