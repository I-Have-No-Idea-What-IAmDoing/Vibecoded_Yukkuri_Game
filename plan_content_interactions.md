# Content: Expand Interactions

## 1. Overview
This plan adds social interactions between Yukkuris: "Talk", "Fight", and "Dance". It introduces new AI behaviors and expands the `UtilitySelector` to handle these social goals.

## 2. Data Model Changes
*   **File**: `src/yukkuri_game/game/yukkuri_components.py`
    *   **Action**: Ensure `YukkuriStats` has `type_id` (already exists) to determine compatibility for Fighting vs Talking.

## 3. AI Behavior System Updates
*   **File**: `src/yukkuri_game/game/ai/utility.py`
    *   **Action**: Add new utility scorers:
        *   `SocialNeedScorer` (based on loneliness/happiness).
        *   `AggressionScorer` (based on stress/low happiness/incompatible types nearby).
        *   `GroupActivityScorer` (random chance or scheduled).

*   **File**: `src/yukkuri_game/game/ai/utility_selector.py`
    *   **Action**: Register new actions: "Talk", "Fight", "Dance".

*   **File**: `src/yukkuri_game/game/ai/behavior.py`
    *   **Action**: Implement `SocialInteract` Action node.
        *   Similar to `Interact` but for entities.
    *   **Action**: Implement `FindSocialTarget` Action node.
        *   Finds nearby Yukkuri.
    *   **Action**: Implement behavior trees for:
        *   `build_talk_behavior`
        *   `build_fight_behavior`
        *   `build_dance_behavior`
    *   **Action**: Register these goals in `BehaviorRegistry`.

## 4. Interaction Logic
*   **File**: `src/yukkuri_game/game/services.py` (or `SocialSystem` if decoupled)
    *   **Action**: Implement `interact_social(initiator_id, target_id, type)`.
    *   **Logic**:
        *   **Talk**: Increase happiness for both.
        *   **Fight**: Decrease health for both, decrease happiness.
        *   **Dance**: Increase happiness, play animation (if available).

## 5. Pre-commit Steps
*   **Action**: Ensure proper testing, verification, review, and reflection are done.

## 6. Verification
*   **Test**: Spawn two Yukkuris. Force AI state or high social utility. Verify they approach each other and interaction occurs (stats change).
