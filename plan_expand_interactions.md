# Plan: Content - Expand Interactions

## 1. Define New Actions
*   **Target File**: `data/ai/actions.toml`
*   **Action**: Add new action definitions.
*   **Details**:
    *   `[actions.Talk]`: High happiness gain, low cost. Requires another Yukkuri.
    *   `[actions.Fight]`: Negative happiness, health loss. Triggered by low compatibility or high stress (need to define considerations).
    *   `[actions.Dance]`: Group activity. High fun.

## 2. Update Behavior Registry
*   **Target File**: `src/yukkuri_game/game/ai/behavior.py`
*   **Action**: Implement behavior builders for new actions.
*   **Details**:
    *   `build_talk_behavior`: Find another Yukkuri -> Move To -> Interact (Talk).
    *   `build_fight_behavior`: Find target (enemy?) -> Move To -> Interact (Attack).
    *   `build_dance_behavior`: Find spot/partner -> Move To -> Interact (Dance).
    *   Register these using `BehaviorRegistry.register_goal`.

## 3. Implement Social Interaction Logic
*   **Target File**: `src/yukkuri_game/game/services.py` (GameService) or `src/yukkuri_game/game/systems/interaction.py`
*   **Action**: Add `interact_with_entity(initiator_id, target_id, interaction_type)` method.
*   **Details**:
    *   **Talk**: Increase happiness for both `initiator` and `target`.
    *   **Fight**: Decrease health/happiness for both.
    *   **Dance**: Increase happiness/energy for both.
    *   Ensure mutual interaction (if A talks to B, B also receives effect).

## 4. Update Find Logic for Entities
*   **Target File**: `src/yukkuri_game/game/ai/behavior.py` (FindItem or new FindEntity)
*   **Action**: Create `FindEntity` action node.
*   **Details**:
    *   Similar to `FindItem` but searches for `YukkuriStats` instead of `ItemStats`.
    *   Filters: `ignore_self=True`.
    *   Criteria: Random, Closest, or Specific (e.g., low relationship? - Relationships not implemented yet, so maybe random for now).

## 5. AI Considerations
*   **Target File**: `src/yukkuri_game/game/ai/utility.py`
*   **Action**: Ensure `UtilityAIEngine` can parse new considerations.
*   **Details**:
    *   Add `Social` need (can use `happiness` as proxy for now).
    *   Or add `Loneliness` if we add that stat.

## 6. Pre-commit Steps
*   **Action**: proper testing, verification, review, and reflection.
*   **Details**: Verify new actions appear in the behavior tree. Verify interactions trigger correctly.
