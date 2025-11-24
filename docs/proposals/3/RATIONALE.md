# Rationale: Why "Clear-Cut" Wins

## 1. Solving the Complexity Trap
Previous proposals (Prop 1 & 2) fell into the trap of simulating "Realism" at the cost of "Readability."
*   **Prop 1** wanted 5 dimensions and a full physics simulation for emotions.
*   **Prop 2** wanted vector math for everything but forgot to define the inputs.

**Proposal 3** accepts that this is a game. Players understand archetypes ("The Jerk", "The Coward"). The **Tri-Axis Model** codifies these archetypes into numbers that are easy to debug and easy for players to predict, while still allowing for 200^3 possible combinations.

## 2. Performance First
*   **Memory:** By using a fixed-size circular buffer (Size=5) for Headlines, we guarantee $O(1)$ memory usage per relationship. We never spiral into allocating thousands of objects for a long-running colony.
*   **Processing:** Opinion calculation is largely cached. We only re-sum the Headlines when a new one is added. Base Compatibility is static. This is significantly faster than iterating through variable-length lists every frame.
*   **Broadcasting:** By limiting social broadcasts to spatial grids and Interest Groups, we avoid the exponential cost of global gossip.

## 3. Clearer Emotional Feedback
The **2D Stress/Happiness** graph is standard game design (Darkest Dungeon, RimWorld's Mood/Break risk).
*   Separating "Dominance" into a static Personality Trait (`Bravery`) simplifies the simulation. A character doesn't need to calculate if they feel "Dominant" every frame; they just *are* Brave or Cowardly, and that dictates how they express their Stress.
*   This makes writing AI behavior trees much simpler:
    *   `if Stress > 80 and is_Coward: Flee()`
    *   `if Stress > 80 and is_Brave: Fight()`

## 4. The Headline System vs. Continuous History
Players don't remember that their pet ate a cookie 400 cycles ago. They remember "That time Marisa stole the cookie."
The **Headline System** mimics human memory bias: we remember the *peaks*, not the noise. This aligns the game's internal logic with the player's narrative experience.
