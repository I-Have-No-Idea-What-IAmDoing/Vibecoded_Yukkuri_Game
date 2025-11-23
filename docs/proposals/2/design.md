# Proposal 2: Enhanced Personality & Relationship System

## 1. Introduction

The current Personality and Relationship system provides a basic framework for social interaction (Affinity, Trust, Fear) and simple Mood states. However, it lacks depth in memory retention, complex emotional states, and indirect social consequences (witnessing events, gossip).

This proposal outlines a redesign to introduce:
1.  **Vector-based Personality & Moods** for more nuance.
2.  **Two-Tier Memory System** (Episodic vs. Semantic) to create lasting opinions.
3.  **Social Propagation** where actions observed by third parties affect their relationships.

## 2. Core Components

### 2.1. Vector-Based Personality (The "Soul")
Instead of just a list of traits, we define a core personality vector based on a simplified Big Five or similar model, adapted for Yukkuri behavior.

*   **Openness/Curiosity**: Tendency to explore or try new foods/items.
*   **Aggression/Dominance**: Tendency to fight or assert control.
*   **Social/Extroversion**: Need for interaction and group size preference.
*   **Rationality/Intelligence**: Ability to delay gratification and process complex interactions.

**Traits** (e.g., "Scum", "Angel") will act as *presets* or *modifiers* to these base vectors, rather than being the only logic drivers.

### 2.2. PAD Emotional Model (The "Heart")
Replace the simple `Mood` string with a **PAD (Pleasure, Arousal, Dominance)** model.
This allows for continuous emotional states rather than discrete switches.

*   **Pleasure**: Positive vs. Negative feeling. (Happy <-> Sad/Pain)
*   **Arousal**: Energy level of the emotion. (Excited/Furious <-> Calm/Bored)
*   **Dominance**: Feeling of control. (Confident/Anger <-> Fear/Submissive)

**Mapping Examples:**
*   *Anger*: Low Pleasure, High Arousal, High Dominance.
*   *Fear*: Low Pleasure, High Arousal, Low Dominance.
*   *Joy*: High Pleasure, High Arousal, High Dominance.
*   *Relaxed*: High Pleasure, Low Arousal, High Dominance.

### 2.3. Dual-Layer Memory System (The "Brain")

#### Short-Term Memory (Episodic)
Retains recent specific events (as currently implemented).
*   *Record*: "Reimu #2 hit me at 12:00."
*   *Limit*: Last 10-20 events or last 1 game hour.

#### Long-Term Memory (Semantic/Sentiment)
Periodically, Short-Term Memories are **consolidated** into a persistent Sentiment Vector towards another entity.
*   **Affinity**: Like/Dislike.
*   **Respect**: Competence/Power assessment.
*   **Trust**: Reliability/Safety.

**Consolidation Logic:**
*   Repeated negative events lower Affinity.
*   High-impact trauma is "locked" (hard to forget).
*   Positive interactions slowly decay if not reinforced (drift to neutral), but negative impressions linger longer (evolutionary bias).

## 3. Social Dynamics

### 3.1. Witness System
Interactions are no longer private between Actor and Target.
*   **Event Broadcast**: When A interacts with B, a `SocialEvent` is broadcast to entities within a radius $R$.
*   **Witness Reaction**:
    *   If C sees A hit B:
        *   C's opinion of A decreases (if C likes B).
        *   C's opinion of A might increase (if C hates B - "Schadenfreude").
        *   C's fear of A increases (if A is strong).

### 3.2. Group Dynamics
*   **Social Tiers**: Introduction of "Outsider", "Acquaintance", "Friend", "Family/Pack".
*   **Pack Logic**: Entities with high mutual affinity form a dynamic Pack/Family group, sharing a "Group Territory" and "Group Resources".

## 4. Systems Architecture

### Updated `Personality` Component
```python
class Personality:
    # Base Vectors (-1.0 to 1.0)
    curiosity: float
    aggression: float
    social: float
    rationality: float

    # Mood (PAD Model)
    pleasure: float
    arousal: float
    dominance: float

    traits: Set[str] # Modifiers
```

### Updated `RelationshipData`
```python
class RelationshipData:
    # Sentiment Vectors (-100 to 100)
    affinity: float
    respect: float
    trust: float

    # Status
    status_label: str # "Stranger", "Friend", "Rival"

    # Memory
    short_term_memories: List[MemoryRecord]
    long_term_summary: Dict[str, float] # e.g., {"times_fed_me": 5, "times_hit_me": 1}
```

### New `MemorySystem`
A dedicated system (or sub-process of `SocialSystem`) that runs less frequently (e.g., every 10 seconds) to process memory consolidation.

## 5. Rationale

*   **Emergent Storytelling**: By allowing third-party witnesses and long-term grudges/friendships independent of recent interaction spam, the game world feels more alive.
*   **Nuanced Behavior**: A "Scared" Yukkuri (Low Dominance, High Arousal) acts differently than a "Depressed" one (Low Dominance, Low Arousal).
*   **Scalability**: Vector math is faster and easier to balance than complex `if-else` chains for every possible trait combination.
