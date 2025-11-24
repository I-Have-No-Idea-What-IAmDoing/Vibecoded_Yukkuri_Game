# Design Document: The "Clear-Cut" Personality & Social System

## 1. Overview
This proposal seeks to bridge the gap between "Stats" and "Simulation" without incurring the performance costs or complexity overhead of previous proposals. It prioritizes **Player Readability** and **Performance** while delivering the requested depth in memory and social dynamics.

## 2. Personality: The Quad-Axis Model
We reject the obscure "Big Five" float vectors in favor of a 4-Axis integer system (-100 to +100) that maps directly to Yukkuri archetypes.

### 2.1 The Axes
1.  **Kindness** (Gesu <-> Nice): Determines willingness to share, help, or harm.
2.  **Energy** (Lazy <-> Hyper): Determines action frequency, movement speed, and hunger rate.
3.  **Bravery** (Coward <-> Brave): Determines fight/flight thresholds and pain tolerance.
4.  **Greed** (Generous <-> Greedy): Determines hoarding behavior, resource sharing, and risk-taking for material gain.

### 2.2 Traits as Lenses & Center Shifts
Traits (defined in TOML) are no longer simple static clamps. They are **Lenses** that filter perception and **Center Shifters** that modify the "natural resting point" of the personality axes.

*   **Center Shift:** A Trait shifts the *center* of the -100 to +100 range.
    *   *Example:* A "Scum" trait centers Kindness at -50. The Yukkuri *can* reach +20 Kindness with extreme effort or positive reinforcement, but it naturally drifts back to -50.
*   **Behavioral Overrides:** Traits act as tags allowing or disallowing specific logic paths.
    *   *Example:* A `Predator` trait doesn't just add `+0.5 Assertion`. It adds a **Behavioral Override**: "Yukkuri can be Food, not Friends."
    *   *Example:* A `Scum` trait inverts the Social instinct: "Gain pleasure from others' pain."

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
To solve the "unbounded memory growth" problem, we introduce the **Headline System** with Locking and Split Buffers.

### 4.1 Concept
We do not store every interaction. We only store **Headlines**—events that exceed a specific emotional threshold.

### 4.2 Data Structure: Split Buffers
Each Relationship maintains two distinct buffers:
1.  **TrivialEvents (Size 25):** Small, everyday interactions. Fast cycling.
2.  **CoreMemories (Size 35):** Major life events (First Mate, Trauma, Saved Life).

### 4.3 Locking
Important memories can be **Locked**. A Locked memory cannot be overwritten by new entries in the `CoreMemories` buffer unless the new entry is of significantly higher magnitude.
*   *Example:* "Parent" and "Mate" memories are locked by default.

### 4.4 Opinion Calculation
$$ \text{Opinion} = \text{Base Compatibility} + \sum (\text{CoreMemories}) + \sum (\text{TrivialEvents}) $$
*   **Base Compatibility:** Calculated once from Personality Axis comparison.
*   **CoreMemories:** High impact, long-lasting.
*   **TrivialEvents:** Low impact, provide recent context.

## 5. Social Propagation: The Sector System
We avoid $O(N^2)$ broadcasting by dividing the map into large sectors (e.g., a 4x4 grid).

### 5.1 Sector Broadcasting
*   **Visual Events:** Broadcast only to entities in the *same* or *adjacent* sectors who have Line-of-Sight.
*   **Auditory Events:** Broadcast to the *same* sector (Loud) or *adjacent* sectors (Very Loud).

### 5.2 Interest Groups as Hearing Bonus
Being in the same "Interest Group" (e.g., Pack, Family) functions as a **Hearing Bonus**. It means "I listen to you *more*," not "I hear you *everywhere*." It lowers the threshold for noticing an event but does not bypass spatial limits.

## 6. The Gossip Chain
Information spreads organically like a virus, rather than instantly via telepathy.

### 6.1 Gossip Packets
Witnesses do not immediately update the victim's reputation globally. Instead, they add a **Gossip Packet** to their own outgoing queue.

### 6.2 Interaction Exchange
When Entity A talks to Entity B, they exchange their top 3 **Gossip Packets**.
*   *Result:* If A sees C do something bad, B only learns about it when A talks to B. The information ripples through the population over time.

## 7. Architecture

### Components
*   `PersonalityAxis`: Stores the 4 int values.
*   `EmotionalState`: Stores Happiness (float) and Stress (float).
*   `MemoryBank`: Stores `TargetID -> {Trivial: RingBuffer, Core: RingBuffer}`.
*   `GossipQueue`: Stores a priority queue of `GossipPacket`s to share.

### Systems
*   `SocialSystem`: Handles Interaction -> Headline generation and Sector-based broadcasting.
*   `EmotionSystem`: Decays Happiness/Stress towards 0 (or baseline).
*   `WitnessSystem`: Listens for events within Sectors and generates Gossip.
*   `GossipSystem`: Manages the exchange of packets during conversation.
