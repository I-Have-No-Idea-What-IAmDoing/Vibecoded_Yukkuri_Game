# Critique of Proposal 3

## Core Strengths
This proposal correctly identifies the need for a **Data-Driven** approach (Asset-based items) rather than Entity Persistence. This solves the scalability issues found in Proposal 1.

## Areas for Improvement

### 1. Entity <-> Data Lifecycle
The proposal mentions "Player picks up a Health Potion" but doesn't technicaly specify the transition.
-   **Requirement**: Explicitly state that the World Entity is **destroyed** on pickup and a **new** World Entity is spawned on drop.
-   **Data Preservation**: Ensure that dynamic data (e.g., durability, freshness) is extracted from the Entity components into the `ItemStack` data before destruction.

### 2. ID Disambiguation
-   **Ambiguity**: The term `item_id` in `ItemStack` could be confused with `EntityID`.
-   **Clarification**: Rename to `item_asset_id` or `prototype_id` to make it clear this refers to the static Data Asset (JSON/YAML), not an active ECS entity.

### 3. Integration with Carrier System (Proposal 2)
-   **Differentiation**: Clarify that this system is for **Storage** (hiding items, stacking). Proposal 2 covers **Carrying** (holding items visible in hands).
-   **Interoperability**: A Yukkuri might "Carry" an item (Proposal 2) and then put it into a "Bag" (Proposal 3). The system should support transferring data between `CarrierComponent` (Entity/Mount) and `InventoryComponent` (Data/Storage).

## Recommendation
Enhance the design to explicit detail the `Pickup -> Serialize -> Destroy` and `Drop -> Spawn -> Deserialize` loop.
