# Critique: Force-Based Hopping Movement System (Proposal 2)

## 1. Feature Creep & Z-Axis Hell
Adding a simulated Z-axis to a 2D top-down physics engine is a rookie mistake. You are inviting a world of pain regarding depth sorting, collision detection (can I hop over a rock? If so, why did I collide with the wall behind it?), and visual disparities. Pymunk is a 2D engine. Fighting it to fake 3D height usually results in glitchy physics where entities get stuck in "walls" they supposedly jumped over.

## 2. Gameplay Annoyance
"Hopping" sounds cute on paper but is often infuriating in practice. If a Yukkuri moves in discrete impulses, it becomes imprecise.
- **Overshooting**: AI will constantly overshoot targets because it's locked into a ballistic trajectory mid-hop.
- **Micro-management**: Trying to interact with a moving object that is bouncing up and down is frustrating for the player (clicking on a moving target).
- **Stuttery Visuals**: Unless the framerate and interpolation are perfect, rapid hopping can look like jitter.

## 3. Tightly Coupled Mess
You are tightly coupling the physics movement logic to `YukkuriStats`.
- `Agility`, `Health`, `Athleticism`, `Weight`, `Fullness`.
This makes the movement system completely non-reusable. If you ever want to add a simple bouncy ball toy, or a predator that *doesn't* have "Fullness," you can't use this system. You've hardcoded game mechanics into the physics simulation layer.

## 4. Physics Hacks
"Manual Euler integration for z" inside a `PhysicsSystem` that otherwise uses Pymunk's sophisticated solver is gross. You are mixing two different simulation models. Pymunk handles the X/Y collisions, but your manual hack handles Z gravity? When a Yukkuri "lands" (Z=0), you apply friction. But Pymunk applies friction *all the time* if shapes are touching. You'll be fighting the engine's built-in friction constantly to make the "Airborne" phase work.

## 5. Over-reliance on "Juice"
This proposal prioritizes "Squash & Stretch" and "Dust Particles" (visual polish) over robust pathfinding and collision avoidance. A "bouncy" character that constantly gets stuck on corners or vibrates against walls because of physics conflicts isn't "juicy," it's broken.

## Summary
The "Hopping" idea is good for flavor but terrible as a fundamental physics implementation. Don't fight the 2D physics engine. Don't bake RPG stats into the collision solver.
