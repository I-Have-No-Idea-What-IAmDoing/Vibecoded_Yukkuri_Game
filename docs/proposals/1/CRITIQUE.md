# Critique of Proposal 1: "Shape Grafting" & Pymunk Abuse

This proposal attempts to solve a simple problem—stacking entities—by over-engineering a solution that fights the physics engine at every turn. It is a textbook example of "complexity addiction" over pragmatic game design.

## 1. Architectural Insanity

### The "Grafting" Mechanic is a Liability
The core idea of dynamically destroying bodies, creating new shapes, and welding them to a parent body at runtime is a maintenance nightmare waiting to happen.
*   **Memory Leaks:** Constantly creating and destroying Pymunk bodies/shapes is error-prone. One missed reference or uncleaned pointer will lead to memory leaks or segfaults.
*   **ID Drift:** Entity IDs and Physics IDs will inevitably desync. Managing the mapping between ECS entities and their "grafted" physics representation requires a complex lookup table that will be brittle.
*   **State Loss:** When you destroy the Rider's body to graft it, you lose its accumulated state (velocity, accumulated forces, contact history). When you reconstruction it, you are effectively spawning a new entity.

### Visual Desync
The proposal admits that "Syncing visual transforms manually" is a con, but understates the issue.
*   **Jitter:** Updating visual transforms based on a physics body that has a constantly changing center-of-mass (due to riders being added/removed) will result in visual popping and jitter.
*   **Interpolation Hell:** Good luck interpolating movement for rendering when the underlying physics object is being swapped out.

## 2. Gameplay & Design Flaws

### "Input vs Knockback" is Overkill
While separating input velocity from knockback is a sound concept, building an entire custom physics controller around it for a top-down sprite game is excessive.
*   **Friction Fighting:** Pymunk already handles friction. Trying to override velocity every frame while also wanting "physics interactions" leads to weird behaviors where characters slide on ice but stop instantly on grass, but then get launched into orbit by a collision.
*   **Edge Case Explosion:** What happens if a rider is mounted, the parent hits a wall, and the "grafted" shape of the rider clips into the wall? The physics solver will violently eject the entire stack, likely phasing them through geometry.

### The "Orphan" Problem
The solution for when a parent dies ("Iterate backwards... trigger Dismount") is fragile.
*   **Race Conditions:** If the parent dies in the middle of a physics step, and you try to spawn the child's body in the same step, Pymunk might lock the space.
*   **Overlap Instakill:** If you spawn the child exactly where the parent was, they might instantly collide with the thing that killed the parent, taking unfair damage or getting stuck.

## 3. Conclusion

This proposal is **rejected**. It tries to turn Pymunk into something it isn't (a compound sprite system) and introduces high-risk complexity (dynamic body reconstruction) for a low-value feature (stacking). The "Grafting" metaphor is clever but practically disastrous.
