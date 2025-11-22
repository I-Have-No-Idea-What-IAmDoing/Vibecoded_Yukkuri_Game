# Content: Expand Interactions

## Goal
Add social interactions between Yukkuris to make them feel more alive. Specifically: "Talk", "Fight", and "Dance".

## Steps

1.  **Define Interaction Constants**
    -   **File**: `src/yukkuri_game/game/ai/behavior.py` or `src/yukkuri_game/config.py`
    -   Define constants for interaction ranges and durations.

2.  **Implement Behavior Actions**
    -   **File**: `src/yukkuri_game/game/ai/behavior.py`
    -   **Class `SocialInteract`**: A generic or specific action for social stuff.
        -   **Talk**: Requires another Yukkuri nearby. Increases happiness for both.
        -   **Fight**: Requires incompatible types (e.g., Reimu vs Marisa if configured) or low happiness. Decreases health/happiness.
        -   **Dance**: Group activity. Requires high happiness.

3.  **Add Social Goals to Registry**
    -   **File**: `src/yukkuri_game/game/ai/behavior.py`
    -   Create builders: `build_talk_behavior`, `build_fight_behavior`.
    -   Register them in `BehaviorRegistry`.

4.  **Update Utility System**
    -   **File**: `src/yukkuri_game/game/ai/utility.py`
    -   Add utility scorers for `Talk`, `Fight`.
    -   `Talk` utility: High if happiness is moderate, loneliness is high (if loneliness exists, or just random chance).
    -   `Fight` utility: High if nearby enemy type OR happiness is very low (stress release).

5.  **Update Visuals/Audio (Basic)**
    -   **File**: `src/yukkuri_game/game/services.py` (`GameService.interact...`) or specialized handler.
    -   Play "chat" sound for talking.
    -   Play "hit" sound for fighting.
    -   (Optional) Show emoticons (speech bubble, angry vein) via particles or UI.

6.  **Verification**
    -   **Test**: Spawn two Yukkuris close to each other.
    -   Mock/Force the utility to pick "Talk".
    -   Verify they move close (or stay) and happiness increases.
    -   **Test**: Spawn two incompatible/angry Yukkuris.
    -   Verify they choose "Fight" and health decreases.

## Pre-commit
-   Ensure proper testing, verification, review, and reflection are done.
