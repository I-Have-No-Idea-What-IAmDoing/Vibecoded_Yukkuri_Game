# Design Document: Personality & Relationship System 2.0

## 1. Overview
The current Personality and Relationship system provides a functional baseline but lacks depth, resulting in predictable and repetitive social behaviors. This proposal outlines a redesign aimed at creating **emergent storytelling** and **dynamic character growth**.

The new system moves away from static "stats" and "flags" toward a **simulationist model** inspired by systems in *RimWorld*, *The Sims*, and *Dwarf Fortress*.

## 2. Personality System 2.0

### 2.1 Core Dimensions (The "Big Five" of Yukkuri)
Instead of arbitrary "Values", every Yukkuri will have 5 base dimensions (0.0 - 1.0) that define their default behavior.

1.  **Smartness (Intellect):** Ability to learn, memory retention, problem-solving.
2.  **Attitude (Agreeableness):** Base kindness vs. selfishness (Gesu).
3.  **Discipline (Conscientiousness):** Ability to suppress urges, follow rules.
4.  **Social (Extraversion):** Need for interaction, boldness in social moves.
5.  **Stress Tolerance (Neuroticism):** Resistance to trauma, speed of mood decay.

### 2.2 Traits as Modifiers
Traits (defined in TOML) will no longer just be flags but will:
*   Apply **permanent offsets** to Core Dimensions (e.g., "Gesu" -> -0.4 Attitude).
*   Unlock **special interactions** (e.g., "Predator" -> "Hunt").
*   Alter **Need Decay rates** (e.g., "Glutton" -> 1.5x Hunger decay).

### 2.3 Drives (Utility AI Base)
"Values" are replaced by **Drives**. Drives are the long-term motivations that weight decision-making.
*   *Safety*
*   *Comfort*
*   *Social Connection*
*   *Dominance*
*   *Curiosity*

## 3. Emotional System (PAD Model)

Replacing the static `Mood` string is a dynamic vector-based system using the **PAD (Pleasure, Arousal, Dominance)** model.

### 3.1 The State Vector
*   **Pleasure (-1.0 to 1.0):** Agony <-> Ecstasy
*   **Arousal (0.0 to 1.0):**  Bored/Sleepy <-> Excited/Panicked
*   **Dominance (-1.0 to 1.0):** Submissive/Powerless <-> Empowered/Controlling

### 3.2 Derived Emotional States
The "Mood" displayed to the player is derived from the current vector:
*   High P, High A, High D -> **Triumphant/Manic**
*   Low P, High A, Low D -> **Fear/Terror**
*   Low P, High A, High D -> **Anger/Rage**
*   High P, Low A -> **Content/Relaxed**

### 3.3 Emotional Volatility
Emotions drift back to a "Baseline" (determined by Personality) over time. Interactions apply impulse vectors to this state.

## 4. Memory System 2.0

### 4.1 Short-Term Buffer
Retains the last ~10 events. Used for immediate context ("He just hit me, I shouldn't hug him yet").

### 4.2 Long-Term Consolidation
Significant events (High Emotional Impact) are consolidated into **Core Memories**.
*   *Structure:* `{ Timestamp, OtherID, EventType, EmotionalSnapshot, OpinionModifier }`
*   *Example:* "Mother ate my food" -> High Arousal, Low Pleasure -> -20 Opinion of Mother.

### 4.3 Associative Recall
Seeing an entity or object can trigger a memory recall, re-applying a fraction of that memory's emotional state.

## 5. Relationship System 2.0

### 5.1 The "Opinion" Score
Relationships are no longer just "Affinity". They are defined by an **Opinion** score calculated dynamically:
$$ \text{Opinion} = \text{Base Compatibility} + \sum (\text{Memory Modifiers}) + \text{Recent Interactions} $$

### 5.2 Dynamic Roles
Thresholds in Opinion and specific Memory combinations unlock **Dynamic Roles**:
*   *Rival:* Negative Opinion + High Respect (Dominance).
*   *Bully:* Negative Opinion + Low Respect (Target is Low Dominance).
*   *Idol:* Positive Opinion + Gap in Dominance.

### 5.3 Social Graph
Yukkuris can gossip. If A tells B that C is bad, B's opinion of C lowers (modified by B's trust in A).

## 6. Architecture Changes

### New Components
*   `EmotionState`: Stores PAD vector.
*   `SocialMemory`: Stores Long-term and Short-term lists.
*   `PersonalityDimensions`: Stores the 5 core stats.

### System Updates
*   `SocialSystem`: Handles Interaction -> PAD Impulse -> Memory formation.
*   `EmotionSystem`: Handles PAD decay and State mapping.
*   `DecisionSystem` (Update): Uses Drives + Current Emotion to pick actions.
