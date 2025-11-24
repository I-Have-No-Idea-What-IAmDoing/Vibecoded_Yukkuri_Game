# Rationale: Why Proposal 4 Wins

## 1. The Sweet Spot of Complexity
*   **Proposal 1** failed because it tried to be a psychology simulator (Big Five, PAD vectors).
*   **Proposal 3** failed because it tried to be a spreadsheet (Tri-Axis, Headlines).
*   **Proposal 4** succeeds by modeling **Game Systems**, not real life. The "Hydraulic" model (Buckets) is easy for players to understand ("My Ego bucket is full, so I'm acting arrogant") and cheap for the CPU to calculate.

## 2. Memory That Scales
*   **P1** had infinite memory growth ($O(N^2 * M)$).
*   **P3** had arbitrary amnesia (Circular Buffer 5).
*   **P4** uses the **Weighted Highlight** system. By capping memories to "Top 3 Most Impactful", we guarantee fixed memory usage per relationship ($O(1)$ space) while preserving the *narrative* importance of major events. A Yukkuri won't remember every time you fed it, but it will forever remember the one time you burned it.

## 3. Social Performance
*   **P2** and **P1** suffered from $O(N^2)$ broadcast storms.
*   **P4** introduces **Sector-Based Broadcasting** and **Gossip Queues**.
    *   *Sectors* limit the immediate CPU cost of finding witnesses.
    *   *Gossip* spreads the computational load over time. Information travels at the speed of movement, not the speed of light, which is both more realistic and more performant.

## 4. Character Depth
*   **The Instincts** (Survival, Social, Assertion, Cognition) map directly to gameplay actions (Fleeing, Grouping, Demanding, Solving).
*   **Traits as Lenses** allows for special behaviors (like "Predator") that fundamentally change how the world is perceived, rather than just tweaking a number. This supports the "Emergent Storytelling" goal better than P2's vague modifiers.

## 5. Conclusion
Proposal 4 represents the mature synthesis of the previous ideas. It accepts the constraints of the engine and the hardware while delivering the player-facing complexity that makes the simulation feel alive.
