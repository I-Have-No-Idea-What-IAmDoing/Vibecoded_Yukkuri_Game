# Rationale: Why "Clear-Cut" Wins

## 1. Solving the Complexity Trap
Previous proposals (Prop 1 & 2) fell into the trap of simulating "Realism" at the cost of "Readability."
*   **Prop 1** wanted 5 dimensions and a full physics simulation for emotions.
*   **Prop 2** wanted vector math for everything but forgot to define the inputs.

**Proposal 3** accepts that this is a game. Players understand archetypes ("The Jerk", "The Coward"). The **Quad-Axis Model** codifies these archetypes into numbers that are easy to debug and easy for players to predict, while still allowing for 200^4 possible combinations.

## 2. Performance First: The Sector System
*   **Broadcasting:** By dividing the map into a coarse 4x4 Grid (Sectors), we eliminate global checks. A Yukkuri only cares about what it can see (Same/Adjacent + LoS) or hear. This drastically reduces the number of distance checks per frame.
*   **Memory:** Using fixed-size circular buffers (`Trivial` + `Core`) guarantees $O(1)$ memory usage per relationship. We never spiral into allocating thousands of objects.
*   **Processing:** Opinion calculation is cached. Base Compatibility is static. We only re-calculate when a new Memory is locked or a Trivial event occurs.

## 3. Depth via Lenses, Not Math
Instead of complex formulas to simulate a "Scum" Yukkuri, we use **Traits as Lenses**.
*   It is computationally cheaper and design-wise clearer to say "If Scum: Invert Social Instinct" than to have a complex matrix of weights.
*   **Dynamic Centers** allow for character growth. A "Scum" isn't hard-coded to be evil forever; they just default to it. This allows for rare, emergent "Redemption Arcs" where a Scum might form a positive Core Memory that pulls them temporarily towards kindness, adding narrative depth without simulation bloat.

## 4. Why 4 Axes? (The Greed Factor)
Feedback indicated that "Kindness" was overloaded. A Yukkuri can be "Nice" (polite, gentle) but also "Greedy" (wants all the food). Separating **Greed/Generosity** allows for more nuanced archetypes:
*   *The Polite Hoarder:* High Kindness, High Greed.
*   *The Gruff Philanthropist:* Low Kindness, Low Greed (Generous).

## 5. Organic Social Spread (Gossip)
Telepathic reputation updates break immersion. If a Yukkuri steals bread in the forest, the ones in the city shouldn't know instantly.
*   **The Gossip Chain** simulates the "Telephone Game." Information travels physically with the entities.
*   This creates gameplay loops: A "Scum" might try to eliminate witnesses before they can spread the gossip.
*   It creates "Information Pockets" where a Yukkuri can be a hero in Sector A but a villain in Sector B, until the groups meet.

## 6. Memory Locking
Separating `Trivial` and `Core` memories solves the "Spam" problem.
*   **Problem:** In old systems, 50 "Hello" interactions would push out the memory of "You killed my brother."
*   **Solution:** `CoreMemories` are protected. "You killed my brother" is a Locked Core Memory. No amount of "Hello" spam will erase it. This ensures that significant narrative beats stick, while daily noise cycles through naturally.
