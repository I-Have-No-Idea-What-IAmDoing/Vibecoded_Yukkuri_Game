# Critique of Data Persistence Proposal (Manifest & Protocol)

## Section 7: Data Persistence & State Transfer

The revised proposal's Section 7 attempts to solve the "Global State" and "DTO" problems but inadvertently creates a bug-prone, non-scalable, and rigid architecture. It trades "Boilerplate" for "Human Error" and "Architectural Dead-Ends."

1.  **The "Manual Dirty Flag" Disaster**:
    - The proposal explicitly states: *"When a relevant component changes... it marks itself as `dirty`."*
    - This relies on **100% developer discipline**. Every single time a developer writes `inventory.gold += 10`, they **MUST** remember to write `inventory.dirty = True`.
    - If they forget once? The player loses progress, bugs are untraceable, and QA will spend weeks chasing "sometimes the gold doesn't save."
    - This is not "Zero Boilerplate"; this is **Invisible Boilerplate** that crashes your game logic when omitted. It is the definition of fragile code.

2.  **The "Singleton" Fallacy (Manifests)**:
    - The Manifest system uses `SessionKey` enums like `PLAYER_INVENTORY` or `DUNGEON_FLAGS`.
    - **This only works for singletons.** What happens when we have 100 persistent treasure chests? Do we create `CHEST_1`, `CHEST_2`... `CHEST_100` in the Enum?
    - The design fails to distinguish between **Global Session State** (Story flags, Player stats) and **World State** (Entities, positions, states of dynamic objects).
    - By forcing everything through a `SessionKey` map, you have effectively created a system that cannot handle a dynamic world. You can save Link, but you can't save the Pots he broke unless you manually define a Key for every pot in existence.

3.  **Versioning & Coupling Nightmare**:
    - The proposal mandates: *"Components... should inherit from `msgspec.Struct`."*
    - You have now married your **Runtime Memory Layout** to your **Disk Storage Format**.
    - What happens when you change `float health` to `int health` in your game logic? Your save files are now corrupted/incompatible.
    - Because the Component *is* the serialization schema, you cannot refactor your code without breaking every user's save file. You need an explicit separation or a robust migration layer, which is conspicuously absent.

4.  **Ambiguous Ownership & Race Conditions**:
    - "The `SceneManager`... injects this data."
    - What if two Scenes are active (Stacked Scenes, e.g., Inventory UI over Gameplay)? Do they share the same `msgspec` instance?
    - If they share it, who owns the "Dirty" flag? If the UI clears the dirty flag after a partial save, does the Gameplay scene know?
    - The proposal treats data as "Blobs passed around" rather than "State managed by an owner," leading to potential desyncs where the UI shows 50 gold but the backend has already saved 40.

**Conclusion**: The "Manifest & Protocol" model is a naive optimization that introduces manual error vectors (dirty flags), fails to scale to world-state (singleton keys), and locks the codebase into a rigid serialization format (inheritance coupling). It is functional only for the simplest of arcade games, not a scalable engine.
