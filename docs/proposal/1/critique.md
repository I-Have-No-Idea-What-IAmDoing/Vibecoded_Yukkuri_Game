# Critique of Proposal 1: Architecture Redesign

## Summary
The proposal outlines a standard, if somewhat generic, modernization of a game engine architecture. While the goals (modularity, data-driven design) are sound, the proposal suffers from over-engineering, vagueness in implementation details, and a lack of pragmatic consideration for the existing codebase. It reads like a textbook exercise rather than a tailored solution for the specific needs of the Yukkuri Game Engine.

## Specific Criticisms

### 1. Application & Scene Management: Overkill for Current Scope?
*   **Critique**: Splitting `GameManager` into `Application`, `SceneManager`, and `Scene` is standard, but the proposal fails to justify *why* this complexity is needed *now*. Is the game actually planning to have multiple complex scenes (e.g., distinct mini-games, complex editor modes) that necessitate a stack? Or is this just "good practice" bloat?
*   **Gap**: No mention of how data persistence between scenes (e.g., inventory carrying over from a "Shop Scene" to a "Gameplay Scene") is handled. A scene stack is useless if you can't share state effectively.
*   **Harsh Reality**: You're adding three layers of indirection. Show me the concrete use case or stick to a simpler state machine.

### 2. Enhanced Event System: The "Call Stack Explosion" Boogeyman
*   **Critique**: The fear of "call stack explosion" and "infinite loops" is often a sign of bad system design, not a lack of event queuing. Introducing a queued event system adds non-determinism (events happening "later") which makes debugging a nightmare.
*   **Gap**: The proposal mentions "Prioritized Listeners" but doesn't explain how conflicts are resolved. If two systems want to consume the same event, who wins?
*   **Harsh Reality**: "Immediate vs Queued" is a recipe for race conditions. Pick one (preferably immediate for simplicity, or strictly phase-based) and stick to it. Don't build a generic message bus when a direct function call or a simple observer pattern would suffice.

### 3. Input Abstraction: Configuration Hell
*   **Critique**: "ActionMapper" sounds nice until you have to maintain a massive mapping file. The proposal waves hands at "YAML/TOML" without defining the schema.
*   **Gap**: How does this handle analog inputs vs digital inputs? How does it handle context-sensitive inputs (e.g., "A" means Jump in game, but "Select" in menu)? A global `ActionMapper` usually falls apart with UI interaction.
*   **Harsh Reality**: You are solving a problem (remapping) before proving it's a priority. Just wrapping `is_key_pressed` in `is_action_pressed` is a facade, not an abstraction, unless you handle the context switching complexity.

### 4. Data-Driven Entity Factory: The Performance Trap
*   **Critique**: Loading entities from YAML/TOML at runtime (or even parsing at startup) can be slow and error-prone. "Strings as types" (e.g., `create_entity("yukkuri_baby")`) destroys compile-time/lint-time safety.
*   **Gap**: No mention of component data validation. What happens if a typo in YAML breaks the game?
*   **Harsh Reality**: You're trading code clarity for "moddability" that no one asked for yet. Unless you have a schema validator, you're just moving bugs from Python to YAML.

### 5. Strict ECS Separation: Dogma over Pragmatism
*   **Critique**: "Components: Pure data classes. No logic." is ECS dogma that often leads to "System Spaghetti" where systems have to know too much about the internal structure of data. Helper methods on components (e.g., `vec.add()`) are often necessary and fine.
*   **Gap**: "Stateless systems" is a lie. Systems need to track time, cache queries, etc. Where does *that* state go? "Resources" is just a fancy name for Globals.
*   **Harsh Reality**: Blindly following "Strict ECS" often results in unreadable code where logic is scattered across 5 systems to do one simple thing like "Move and Play Sound".

### 6. Service Architecture: Global State with Extra Steps
*   **Critique**: A `ServiceContainer` is just a Service Locator, which is a well-known anti-pattern if misused. It hides dependencies.
*   **Gap**: Why not just pass dependencies in the constructor?
*   **Harsh Reality**: You're replacing `import Global` with `Container.get(Global)`. It's the same coupling, just harder to statically analyze.

## Conclusion
This proposal is a classic case of "Second System Effect". It proposes a Grand Rewrite™ that adds massive complexity for theoretical benefits.
**Recommendation**:
1.  Scrap the generic "Event Manager" and use specific, typed events where needed.
2.  Drop the "Scene Stack" unless you have >2 scenes implemented *now*.
3.  Implement Prefabs *only* for the most common entities first, and stick to a strict schema.
4.  Don't ban logic in components if it simplifies usage (e.g. getters/setters/helpers).

**Verdict**: REVISE HEAVILY. Focus on concrete problems, not architectural purity.
