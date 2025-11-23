# Yukkuri Personality and Relationship System Design (Consolidated)

## 1. Overview
This document presents a consolidated design for the Yukkuri Personality and Relationship System. It synthesizes the detailed relationship metrics and social dynamics from Proposal 0 with the robust, data-driven trait architecture and AI integration of Proposal 2.

The goal is to create a system where Yukkuris possess distinct personalities defined by traits (loaded from data) that influence their stats, AI decision-making curves, and social interactions, leading to emergent storytelling.

## 2. Core Concepts

### 2.1 Personality
Personality is the filter through which a Yukkuri perceives and acts upon the world.

*   **Traits**: Data-driven characteristics (e.g., `GESU`, `NICE`, `GLUTTON`) defined in TOML files. Traits provide:
    *   **Stat Modifiers**: Permanent or percentage-based changes to stats (e.g., Hunger decay rate).
    *   **AI Modifiers**: Overrides for Utility AI curves (e.g., a `LONER` trait flattens the utility curve for social needs).
    *   **Context Flags**: Simple boolean flags (e.g., `trait_GESU=1.0`) injected into the AI context for simple logic.
*   **Values**: A set of core values (0-100) representing the Yukkuri's moral compass (e.g., `compassion`, `bravery`, `greed`). These can drift over time or be reinforced by parents.
*   **Attitude**: A transient emotional state (e.g., `SCARED`, `ARROGANT`, `GRATEFUL`) derived from recent events.

### 2.2 Relationships
Relationships are tracked as a directed graph (A -> B). How A feels about B is distinct from how B feels about A.

*   **Affinity (-100 to 100)**: General like/dislike. <0 is hostility, >0 is friendship.
*   **Trust (0 to 100)**: Belief that the other entity will not harm them.
*   **Fear (0 to 100)**: Recognition of dominance or threat.
*   **Familiarity (0 to 100)**: How well they know the other. Unlocks deeper interactions.
*   **Lineage**: Explicit tracking of biological ties (Parents, Children, Mate, Clan ID).

### 2.3 Social Dynamics
Social interactions are governed by an **Interaction Matrix** and **Compatibility**.

*   **Compatibility**: Derived from comparing Traits and Values. (e.g., `NICE` likes `NICE`, `GESU` exploits `NAIVE`).
*   **Interaction Matrix**: Defines how actions modify Relationship metrics (see Section 5).
*   **Hierarchy**: Dominance is established through `Fear`. High Fear allows "Bullying" behaviors; High Affinity allows "Cooperation".

## 3. Architecture

### 3.1 Components

#### `Personality`
```python
@dataclass
class Personality:
    traits: Set[str]          # e.g., {"GESU", "GLUTTON"}
    values: Dict[str, float]  # e.g., {"compassion": 10.0}
    attitude: str = "NEUTRAL"
```

#### `RelationshipRegistry`
```python
@dataclass
class RelationshipRegistry:
    relationships: Dict[int, RelationshipData] # entity_id -> Data
    parents: List[int]
    children: List[int]
    mate_id: Optional[int]
    clan_id: Optional[int]
```

#### `RelationshipData` (Helper)
```python
@dataclass
class RelationshipData:
    affinity: float = 0.0
    trust: float = 0.0
    fear: float = 0.0
    familiarity: float = 0.0
    last_interaction_time: float
    memories: List[Memory] # Optional: List of significant events
```

### 3.2 Data Structures (TOML)
We adopt the data-driven approach from Proposal 2 for Traits.

`data/traits/traits.toml`:
```toml
[traits.GESU]
name = "Gesu"
description = "Selfish and cruel. Gains happiness from others' suffering."
conflicts = ["NICE"]

[traits.GESU.stat_modifiers]
happiness_decay = 1.2 # Harder to keep happy naturally

[traits.GESU.ai_modifiers]
# Overrides the curve for the 'Compassion' consideration to be effectively zero/negative
"Social/Compassion" = { curve = "linear", params = { m = -1.0 } }
# Boosts utility of aggressive actions
"Action/Bully" = { weight_mult = 2.0 }

[traits.GESU.interaction_modifiers]
# Custom modifiers for social calculations
social_penalty = 0.5
conflict_bonus = 1.5
```

### 3.3 AI Integration
The `UtilityAIEngine` will be enhanced to support a hybrid model:

1.  **Context Injection**:
    *   Traits and Values are flattened into the context (`trait_GESU=1.0`, `value_greed=80.0`).
    *   Relationship stats for the current target are injected (`rel_affinity`, `rel_fear`).
2.  **Curve Overrides (The "Prop 2" Feature)**:
    *   When evaluating an Action, the engine checks if the entity has Traits that override specific Consideration curves.
    *   This allows a `LONER` trait to fundamentally change *how* the AI perceives the "Social" need, rather than just adding a static score.

## 4. Interaction Matrix
The core logic for social state changes.

| Action | Affinity | Trust | Fear | Familiarity | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Share Food** | +15 | +10 | -5 | +5 | High impact if hungry. |
| **Play** | +10 | +5 | -5 | +10 | Bonding activity. |
| **Groom** | +5 | +2 | -2 | +2 | Requires existing high Affinity. |
| **Insult** | -10 | -5 | +2 | +1 | "Ugly!", "Poo-poo!". |
| **Attack (Light)** | -20 | -10 | +10 | +2 | Bumping, nipping. |
| **Attack (Heavy)** | -50 | -30 | +30 | +5 | Permanent damage likely. |
| **Puff-Up** | -5 | 0 | +10 | +1 | Intimidation check. |
| **Beg** | -5 | -5 | 0 | +1 | Lowers respect. |

*Modifiers:*
*   **`NAIVE` Receiver**: Trust gains x2, Trust losses x0.5.
*   **`COWARD` Receiver**: Fear gains x2.
*   **`GESU` Actor**: Sharing food might reduce their own Happiness (unless manipulating).

## 5. Summary of Strengths
*   **From Proposal 0**: Rich relationship metrics (Trust, Fear), Family/Lineage tracking, and the detailed Interaction Matrix.
*   **From Proposal 2**: Data-driven Trait system (TOML), flexible AI integration via Curve Overrides, and Familiarity metric.
