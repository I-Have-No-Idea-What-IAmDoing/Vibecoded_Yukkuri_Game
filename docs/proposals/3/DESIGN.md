# Design Document: The "Clear-Cut" Personality & Social System

## 1. Overview
This proposal seeks to bridge the gap between "Stats" and "Simulation" without incurring the performance costs or complexity overhead of previous proposals. It prioritizes **Player Readability** and **Performance** while delivering the requested depth in memory and social dynamics.

## 2. Personality: The Quad-Axis Model
We reject the obscure "Big Five" float vectors in favor of a 4-Axis integer system (-100 to +100) that maps directly to Yukkuri archetypes.

### 2.1 The Axes
1.  **Kindness** (Gesu <-> Nice): Determines willingness to help vs harm.
2.  **Energy** (Lazy <-> Hyper): Determines action frequency, movement speed, and hunger rate.
3.  **Bravery** (Coward <-> Brave): Determines fight/flight thresholds and pain tolerance.
4.  **Greed** (Generous <-> Greedy): Determines resource sharing, hoarding behavior, and fairness in trade.

### 2.2 Traits as Centers & Lenses
Traits are no longer simple hard clamps. They act as **Dynamic Centers** and **Perceptual Lenses**.

#### 2.2.1 Dynamic Centers
Instead of forbidding values, a Trait shifts the *resting point* (center) of a personality axis.
*   *Standard:* Center is 0. Range is [-100, +100].
*   *Trait "Scum":* Shifts Kindness Center to -50.
    *   The Yukkuri naturally gravitates towards -50 (Gesu).
    *   It *can* reach +20 (Nice) with significant effort or specific events, but it fights its nature to do so.

#### 2.2.2 Traits as Lenses
Traits function as tags that apply **Behavioral Overrides** or modify Instincts. They act as a filter over perception.
*   *Trait "Predator":*
    *   **Lens:** "Yukkuris are Food, not Friends."
    *   **Effect:** Disables "Social Penalty" for eating other Yukkuris. Inverts the "Compassion" trigger.
*   *Trait "Scum":*
    *   **Lens:** "Others' pain is my pleasure."
    *   **Effect:** Inverts Social Instinct; witnessing pain generates Happiness instead of Stress.

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

## 4. Memory: The "Core & Trivial" System
To solve the "unbounded memory growth" problem while preserving meaningful history, we use a dual-buffer system with locking.

### 4.1 Concept
Not all memories are equal. We separate the "daily noise" from the "life-changing events".

### 4.2 Data Structure
Each Relationship maintains two separate buffers:

1.  **TrivialEvents (Size 25):** A circular buffer for minor interactions (chat, small trades, minor annoyances). These are overwritten frequently.
2.  **CoreMemories (Size 35):** A buffer for high-impact events (Trauma, Mate selection, Life-saving).

### 4.3 Locking
Specific high-importance memories can be **Locked**.
*   Locked memories cannot be overwritten by new Core Memories unless the new event has a significantly higher "Weight" or the locked memory is explicitly dissolved (e.g., divorce).
*   *Examples:* Parent, Mate, First Trauma, Nemesis.

### 4.4 Opinion Calculation
$$ \text{Opinion} = \text{Base Compatibility} + \sum (\text{CoreMemories}) + \text{Weighted Avg}(\text{TrivialEvents}) $$
*   **Base Compatibility:** Personality Axis comparison.
*   **CoreMemories:** Define the pillars of the relationship.
*   **TrivialEvents:** Provide the current "mood" of the relationship.

## 5. Social Propagation: The Sector System
We avoid $O(N^2)$ broadcasting by using a spatial sector map.

### 5.1 The Sector Map
The world is divided into large sectors (e.g., a 4x4 Grid).

### 5.2 Propagation Rules
Events broadcast based on their type and the observer's location relative to the actor.

*   **Visual Events:** Broadcast to entities in the **Same** or **Adjacent** sectors who have **Line-of-Sight**.
*   **Auditory Events:**
    *   **Loud:** Broadcast to **Same** sector.
    *   **Very Loud:** Broadcast to **Same** and **Adjacent** sectors.

### 5.3 Interest Groups
Interest Groups (e.g., `Pack_ID`) no longer grant telepathy. They function as a **Hearing Bonus**.
*   Being in the same pack means "I pay attention to your voice more," effectively increasing the signal reception range slightly or prioritizing that signal over noise. It does *not* allow hearing across the map.

## 6. The Gossip Chain
Information spreads organically like a virus, rather than instantly.

### 6.1 Gossip Packets
Witnesses do not immediately update the victim's reputation globally. Instead, they form a **Gossip Packet** containing:
*   `ActorID`, `Action`, `TargetID`, `Timestamp`, `OpinionModifier`
*   This packet is added to the witness's **Outgoing Gossip Queue**.

### 6.2 Interaction & Spread
When Entity A talks to Entity B:
1.  They exchange their **Top 3 Gossip Packets** (prioritized by recency and shock value).
2.  Entity B receives the packet. If it's new information, B processes it (reacts to it) and adds it to their own Queue to spread further.
3.  This creates a viral wave of reputation updates that travels across the map over time.

## 7. Architecture

### Components
*   `PersonalityAxis`: Stores the 4 int values.
*   `EmotionalState`: Stores Happiness (float) and Stress (float).
*   `MemoryBank`: Stores `TargetID -> { TrivialBuffer, CoreBuffer }`.
*   `GossipQueue`: Stores list of pending `GossipPackets`.

### Systems
*   `SocialSystem`: Handles Interaction -> Gossip Exchange.
*   `EmotionSystem`: Decays Happiness/Stress.
*   `WitnessSystem`: Grid-based event listener for broadcasting.
*   `SectorManager`: Manages the 4x4 grid and spatial lookups.
