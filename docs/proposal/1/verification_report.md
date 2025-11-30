# Verification of Architecture Proposal (v4)

## Summary
The proposal in `design.md` significantly improves upon previous iterations by addressing concerns regarding boilerplate, schema migration, and type safety. However, critical gaps remain regarding **Entity Reference Integrity**, **Dynamic World Persistence**, and **System Coupling**.

## Soundness and Validity Checks

### 1. Entity Reference Integrity (Major Gap)
The proposal describes saving components (e.g., `Inventory`) but does not address how to preserve relationships between entities.
*   **Problem**: If an entity has a component `Owner(target_entity_id=123)` and we save/load, the entity IDs will likely change upon recreation. The reference `123` will point to nothing or the wrong entity.
*   **Impact**: Any system relying on entity relationships (AI targets, ownership, parenting, aggro lists) will break after a save/load cycle.
*   **Recommendation**: The persistence system must include an ID remapping mechanism or stable UUIDs for persistent entities.

### 2. Dynamic World Persistence (Major Gap)
The `Scene.EXPORTS` mechanism relies on explicit, static keys (e.g., `keys.player.INVENTORY`).
*   **Problem**: This works for singletons (Player) but fails for dynamic collections. How do we save "all 50 enemies currently alive"? We cannot assign a unique static key to each dynamically spawned enemy in `EXPORTS`.
*   **Impact**: The current design can only save "Game State" (global flags, player stats) but cannot save "Level State" (positions of dynamic entities).
*   **Recommendation**: Introduce a `WorldSerializer` or a specific strategy for serializing collections of entities, distinct from the dependency injection used for the Player.

### 3. System Coupling "Direct Observers" (Minor Concern)
The advice to use "Direct Observers" or "system-to-system communication" is risky.
*   **Problem**: "System A calls System B directly" creates hard dependencies. If System B is removed or replaced, System A breaks.
*   **Impact**: Reduces modularity and testability.
*   **Recommendation**: Clarify that "Direct Observers" should still ideally be decoupled (e.g., via C# style Events/Delegates or explicit callback registration interfaces) rather than hard references.

## Conclusion
The proposal is valid for *State Transfer* (moving player data between levels) but **unsound** for *Full Persistence* (saving the exact state of a level). It requires revision to address Entity IDs and Dynamic Collections.
