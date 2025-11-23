# Relationship System Design

## Overview
The Relationship System tracks how Yukkuris perceive one another, enabling complex social dynamics like friendships, rivalries, bullying, and family formation. It moves beyond simple "faction" logic to individual-level relationships.

## Core Components

### 1. Relationship Metrics
Relationships are directed. If Yukkuri A knows Yukkuri B, A holds a `Relationship` object for B containing:

*   **Affection (Love <-> Hate):** (-100 to 100)
    *   High: Will share food, play, protect.
    *   Low: Will ignore, insult, or attack.
*   **Dominance (Superior <-> Inferior):** (-100 to 100)
    *   High (I am superior): Demands food, expects submission.
    *   Low (I am inferior): Offers food, flees if threatened.
*   **Trust (Safe <-> Dangerous):** (-100 to 100)
    *   High: Will sleep near, allow close proximity.
    *   Low: Will flee or fight preemptively.

### 2. The Relationship Graph
Each Yukkuri entity will possess a `SocialMemory` component acting as a local graph of known entities.

```python
@dataclass
class Relationship:
    entity_id: int
    affection: float = 0.0
    dominance: float = 0.0
    trust: float = 0.0
    last_interaction_time: float = 0.0

@dataclass
class SocialMemory:
    # Map of target_entity_id -> Relationship
    relationships: Dict[int, Relationship]
```

## Interaction Dynamics

### Forming Relationships
*   **First Sight:** When a Yukkuri perceives a new entity, a neutral (or type-biased) relationship is created.
*   **Decay:** Relationships not refreshed by interaction may decay towards neutral over time (forgetting).

### Modifying Relationships
Interactions trigger relationship updates:
*   **Action: Play** -> Success -> Both gain Affection.
*   **Action: Attack** ->
    *   Attacker: Gains Dominance (if won).
    *   Victim: Loses Affection, Loses Trust, Loses Dominance.
*   **Action: Share Food** -> Receiver gains Affection and Trust.

### Impact on Utility AI
The Utility AI `context` will be enriched with relationship data regarding the `current_target`.

*   **Target Selection:** When choosing a target for "Play", filter by High Affection.
*   **Action Weighting:**
    *   `Attack`: Weighted positively if `Dominance` is High (bullying) or `Affection` is Low (hating).
    *   `Flee`: Weighted positively if `Trust` is Low (fear).

## Special States
*   **Family/Clan:** Extremely high Affection + Trust.
*   **Nemesis:** Extremely low Affection.
*   **Pet/Slave:** High Dominance + specific interactions.

## Emergence Examples
1.  **Bullying Cycle:** A High Arrogance Yukkuri meets a Low Arrogance one. High Dominance leads to demands. Low Dominance leads to submission. The cycle reinforces itself.
2.  **Jealousy:** A Yukkuri sees their Friend (High Affection) playing with an Enemy (Low Affection).
