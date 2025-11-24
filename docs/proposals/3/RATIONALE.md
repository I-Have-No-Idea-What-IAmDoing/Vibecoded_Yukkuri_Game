# Rationale: Why "Clear-Cut" Wins

## 1. Solving the Complexity Trap
Previous proposals (Prop 1 & 2) fell into the trap of simulating "Realism" at the cost of "Readability."
*   **Prop 1** wanted 5 dimensions and a full physics simulation for emotions.
*   **Prop 2** wanted vector math for everything but forgot to define the inputs.

**Proposal 3** accepts that this is a game. Players understand archetypes ("The Jerk", "The Coward"). The **Quad-Axis Model** (Kindness, Energy, Bravery, Greed) codifies these archetypes into numbers that are easy to debug and easy for players to predict, while still allowing for billions of possible combinations.

## 2. Performance First
*   **Memory:** By using fixed-size circular buffers (`Trivial`=25, `Core`=35) for Headlines, we guarantee $O(1)$ memory usage per relationship. We never spiral into allocating thousands of objects for a long-running colony. Locking ensures key memories are preserved without unbounded lists.
*   **Processing:** Opinion calculation is largely cached. We only re-sum the Headlines when a new one is added. Base Compatibility is static.
*   **Broadcasting:** The **Sector System** strictly limits the number of entity checks for any event. Visual/Auditory events are culled by sector before Line-of-Sight is even calculated.
*   **Gossip:** By removing "Telepathic Broadcasting" in favor of the **Gossip Chain**, we distribute the CPU load of reputation updates. Instead of 1 event causing 50 immediate updates, it causes 1 update that slowly propagates during idle chatter ticks.

## 3. Clearer Emotional Feedback
The **2D Stress/Happiness** graph is standard game design (Darkest Dungeon, RimWorld's Mood/Break risk).
*   Separating "Dominance" into a static Personality Trait (`Bravery`) simplifies the simulation. A character doesn't need to calculate if they feel "Dominant" every frame; they just *are* Brave or Cowardly, and that dictates how they express their Stress.
*   This makes writing AI behavior trees much simpler:
    *   `if Stress > 80 and is_Coward: Flee()`
    *   `if Stress > 80 and is_Brave: Fight()`

## 4. The Headline System vs. Continuous History
Players don't remember that their pet ate a cookie 400 cycles ago. They remember "That time Marisa stole the cookie."
The **Headline System** mimics human memory bias: we remember the *peaks*, not the noise. This aligns the game's internal logic with the player's narrative experience.

## 5. Traits as Lenses: Agency over Restrictions
Early drafts used "Clamps" (e.g., "Cannot be Nice"), but this felt robotic.
*   **Center Shifting** allows for emergent storytelling. A "Scum" *can* be nice, but it takes constant effort (fighting their nature). If they stop trying, they slide back to being Scum. This creates a "Redemption Arc" mechanic automatically.
*   **Behavioral Overrides** provide the flavor. Stats provide the thresholds, but Overrides provide the *context*. A `Predator` isn't just "Brave"; they fundamentally view other Yukkuri as a resource.

## 6. Organic Information Flow
The **Gossip Chain** solves the "Hivemind" problem. If a murder happens in the forest and no one talks about it, the murderer's reputation in the village remains clean. This allows for secret crimes, lies, and rumors—essential elements of colony drama.
