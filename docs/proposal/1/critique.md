# Critique: Yukkuri Movement System Overhaul (Proposal 1)

This proposal is a textbook example of architectural over-engineering, a solution in search of a problem. It prioritizes dogmatic adherence to ECS "purity" over practical, maintainable, and—most importantly—*fun* game development. It is a blueprint for turning a simple problem into a complex one, guaranteeing weeks of development for zero net gain in gameplay quality.

## 1. You Are Not Building a AAA RTS Engine
The core sin of this proposal is mistaking the project's scale. You are building a pet simulator, not StarCraft III. Decomposing a single, clear action ("move to X") into a five-stage pipeline (`AI -> MovementRequest -> NavigationSystem -> Path -> SteeringSystem -> Physics`) is laughably overwrought. This isn't "separation of concerns"; it's the violent fragmentation of a single, cohesive idea. The "god object" `MoveToTarget` you so despise is, in fact, a feature. It places all the relevant logic in one location, making it easy to understand and debug. This proposal scatters that logic across half a dozen files, ensuring that no developer will ever be able to hold the entire movement process in their head at once.

## 2. A Vow of Boredom
The proposal proudly champions generic, reusable steering behaviors like "Seek" and "Arrive." These are the most boring, sterile, floaty movement algorithms imaginable. They produce movement that feels like a physics tutorial, not a living creature. By abstracting the *how* of movement away from the *what*, you actively prevent the implementation of unique, character-specific motion. Yukkuris shouldn't glide like air hockey pucks; they should waddle, stumble, and hop. This design makes expressing that character—the very soul of the game—more difficult, not less, because any such quirk would violate the clean separation of the "SteeringSystem." You're proposing to build a system that is reusable for projectiles and pet creatures, which means it will be good for neither.

## 3. The Debugging Nightmare You're Creating for Yourself
The claim that this will be easier to debug is patently false. You are trading a single, inspectable call stack within the `MoveToTarget` method for a distributed, asynchronous state machine spread across multiple components and systems. Good luck figuring out why a Yukkuri stopped moving. Is it because the AI failed to create a `MovementRequest`? Or the `NavigationSystem` couldn't find a path and silently failed? Or the `SteeringSystem` got stuck in a local minimum but the `Path` status was never updated to "stuck"? You are creating a state-synchronization hellscape that will require a dedicated ECS debugger just to untangle.

## 4. Solving a Non-Problem While Ignoring the Real One
The proposal obsesses over code organization but fails to ask the most important question: **is the current movement any good?** Does it look and feel alive? This entire document proposes a massive, high-risk refactoring that, if successful, will result in movement that is functionally identical to the old system. It delivers zero user-facing value. It is a solution for a developer's OCD, not a player's experience.

---

# Revise

The impulse to refactor a "god object" is correct, but the execution is flawed. The goal should be to improve clarity and quality, not to chase architectural purity.

## 1. Refactor, Don't Re-architect
Instead of blowing up the architecture, refactor `MoveToTarget` into a more focused `MovementController` component. This component is a stateful object responsible for the *execution* of movement, but it is not a disconnected, asynchronous system. It's a concrete object that the AI can directly command.

```python
# In your behavior tree node:
movement_controller = get_component(entity, MovementController)
movement_controller.move_to(target_position)

# The controller handles the details:
class MovementController:
    def move_to(self, target):
        self.path = self._pathfinder.find_path(self.position, target)
        # ... and so on

    def update(self, dt):
        # Follow path, apply steering, handle physics
        # ...
```

## 2. Embrace Character, Not Generics
The `MovementController` should be a base class. Create a `YukkuriMovementController` that inherits from it. This is where you implement the waddling, the stumbling over small obstacles, and the unique animations. This approach embraces the specific needs of the character, rather than trying to fit it into a sterile, one-size-fits-all "Steering System." The code for how a Yukkuri moves belongs with the Yukkuri, not in a generic system shared with hypothetical projectiles.

## 3. AI Stays in Control
The AI should have direct, imperative control over the `MovementController`. If a behavior needs to make a sudden stop, it calls `movement_controller.stop()`. If it needs to jump, it calls `movement_controller.jump()`. This is simple, predictable, and easy to debug. The "fire-and-forget" `MovementRequest` pipeline introduces latency and makes these kinds of reactive, nuanced behaviors incredibly difficult to implement.

## 4. Focus on Quality First
Before embarking on this refactoring, make the movement *better*. Implement the waddle. Add animation blending. Make the Yukkuris feel weighty and alive. Once you have code that produces a high-quality result, *then* you can refactor that working code for clarity. Don't refactor for a hypothetical future; build what's good for the player now.
