# Comprehensive Personality and Relationship System Plan

## 1. Overview

This plan synthesizes the strengths of previous proposals to create a robust, scalable, and data-driven Personality and Relationship system for the Yukkuri Game.

*   **From Proposal 0/1:** It adopts the detailed **Social Mechanics** (Affinity, Trust, Fear, Hierarchy), **Family/Lineage** tracking, and the concept of an **Interaction Matrix**.
*   **From Proposal 2:** It adopts the **Data-Driven Architecture** (TOML-based traits), the separation of `Personality` and `Relations` components, and the powerful **AI Integration** strategy (Traits modifying Utility AI curves).

The goal is to enable complex emergent behaviors where personality traits directly influence AI decision-making and social interactions create evolving relationship networks.

## 2. Core Concepts

### 2.1 Personality
Personality defines the internal state and behavioral bias of a Yukkuri.
*   **Traits**: Permanent or semi-permanent tags (e.g., `GESU`, `BRAVE`, `GLUTTON`) defined in `data/traits/traits.toml`.
*   **Values**: Core internal counters (e.g., `compassion`, `greed`).
*   **Attitude**: A transient state (e.g., `ANGRY`, `SCARED`) derived from recent events and current needs.

### 2.2 Relationships
Relationships track the directed history and opinion between two entities.
*   **Metrics**:
    *   **Affinity (-100 to 100)**: General like/dislike.
    *   **Trust (0 to 100)**: Confidence in non-hostility.
    *   **Fear (0 to 100)**: Dominance/Submission hierarchy.
    *   **Familiarity (0 to 100)**: Knowledge of the other entity.
*   **Lineage**: Explicit tracking of Parents, Children, Mates, and Family Group IDs.

### 2.3 Data-Driven Design
Traits are not hardcoded logic switches but data definitions that modify:
1.  **Base Stats**: (e.g., `max_health`, `move_speed`).
2.  **Decay Rates**: (e.g., `hunger_decay`).
3.  **AI Curves**: (e.g., Modifying the `Social` consideration curve to make "Loners" care less about friends).
4.  **Social Multipliers**: (e.g., How much `Affinity` is gained/lost from specific actions).

## 3. Architecture

### 3.1 ECS Components

#### `Personality`
```python
@dataclass
class Personality:
    traits: Set[str]          # Loaded from TOML IDs
    values: Dict[str, float]  # Dynamic values like 'stress', 'compassion'
    attitude: str = "NEUTRAL"
```

#### `RelationshipRegistry` (or `Relations`)
```python
@dataclass
class RelationshipData:
    affinity: float = 0.0
    trust: float = 0.0
    fear: float = 0.0
    familiarity: float = 0.0
    last_interaction: float = 0.0

@dataclass
class RelationshipRegistry:
    relationships: Dict[int, RelationshipData]
    parents: List[int]
    children: List[int]
    mate_id: Optional[int]
    family_group_id: Optional[int]
```

### 3.2 Data Storage (`data/traits/traits.toml`)

We will use the schema from Proposal 2, expanded with Proposal 0's social rules.

```toml
[traits.gesu]
name = "Gesu"
description = "Selfish and cruel. Easy is everything."
conflicts = ["nice"]

[traits.gesu.stat_modifiers]
stress_decay = 1.2 # Gets stressed easily if not 'easy'

[traits.gesu.ai_modifiers]
# Overrides AI scoring to prioritize self-gain
"Self/Greed" = { curve = "linear", params = { m = 2.0 } }

[traits.gesu.social_modifiers]
# Interaction Matrix Multipliers
receive_sharing_trust_mult = 0.5 # Doesn't trust kindness
inflict_pain_happiness_bonus = 10.0 # Sadism
```

### 3.3 AI Integration (The "Killer Feature")

The `UtilityAIEngine` will be updated to apply Trait Modifiers **before** scoring considerations.
1.  **Context Injection**: `Personality` and `Relations` data are injected into the context.
2.  **Curve Overrides**: When evaluating an Action (e.g., `Socialize`), the engine checks if any active Trait overrides the curves for the Considerations involved (e.g., `Loneliness`).

## 4. Social Dynamics & Systems

### 4.1 First Impressions
New relationships start with base values calculated from:
*   **Visual Compatibility**: Species match, Badge/Accessories.
*   **Trait Compatibility**: "Nice" likes "Nice", "Gesu" hates "Weak".
*   **Charisma**: Derived from Quality/Stats.

### 4.2 The Interaction Matrix (Social System)
A standardized way to handle social actions.
*   **Action**: `ShareFood`
*   **Base Effect**: `Affinity +15`, `Trust +10`
*   **Modifiers**:
    *   Actor Traits (e.g., `Generous` boosts effect).
    *   Receiver Traits (e.g., `Suspicious` reduces Trust gain).
    *   Current Relationship (e.g., High `Fear` might convert `Affinity` gain to `Stress`).

### 4.3 Hierarchy
*   **Bullying**: High `Fear` + Low `Affinity` = Victimization.
*   **Leadership**: High `Trust` + High `Affinity` + High `Capability`.

## 5. Implementation Phases

### Phase 1: Foundation (Data & Components)
*   **Goal**: Get the data structures in place and load traits from files.
*   **Tasks**:
    1.  Create `data/traits/traits.toml` with initial examples.
    2.  Implement `Personality` and `RelationshipRegistry` components.
    3.  Update `EntityFactory` to assign random traits and initialize empty registries.
    4.  Create `TraitService` to load and parse the TOML.

### Phase 2: AI & Stats Integration
*   **Goal**: Traits actually change how entities behave individually.
*   **Tasks**:
    1.  Update `StatDecaySystem` to use trait modifiers for hunger/fun/etc.
    2.  Update `UtilityAIEngine` to support **Curve Overrides** from traits.
    3.  Create "Test Personalities" (Loner vs. Socialite) and verify distinct AI scoring behavior.

### Phase 3: Relationship Core
*   **Goal**: Entities track opinions of each other.
*   **Tasks**:
    1.  Implement `RelationshipSystem`.
    2.  Implement `First Impressions` logic (triggered on sensing new entity).
    3.  Implement basic API: `get_affinity(a, b)`, `update_relationship(a, b, delta)`.
    4.  Debug UI: Show relationship bars in inspector.

### Phase 4: Advanced Socials (The Interaction Matrix)
*   **Goal**: Actions differ based on relationships and traits.
*   **Tasks**:
    1.  Define the `Interaction Matrix` (Action -> Base Delta).
    2.  Connect AI Actions (Eat, Sleep, Play, Attack) to the Relationship System.
    3.  Implement Trait Social Modifiers (e.g., `Gesu` reacting differently to `ShareFood`).
    4.  Implement Family/Lineage tracking (Parents/Children).

### Phase 5: Polish & Content
*   **Goal**: Create specific "Yukkuri" behaviors.
*   **Tasks**:
    1.  Add specific traits: `Gesu`, `Nice`, `Scum`, `Predator`.
    2.  Add specific behaviors: `Begging`, `PuffUp`, `Grooming`.
    3.  Tune values for balance.
