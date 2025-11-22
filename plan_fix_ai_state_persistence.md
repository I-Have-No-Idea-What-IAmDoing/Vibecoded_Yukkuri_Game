# Plan: Fix AI State Persistence

This plan addresses the issue where `AIState` is lost during save/load, causing entity "amnesia".

## 1. Update `PersistenceService.save_game`

- File: `src/yukkuri_game/game/services.py`
- Import `AIState`.
- In the entity loop, check for `AIState` component.
- If present, serialize:
    - `current_action` (str)
    - `current_target_id` (int)
    - `state_data` (dict)
    - `path` (list of tuples) - *Optional, but good for continuity*.
- Add this data to the entity dictionary under a new key, e.g., `"ai_state"`.

## 2. Update `PersistenceService.load_game`

- File: `src/yukkuri_game/game/services.py`
- In the entity creation loop, check for `"ai_state"` key in data.
- If present:
    - Get `AIState` component from the created entity (factory should have added it).
    - If not present, add it (factory might not add it for all types, but should for Yukkuris).
    - Restore:
        - `current_action`
        - `current_target_id`
        - `state_data`
        - `path` (if saved)

## 3. Handle ID Mapping (Crucial)
- *Problem*: `current_target_id` refers to an entity ID in the *old* session. In the new session, entities get new IDs.
- *Solution*:
    - Save Phase: Save `current_target_id`. Also, we usually save entities in a list. We might need a stable ID or rely on index? ECS IDs are transient.
    - *Better Solution*: Use a temporary "save ID" map.
        - Assign a unique index/ID to each entity being saved (0 to N).
        - When saving `current_target_id`, save the *index* of that target entity in the saved list.
        - When loading, build a map `saved_index -> new_entity_id`.
        - After creating all entities, perform a second pass to resolve `current_target_id` using the map.
- *Revised Plan for Step 1 & 2*:
    1.  **Save**:
        - First, map all valid Entity IDs to a sequential "SaveID" (0, 1, 2...).
        - Save entities using this SaveID (or just list order).
        - When saving `AIState.current_target_id`, look up its SaveID. If found, save it. If not (target not being saved), save -1.
    2.  **Load**:
        - Keep a list/map of `SaveID -> NewEntityID`.
        - First pass: Create all entities. Store `NewEntityID` in the map at index `SaveID`.
        - Second pass: Iterate over all created entities. If they have pending AI state with a target SaveID, resolve it to `NewEntityID` and set `current_target_id`.

## 4. Verification
- Create a test case `tests/test_persistence_ai.py`.
- Setup: Create Yukkuri, Create Item. Set Yukkuri target to Item.
- Save.
- Clear World.
- Load.
- Assert: Yukkuri exists, Item exists. Yukkuri `current_target_id` matches the new ID of the Item.

## 5. Pre-commit
- Ensure proper testing, verification, review, and reflection are done.
