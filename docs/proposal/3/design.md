# Yukkuri Inventory System Design

## Overview
The Yukkuri Inventory system will provide a flexible, data‑driven way for entities (players, NPCs, containers) to hold and manage items. It will be built on top of the existing ECS architecture, leveraging components and systems to keep logic decoupled from rendering.

## Goals & Rationale
- **Scalability** – Support an arbitrary number of item types without hard‑coding limits.
- **Extensibility** – New item behaviours (e.g., consumables, equipable gear) can be added by defining data assets rather than code changes.
- **Persistence** – Inventory state must survive save/load cycles and be serializable for networking.
- **UI Integration** – Provide a clear UI for players to view, select, and use items.
- **Performance** – Keep per‑frame overhead low; most operations are event‑driven.

## High‑Level Architecture
1. **InventoryItem (Data Asset)** – Defines static properties such as name, description, icon, stack size, and any special effects. JSON/YAML files (e.g., `data/items/potion.json`).
2. **InventoryComponent (ECS Component)** – Holds a list of `ItemStack` objects attached to an entity.
    - `ItemStack`: Struct containing `item_asset_id` (string) and `quantity` (int).
3. **InventorySystem (ECS System)** – Handles adding/removing items, stacking logic, transfer between inventories.
4. **Lifecycle Manager**:
    - **Pickup**: Converts World Entity -> Serialized Data -> `ItemStack`. Destroys World Entity.
    - **Drop**: Converts `ItemStack` -> Serialized Data -> Spawns new World Entity.
5. **UI Layer** – A set of screens/panels that read the `InventoryComponent`.
6. **Persistence Integration** – Serializes `InventoryComponent` as simple JSON data (list of IDs and counts).

## Interaction Flow Example
1. Player picks up a `Health Potion` (EntityID: 101).
2. `InventorySystem` receives a `PickupEvent(entity_id=101)`.
3. System extracts data from Entity 101 (Asset ID: "potion_health", Durability: 100%).
4. System **destroys** Entity 101.
5. System adds `ItemStack(item_asset_id="potion_health", count=1)` to Player's Inventory.
6. System emits `ItemAdded` and `InventoryChanged`.
7. UI listens for `InventoryChanged` and refreshes.
8. Player selects potion and activates `UseItem`.
9. `InventorySystem` applies effects and decrements stack.

## Integration with Carrier System (Proposal 2)
This system (Inventory/Storage) complements the Carrier System (Holding):
-   **Carrier System**: For items physically held in hands/mouth (Active, Visible).
-   **Inventory System**: For items stored in pockets/bags (Passive, Hidden).
-   **Transfer**: Items can be moved from `CarrierComponent` to `InventoryComponent` (Store) or vice versa (Equip).

## Open Questions
- Should we support nested containers (e.g., bags inside inventory)?
- How to handle items with unique dynamic data (e.g., written notes) inside stacks? (Likely require non-stackable unique items).
- Will there be a global item registry or per‑scene loading?

---
*Prepared as a design proposal for the Yukkuri Inventory system.*
