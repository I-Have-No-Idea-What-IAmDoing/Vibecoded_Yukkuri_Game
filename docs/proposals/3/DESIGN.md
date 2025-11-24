# Design Document: The "Clear-Cut" Personality & Social System

## 1. Overview
This proposal seeks to bridge the gap between "Stats" and "Simulation" without incurring the performance costs or complexity overhead of previous proposals. It prioritizes **Player Readability** and **Performance** while delivering the requested depth in memory and social dynamics.

## 2. Personality: The Tri-Axis Model
We reject the obscure "Big Five" float vectors in favor of a 3-Axis integer system (-100 to +100) that maps directly to Yukkuri archetypes.

### 2.1 The Axes
1.  **Kindness** (Gesu <-> Nice): Determines willingness to share, help, or harm.
2.  **Energy** (Lazy <-> Hyper): Determines action frequency, movement speed, and hunger rate.
3.  **Bravery** (Coward <-> Brave): Determines fight/flight thresholds and pain tolerance.

### 2.2 Traits as Clamps & Modifiers
Traits (defined in TOML) enforce **Range Clamps** or **Multipliers**.
*   *Trait "Scum":* Clamps Kindness to [-100, -20]. (Cannot ever be truly nice).
*   *Trait "Predator":* Multiplies Bravery impact by 1.5x.

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
To solve the "unbounded memory growth" problem, we introduce the **Headline System**.

### 4.1 Concept
We do not store every interaction. We only store **Headlines**—events that exceed a specific emotional threshold.

### 4.2 Data Structure
Each Relationship maintains a fixed-size circular buffer (Size=5) of `Headlines`.
```python
struct Headline {
    EventType type;       // e.g., RECEIVED_DAMAGE, GIVEN_FOOD
    int severity;         // 1-10 scale
    int opinion_impact;   // +/- value
    Timestamp time;
}
```

### 4.3 Opinion Calculation
$$ \text{Opinion} = \text{Base Compatibility} + \sum (\text{Headline.opinion\_impact}) + \text{Decayed Recent Interactions} $$
*   **Base Compatibility:** Calculated once from Personality Axis comparison (e.g., Nice likes Nice).
*   **Headlines:** The heavy hitters. They define the relationship until they are pushed out by new Headlines.
*   **Recent:** A small, fast-decaying buffer for immediate context (prevents "spam hugging").

## 5. Social Propagation: The "Interest Group"
We avoid $O(N^2)$ broadcasting.

### 5.1 Interest Groups
Entities register to "Interest Groups" (e.g., `Family_ID`, `Pack_ID`).
*   **Local Broadcast:** Events are broadcast *only* to:
    1.  Entities within a strict short range (Grid-based lookup).
    2.  Entities in the same `Interest Group` (regardless of range, if "telepathy/shouting" is allowed, otherwise strictly range-limited).

### 5.2 Witness Logic
Witnesses generate a `Headline` regarding the Actor based on the action observed.
*   *Example:* C sees A hit B.
    *   If C likes B -> C adds Headline "A hurt B" (Negative impact).
    *   If C hates B -> C adds Headline "A punished B" (Positive/Neutral impact).

## 6. Architecture

### Components
*   `PersonalityAxis`: Stores the 3 int values.
*   `EmotionalState`: Stores Happiness (float) and Stress (float).
*   `MemoryBank`: Stores the map of `TargetID -> RingBuffer<Headline>`.

### Systems
*   `SocialSystem`: Handles Interaction -> Headline generation.
*   `EmotionSystem`: Decays Happiness/Stress towards 0 (or baseline).
*   `WitnessSystem`: Event-based listener for broadcasting social events.
