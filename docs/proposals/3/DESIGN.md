# Design Document: The "Clear-Cut" Personality & Social System

## 1. Overview
This proposal seeks to bridge the gap between "Stats" and "Simulation" without incurring the performance costs or complexity overhead of previous proposals. It prioritizes **Player Readability** and **Performance** while delivering the requested depth in memory and social dynamics.

## 2. Personality: The 4-Axis Model
We reject the obscure "Big Five" float vectors in favor of a 4-Axis integer system (-100 to +100) that maps directly to Yukkuri archetypes.

### 2.1 The Axes
1.  **Kindness** (Gesu <-> Nice): Determines willingness to share, help, or harm.
2.  **Energy** (Lazy <-> Hyper): Determines action frequency, movement speed, and hunger rate.
3.  **Bravery** (Coward <-> Brave): Determines fight/flight thresholds and pain tolerance.
4.  **Greed** (Greedy <-> Generous): Determines resource sharing, hoarding behavior, and fairness in trade.

### 2.2 Traits as Lenses
Traits are no longer simple clamps. They act as **Lenses** that filter perception and modify Instincts.
*   **Center Shift:** Traits shift the *center* of the range.
    *   *Example:* A "Scum" trait centers Kindness at -50. With effort (training/events), they can reach +20, but their "natural state" pulls them back to -50.
*   **Behavioral Overrides (Tags):** Traits allow/disallow specific logic blocks.
    *   *Example:* `Predator` adds `CAN_EAT_YUKKURI`. It doesn't just tweak stats; it unlocks a behavior.
    *   *Example:* `Scum` inverts Social Instinct: "Gain pleasure from others' pain."

## 3. Emotional State: The 2D Stress-Happiness Graph
We simplify the PAD model to a 2D coordinate system, deriving the third dimension from personality.

### 3.1 The Variables
*   **Happiness (-100 to 100):** The Pleasure axis.
*   **Stress (0 to 100):** The Arousal axis. High stress = panic/frenzy. Low stress = calm/boredom.

### 3.2 Derived Moods (The "Quadrants")
*   **High Happiness + Low Stress:** *Content/Relaxed*
*   **High Happiness + High Stress:** *Excited/Manic*
*   **Low Happiness + Low Stress:** *Depressed/Sulking*
*   **Low Happiness + High Stress:** *Terror/Rage* (Context dependent)

*Note: The "Dominance" aspect of PAD is static, derived from the `Bravery` personality stat. A Brave Yukkuri in "Terror/Rage" chooses Rage; a Coward chooses Terror.*

## 4. Memory: The "Headline" System
To solve the "unbounded memory growth" problem, we use a dual-buffer system with locking.

### 4.1 Data Structure
Each Relationship maintains two buffers:
1.  **Trivial Events (Size 25):** Circular buffer for minor interactions (Chat, Play). Overwritten easily.
2.  **Core Memories (Size 35):** For major events (Trauma, Mate bonded, Saved life).
    *   **Locking:** Core Memories can be flagged as `Locked`. Locked memories cannot be overwritten by new Core Memories unless the new event is of significantly higher magnitude or specific type (e.g., "Divorce" overwrites "Marriage").

### 4.2 Opinion Calculation
$$ \text{Opinion} = \text{Base Compatibility} + \sum (\text{CoreMemories}) + \text{Weighted Avg}(\text{TrivialEvents}) $$
*   **Base Compatibility:** Calculated from Personality Axes + Trait Lenses.
*   **Core Memories:** High impact, long-lasting.
*   **Trivial Events:** Provide short-term context/mood.

## 5. Social Propagation: The Sector System & Gossip Chain
We use a spatial partitioning system for event propagation and a viral gossip model.

### 5.1 The Sector System
The map is divided into large sectors (e.g., 4x4 grid).
*   **Visual Events:** Broadcast only to entities in the *same* or *adjacent* sectors who have Line-of-Sight.
*   **Auditory Events:**
    *   *Loud:* Broadcast to Same + Adjacent sectors.
    *   *Normal:* Broadcast to Same sector.
*   **Interest Groups:** Function as "Hearing Bonus". Being in the same pack means I listen to you *more*, not that I hear you *everywhere*.

### 5.2 The Gossip Chain
Witnesses do not immediately update the victim's reputation globally.
1.  **Witness:** Adds a "Gossip Packet" (e.g., "Marisa hit Reimu") to their own **Outgoing Queue**.
2.  **Transmission:** When Entity A talks to Entity B, they exchange their top 3 Gossip Packets.
3.  **Result:** Information spreads organically like a virus. If you hit someone in secret, the town won't know until the victim (or a witness) talks to someone.

## 6. Architecture

### Components
*   `Personality`: Stores the 4 axis values and Trait set.
*   `RelationshipData`: Stores `TrivialEvents` and `CoreMemories` buffers.
*   `GossipQueue`: Stores active rumors to spread.

### Systems
*   `SocialSystem`: Handles spatial propagation (Sectors) and Gossip exchange.
*   `TraitService`: Applies "Lens" logic (Center Shift + Tags).
