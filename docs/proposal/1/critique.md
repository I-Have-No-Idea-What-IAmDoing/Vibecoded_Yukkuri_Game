# Critique of Data Persistence Proposal

## Section 7: Description of data persistence between scenes

This section is woefully inadequate and demonstrates a naive understanding of state management in complex applications.

1.  **Architecture by Wishful Thinking**: Defining a "GameSession" object solves nothing. It's just a fancy name for a Global Variable bucket. You haven't defined what this object looks like, how it's structured, or how it ensures data integrity. It's a "God Object" in training.

2.  **The Synchronization Nightmare**: The proposal suggests separating "Volatile level state" (ECS) and "Persistent state" (Session). This is a recipe for disaster.
    - If the Player entity has an Inventory Component, and the Session has an Inventory list, **which is the source of truth?**
    - Do systems update the Component or the Session?
    - If they update the Component, when does it get flushed to the Session? On Scene exit? What if the game crashes?
    - If they update the Session directly, why does the Component exist? You are violating ECS principles by forcing Systems to reach out to a global blob instead of local data.

3.  **Ambiguity is Failure**: "Passed to Scenes... OR accessible via ServiceContainer". Make a decision!
    - If it's passed, you pollute the constructor of every Scene.
    - If it's in the ServiceContainer, you've created a hidden dependency that makes testing a nightmare. "Service Locator" is an anti-pattern when used for application state.

4.  **Serialization Hand-Waving**: "Primary target for Save/Load operations" is not a design. It's a wish.
    - How do you handle schema migration when the `GameSession` structure changes?
    - What format? JSON? Pickle?
    - How do you handle circular references or non-serializable objects that might sneak into this "Session"?

5.  **Testing Impossibility**: How do you unit test a System that depends on `GameSession`? You have to mock the entire session state. By coupling game logic to a global persistence context, you are making the engine rigid and fragile.

**Recommendation**: Stop treating persistence as a "bucket of globals". Treat it as a transformation of state. Define clear contracts for how data enters and leaves the ECS world.
