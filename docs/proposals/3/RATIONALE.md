# Rationale: Why "Clear-Cut" Wins

## 1. Solving the Complexity Trap
Previous proposals (Prop 1 & 2) fell into the trap of simulating "Realism" at the cost of "Readability."
*   **Prop 1** wanted 5 dimensions and a full physics simulation for emotions.
*   **Prop 2** wanted vector math for everything but forgot to define the inputs.

**Proposal 3** accepts that this is a game. Players understand archetypes ("The Jerk", "The Coward"). The **4-Axis Model** codifies these archetypes into numbers that are easy to debug and easy for players to predict.

## 2. Performance First
*   **Memory:** By using fixed-size buffers (`Trivial` and `Core`) we prevent memory spirals.
*   **Processing:** Opinion calculation is largely cached.
*   **Broadcasting:** The **Sector System** drastically reduces checks. Instead of checking distance to *all* entities ($O(N)$) for every shout, we only check entities in relevant sectors.

## 3. Clearer Emotional Feedback
The **2D Stress/Happiness** graph is standard game design (Darkest Dungeon, RimWorld's Mood/Break risk).
*   Separating "Dominance" into a static Personality Trait (`Bravery`) simplifies the simulation.
*   **Traits as Lenses:** This allows for more emergent behavior than simple stat clamping. A "Scum" isn't just a stat block; they fundamentally *see* the world differently (Food vs Friend). This creates distinct "AI Personalities" rather than just "AI Stats".

## 4. The Gossip Chain: Organic Storytelling
Instant telepathic reputation updates break immersion.
*   **The Viral Model:** Gossip spreads like a virus. This allows for secrets, lies, and delayed consequences.
*   **Player Story:** "I killed the witness, so nobody knows I stole the food" is a valid gameplay moment now.

## 5. Memory Updates
Locking Core Memories ensures that major narrative beats (Parent, Mate) aren't washed away by a thousand "Hello" interactions. This preserves the history of the Yukkuri.
