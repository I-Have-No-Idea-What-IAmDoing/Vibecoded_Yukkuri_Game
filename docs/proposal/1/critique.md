# Critique: Yukkuri Movement System Overhaul (Proposal 1)

## 1. Architectural Astronauting
This proposal reeks of "ECS purity" at the expense of pragmatism. You are proposing to triple the number of systems and components involved in moving a blob from A to B. Introducing `MovementRequest`, `Path`, `SteeringAgent`, `NavigationSystem`, and `SteeringSystem` to replace one "god object" is classic over-engineering. You aren't building an RTS with thousands of units; you're building a pet simulation. The "god object" `MoveToTarget` likely fits the entire cognitive load of the movement logic in one screen, which is *better* for maintenance than jumping between four different files to understand why a unit stopped moving.

## 2. Generic != Good
The proposal claims "Steering Behaviors" (Seek, Arrive, Wander) as a benefit. These are standard, boring, floaty movement algorithms found in every Unity tutorial. They result in agents that feel like hovercrafts, not living creatures. By abstracting the movement into a generic `SteeringSystem`, you are actively preventing the implementation of character-specific movement quirks (like the waddle or hop of a Yukkuri) because the system is designed to be "reusable for projectiles." Why would a projectile need to "Seek" or "Wander" using the same logic as a biological entity?

## 3. The Performance Fallacy
"Esper is fast" is a hand-wavy dismissal of the fact that you are adding component thrashing. Creating and destroying `MovementRequest` or `Path` components, or even just iterating over disjoint memory for every single entity every frame, adds up. Splitting logic into multiple systems increases the cache miss rate. While premature optimization is the root of all evil, premature abstraction is the root of all spaghetti code.

## 4. Missing the Point
The "Problem Statement" complains about code organization (`MoveToTarget` is a god object), but fails to address the actual *quality* of the movement. Does the current system handle collisions well? Does it look good? This proposal effectively says, "The movement will look exactly the same (boring), but the code will be spread out over 10 files instead of 1." That is a net loss in productivity.

## 5. Implementation Nightmare
Syncing `MovementRequest` (AI intent), `Path` (Navigation state), `VelocityRequest` (Steering output), and `PhysicsBody` (Pymunk state) is a recipe for state desynchronization bugs. What happens when the Physics engine resolves a collision that the Navigation system didn't account for? You'll spend weeks debugging race conditions between your "clean" systems.

## Summary
Refactor the `MoveToTarget` class if it's too big, but don't explode the architecture into fragments just to satisfy a textbook definition of ECS.
