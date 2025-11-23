# Emergent Gameplay & Scenarios

## Overview
By combining the **Personality System** and **Relationship System** with the existing **Utility AI**, we aim to create unscripted, complex narratives.

## Scenario 1: The Greedy Bully
**Setup:**
*   **Yukkuri A (Marisa):** High `Greed`, High `Arrogance`, High `Activity`.
*   **Yukkuri B (Reimu):** Low `Arrogance` (Timid), High `Sociality`.

**Process:**
1.  **Encounter:** A meets B. A checks `Dominance` (starts neutral). A's `Arrogance` makes "Intimidate" a viable action.
2.  **Action:** A performs "Intimidate".
3.  **Reaction:** B, being Timid, performs "Cower" or "Apologize".
4.  **Update:**
    *   A feels `Dominance` increase over B.
    *   B feels `Fear` (Low Trust) and `Submission` (Low Dominance) towards A.
5.  **Conflict:** Food appears.
    *   A's `Greed` + `Dominance` -> Triggers "Take All" or "Demand Food".
    *   B's `Submission` -> Relinquishes food.
6.  **Outcome:** A grows fat and happy. B starves or becomes stressed. B might eventually "Snap" (if Stress > Threshold) or try to run away.

## Scenario 2: The unlikely Friendship
**Setup:**
*   **Yukkuri A:** Lonely (Low Social), Depressed.
*   **Yukkuri B:** High `Kindness`, High `Sociality`.

**Process:**
1.  A is "Crying" (Action triggered by Low Happiness).
2.  B perceives A. B's `Kindness` boosts utility of "Comfort" action when target is distressed.
3.  B performs "Comfort" (licks/nuzzles).
4.  **Update:** A gains `Happiness` and `Affection` for B. B gains `Affection`.
5.  **Loop:** They stick together. A's mood improves. They form a "Family" bond.
6.  **Emergence:** If C attacks A, B (who is normally peaceful) might "Protect" A due to High Affection overriding Low Aggression.

## Scenario 3: Tribal Warfare
**Setup:**
*   Group Red: High internal Affection.
*   Group Blue: High internal Affection.

**Process:**
1.  Red Member encounters Blue Member. No relationship history -> Neutral.
2.  Red Member is `Arrogant`. Insults Blue Member.
3.  Blue Member tells Group Blue (via `Social` signal or witnessing).
4.  Group Blue lowers `Affection` for Red Member (and by extension, Group Red).
5.  Escalation: Turf wars over food sources driven by `Group Loyalty` (Affection) and `Xenophobia` (Low Affection for outsiders).

## Technical Requirements for Emergence
To achieve this, the AI must:
1.  **Perceive** not just food, but *others' actions*.
2.  **React** to social cues (being hit, being fed).
3.  **Remember** the specific agent who acted.

This requires the `InteractionSystem` to be more robust than just "Collision -> Stat Change". It needs to act as a message bus sending events like `OnHit(source, target)`, `OnGift(source, target)` which the Relationship System listens to.
