# Implementation Plan: Data-Driven Inventory System

## Objective
Implement a robust, scalable, and data-driven inventory system for Yukkuri Raising Game using the existing Entity-Component-System (ECS) architecture. This system will allow entities (players, containers) to store, stack, and use items defined in external data files.

## Technical Solutions Research

### Solution A: Pure Data Component (Recommended)
**Concept**:
-   **Architecture**: `InventoryComponent` stores a list of simple data structures (`ItemStack`).
-   **Item Definition**: Items are defined as static assets (`ItemType` from `data_models.py`) loaded from TOML.
-   **Persistence**: `WorldSerializer` natively handles `msgspec` structs, making save/load straightforward.
-   **Entity Interaction**: Picking up an item destroys the World Entity and creates an `ItemStack`. Dropping it creates a new World Entity from the `ItemStack`.

**Pros**:
-   **Performance**: Minimal overhead. Thousands of items in inventory = thousands of small structs, not thousands of Entities (which have overhead).
-   **Architecture Fit**: Aligns perfectly with existing `ResourceManager`, `EntityFactory`, and `WorldSerializer`.
-   **Simplicity**: Easy to traverse for UI rendering.

**Cons**:
-   **Unique Data**: Harder to handle items with unique state (e.g., a "half-eaten" apple or a named sword) without extending the `ItemStack` schema significantly.

### Solution B: Entity Container ("Everything is an Entity")
**Concept**:
-   **Architecture**: `InventoryComponent` stores a list of `EntityID`s.
-   **Item Definition**: Items remain as Entities but are "disabled" (removed from rendering/physics systems) while in inventory.
-   **Persistence**: Nested entity serialization.

**Pros**:
-   **Flexibility**: Retains all dynamic components of an item (e.g., `DecayComponent` on food could continue running if systems allow).
-   **State**: Trivially handles unique item states (damage, modifications).

**Cons**:
-   **Complexity**: Managing "active" vs "inactive" states for entities is error-prone.
-   **Overhead**: High memory and processing cost for large inventories.
-   **Persistence Risk**: Reference resolution for entities "inside" other entities can be tricky with the current 2-pass loader.

### Solution C: Hybrid Slot System
**Concept**:
-   Variation of Solution A where `InventoryComponent` enforces a grid/slot structure (e.g., `FixedSizeInventory`).
-   **Pros**: Explicitly models limited space (Tetris inventory or simple slots).
-   **Cons**: Additional logic for "fitting" items.

## Ranking
1.  **Solution A (Pure Data Variant)** - **Selected**: Best fit for current codebase, high performance, low risk.
2.  **Solution C (Hybrid)** - Good for specific gameplay needs, but can be built *on top* of Solution A.
3.  **Solution B (Entity Container)** - Rejected due to unnecessary complexity and performance overhead for this genre.

---

## MVP Implementation Plan

### 1. Data Model Refinement
**Goal**: Update `ItemType` to support inventory features.
-   [ ] Modify `src/yukkuri_game/engine/data_models.py`:
    -   Add `stack_size: int = 1` to `ItemType`.
    -   Add `description: str = ""` to `ItemType`.
    -   Add `category: str = "misc"` (optional) for sorting.

### 2. Component Implementation
**Goal**: Create the storage component.
-   [ ] Create `src/yukkuri_game/game/components/inventory.py` (or add to `yukkuri_components.py`):
    -   Define `ItemStack` (msgspec.Struct):
        -   `item_type_id: str`
        -   `quantity: int`
        -   `custom_data: Dict[str, Any]` (for future extensibility)
    -   Define `InventoryComponent`:
        -   `capacity: int`
        -   `items: List[ItemStack]`
        -   Methods: `can_add(item_id, count)`, `add(item_id, count)`, `remove(item_id, count)`, `has(item_id, count)`.

### 3. System Implementation
**Goal**: Logic for transferring items between World <-> Inventory.
-   [ ] Create `src/yukkuri_game/game/systems/inventory_system.py`:
    -   **Pickup Logic**: Listen for `InteractionEvent` (or similar trigger).
    -   Find target entity -> Get `ItemComponent` -> Resolve `type_id`.
    -   Add to invalidating entity's `InventoryComponent`.
    -   Destroy world entity.
    -   **Drop Logic**:
        -   Remove from `InventoryComponent`.
        -   Call `EntityFactory.create_item(type_id, ...)` at dropper's position.

### 4. UI Integration (MVP)
**Goal**: Visualize contents.
-   [ ] Create toggleable `InventoryWindow` using `pygame_gui`.
-   [ ] Listen for `InventoryChangedEvent` to rebuild UI lists.

### 5. Persistence
**Goal**: Ensure inventories save/load.
-   [ ] Verify `InventoryComponent` is registered in `loader.py`.
-   [ ] Verify `WorldSerializer` handles the `List[ItemStack]` correctly (it should given `msgspec` support).

## Verification Steps
1.  **Test**: Spawn Item -> Pickup -> Verify Entity Destroyed -> Verify Inventory Count 1.
2.  **Test**: Drop Item -> Verify Inventory Count 0 -> Verify Entity Spawns.
3.  **Test**: Pickup 2nd stackable item -> Verify Inventory Count 2 (not 2 slots).
4.  **Test**: Save Game -> Restart -> Load Game -> Verify Inventory contents.
