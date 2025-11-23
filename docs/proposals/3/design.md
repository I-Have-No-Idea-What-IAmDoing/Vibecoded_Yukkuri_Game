# Personality and Relationship System 2.0 Design

This document outlines the design for a revamped Personality and Relationship system for the Yukkuri Game. The goal is to move from a static, tag-based system to a dynamic, simulation-driven model that allows for emergent storytelling and complex social behaviors.

## 1. Personality Model: Nature vs. Nurture

The new personality system distinguishes between innate tendencies (Nature) and learned values (Nurture).

### 1.1 Core Attributes (Nature)
These are immutable stats determined at birth (0-100 scale). They define the *potential* and *tendencies* of a Yukkuri. Modeled loosely after the "Big Five" personality traits but adapted for Yukkuri behavior.

| Attribute | Low (0-25) | High (75-100) | Description |
| :--- | :--- | :--- | :--- |
| **Aggression** | Passive / Cowardly | Aggressive / Predatory | Tendency to choose violence or domination in conflicts. |
| **Sociability** | Loner / Independent | Herd / Clingy | Need for social interaction and tolerance for crowding. |
| **Intelligence** | Foolish / Instinctual | Smart / Calculated | Learning speed, memory retention, and ability to plan. |
| **Greed** | Generous / Altruistic | Selfish / Gluttonous | Willingness to share resources vs. hoarding. |
| **Stability** | Neurotic / Volatile | Calm / Resilient | Stress resistance and emotional volatility. |

### 1.2 Values & Beliefs (Nurture)
These are dynamic stats that evolve over time based on memories and interactions. They act as multipliers or thresholds for decision-making.

*   **TrustInHumans:** (0-100) How likely they are to approach or flee from players.
*   **PackLoyalty:** (0-100) Importance of the group vs. self.
*   **WorkEthic:** (0-100) Willingness to perform tasks vs. slack off (applies to domesticated/managed yukkuri).

### 1.3 Traits (Perks/Quirks)
The existing "Trait" system (e.g., `Gesu`, `Nice`) will remain but be repurposed as "Perks" or special modifiers that sit on top of the Core Attributes.
*   **Gesu:** Forces *Greed* > 80, *Aggression* > 60. Unlocks "Lie" and "Steal" actions.
*   **SuperHardy:** Physical modifier, distinct from personality.

## 2. Relationship Model: The Tri-Axis System

Instead of a single "Affinity" score, relationships between entities are defined by three axes. This allows for complex feelings like "I respect him but I hate him" or "I love him but he scares me."

### 2.1 The Axes
1.  **Affinity (Love/Hate):** The emotional connection.
    *   *Range:* -100 (Hatred) to +100 (Love).
    *   *Effect:* Willingness to share, groom, and play.
2.  **Dominance (Respect/Disdain):** The hierarchical perception.
    *   *Range:* -100 (I am superior) to +100 (They are superior).
    *   *Effect:* Submissiveness, willingness to follow orders, who initiates interactions.
3.  **Trust (Safety/Fear):** The perception of safety.
    *   *Range:* -100 (Terrified) to +100 (Total Trust).
    *   *Effect:* Fleeing distance, relaxation near target, allowing physical touch.

### 2.2 Relationship Updates
Relationships are updated via:
*   **Direct Interaction:** Being fed increases Affinity. Being hit decreases Trust and Affinity.
*   **Observation:** Seeing someone hit another decreases Trust.
*   **Gossip:** Hearing about someone affects Reputation (see Memory).

## 3. Memory System

A two-tier memory system allows Yukkuri to "learn" from their experiences without storing infinite data.

### 3.1 Episodic Memory (Short-Term)
*   Stores specific events: `{Timestamp, ActorID, Action, ImpactScore}`.
*   *Example:* "Reimu #4 hit me at tick 500 (Impact -50)."
*   **Decay:** These memories fade quickly (e.g., 1-2 game days). High-impact memories last longer.

### 3.2 Semantic Memory (Long-Term/Consolidated)
*   When Episodic memories fade, their emotional weight is "consolidated" into the general Relationship stats or General Beliefs.
*   *Process:*
    1.  Memory of "Reimu #4 hit me" is about to expire.
    2.  System applies a permanent -0.5 to *Trust* for Reimu #4.
    3.  System applies a small negative modifier to global *TrustInKind* (if Reimu #4 is the same kind).
    4.  Memory is deleted.

### 3.3 Gossip & Reputation
*   Yukkuri can share Semantic summaries.
*   *Action:* "Chat".
*   *Payload:* "Reimu #4 is Bad (Affinity -50)."
*   *Result:* Listener adjusts their opinion of Reimu #4 based on their trust in the Speaker.

## 4. Integration with Utility AI

The Utility AI `Considerations` will be updated to use these new inputs.

*   **Action: Play with Target**
    *   *Consideration:* `Target.Affinity` (Must be > 0).
    *   *Consideration:* `Self.Sociability` (Higher makes play more desirable).
*   **Action: Bully Target**
    *   *Consideration:* `Target.Dominance` (Must be < 0, i.e., "I am stronger").
    *   *Consideration:* `Self.Aggression` (Higher score).
    *   *Consideration:* `Self.Sadism` (Derived from Low Empathy/Gesu).

## 5. Summary of Data Changes

### `Personality` Component
```python
@dataclass
class Personality:
    # Nature (0-100)
    aggression: float
    sociability: float
    intelligence: float
    greed: float
    stability: float

    # Nurture (0-100)
    values: Dict[str, float]

    # Traits (Strings)
    traits: Set[str]
```

### `RelationshipData` Component
```python
@dataclass
class RelationshipData:
    affinity: float  # Love <-> Hate
    dominance: float # Inferior <-> Superior
    trust: float     # Fear <-> Safe

    # Semantic Summary (Cached opinion)
    label: str       # "Friend", "Rival", "Bully", "Prey"
```
