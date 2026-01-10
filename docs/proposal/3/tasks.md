# Actionable Tasks for Implementing Yukkuri Inventory System

## Core Implementation
- [ ] **Create Data Asset Structure**: Define `InventoryItem` JSON/YAML schema with fields `asset_id`, `name`, `description`, `icon_path`, `max_stack`, `effects`.
- [ ] **Add ECS Component**: Implement `InventoryComponent` that stores a list of `ItemStack` objects (`item_asset_id`, `quantity`). Include optional `capacity` and `weight_limit` fields.
- [ ] **Develop Inventory System**:
  - Implement **Pickup Logic**:
    - Serialize target Entity to data.
    - `world.delete_entity(target_id)`.
    - Add data to Inventory.
  - Implement **Drop Logic**:
    - Remove data from Inventory.
    - Spawn new Entity at player position using `EntityFactory` + data.
  - Handle `TransferItem` between inventories.
  - Implement stacking logic and weight checks.
- [ ] **Integrate Persistence**:
  - Extend existing save/load serialization to include `InventoryComponent` data.
  - Ensure items are saved as pure data (IDs/Counts), not Entity references.

## UI Development
- [ ] **Design Inventory UI Layout**: Create panels for item grid, tooltip, and action buttons.
- [ ] **Implement UI Binding**: Connect UI to the player's `InventoryComponent` via read‑only interface.
- [ ] **Add Interaction Handlers**: Support item selection, use, drop, and transfer actions.

## Item Effects System
- [ ] **Define ItemEffect Data Asset**: Structure for effects like `Heal`, `Damage`, `Buff`, etc.
- [ ] **Implement Effect Execution**: Hook into `InventorySystem` to apply effects when items are used.

## Optional Features
- [ ] **Nested Containers**: Allow items that are themselves containers (e.g., bags) with their own `InventoryComponent`.
- [ ] **Durability System**: Track item wear and trigger degradation or breakage.
- [ ] **Weight/Encumbrance**: Add weight calculations influencing movement speed.

## Testing & Validation
- [ ] **Unit Tests**: Write tests for adding/removing items, stacking, capacity limits, and persistence round‑trip.
- [ ] **Integration Tests**: Verify UI updates on inventory changes and effect application.
- [ ] **Performance Benchmark**: Ensure inventory operations stay within acceptable frame‑time budget.

---
*This task list is intended to guide the implementation of the Yukkuri Inventory system.*
