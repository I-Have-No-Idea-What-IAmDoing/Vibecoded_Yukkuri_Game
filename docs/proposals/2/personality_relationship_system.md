# Personality and Relationship System Design

## 1. Overview

This document details the design for a complex personality and relationship system for the Yukkuri Raising Game. The goal is to move beyond identical entities by introducing **Traits** and **Dynamic Relationships**, enabling emergent gameplay where Reimus and Marisas behave differently based on their personalities and history.

## 2. Core Concepts

### 2.1 Personality Traits
Traits are distinct characteristics that modify a Yukkuri's stats, needs, and decision-making.

*   **Definition**: Traits are data-driven definitions loaded from TOML.
*   **Assignment**:
    *   **Innate**: Defined by Yukkuri Type (e.g., Marisas might have a higher chance of "Energetic").
    *   **Random**: Assigned at birth/creation based on chance.
    *   **Acquired**: Gained through life events (e.g., "Traumatized" after severe abuse).
*   **Effects**:
    *   **Stat Modifiers**: Permanent buffers/debuffers to max stats (e.g., `max_happiness + 10`).
    *   **Decay/Growth Modifiers**: Multipliers for stat changes over time (e.g., `hunger_decay * 1.5` for "Glutton").
    *   **Consideration Modifiers**: Alters the input curves for Utility AI (e.g., "Loner" makes the `Social` curve flatter or shifts the threshold).
    *   **Interaction Modifiers**: Unlocks or bans specific interactions (e.g., "Mean" unlocks "Insult").

### 2.2 Relationships
Relationships track the social standing between two specific entities.

*   **Structure**: A directed graph where edge weights represent `Affinity` (Opinion).
    *   `Entity A -> Entity B: { affinity: 50, familiarity: 10, memories: [...] }`
*   **Metrics**:
    *   **Affinity (-100 to +100)**: How much A likes B.
        *   > 50: Friend
        *   < -50: Enemy
    *   **Familiarity (0 to 100)**: How well A knows B. Affects interaction success rates (e.g., "Deep Talk" requires high familiarity).
*   **Dynamics**:
    *   **Compatibility**: Base affinity derived from Personality Traits (e.g., "Energetic" likes "Energetic", "Lazy" dislikes "Energetic").
    *   **Interactions**: Events modify affinity (e.g., "Talk" success -> +5 Affinity).
    *   **Decay**: Affinity drifts towards 0 (neutral) over very long periods if no interaction occurs.

### 2.3 Memory System
Short-term and long-term memory of events to influence current decisions.

*   **Memories**: Records of significant interactions.
    *   `{ type: "insulted_me", actor: B, value: -10, timestamp: 1200, decay: 0.99 }`
*   **Aggregation**: When calculating Affinity, active memories are summed up.

## 3. Architecture

### 3.1 New Components

#### `Personality` Component
```python
@dataclass
class Personality:
    traits: List[str] # List of Trait IDs, e.g., ["lazy", "glutton"]
```

#### `Relations` Component
```python
@dataclass
class RelationshipData:
    target_id: int
    affinity: float = 0.0
    familiarity: float = 0.0
    # Potential optimization: keep a small list of recent interactions

@dataclass
class Relations:
    # Map target_entity_id -> RelationshipData
    relationships: Dict[int, RelationshipData]
```

### 3.2 Data Structures (TOML)

#### `data/traits/traits.toml`
```toml
[traits.glutton]
name = "Glutton"
description = "Hunger decays 50% faster, but eating gives more happiness."
conflicts = ["anorexic"]

[traits.glutton.stat_modifiers]
hunger_decay = 1.5

[traits.glutton.interaction_modifiers]
eat_happiness_mult = 1.2

[traits.loner]
name = "Loner"
description = "Social need decays slower. Prefers being alone."

[traits.loner.ai_modifiers]
# Modifies the 'Loneliness' consideration in Utility AI
"Social/Loneliness" = { curve = "logit", params = { x0 = 0.2 } } # Shifts curve so they don't feel lonely until very low
```

### 3.3 System Updates

#### `UtilitySelector` (Update)
*   **Before**: Uses `stats.hunger`, `nearby_friends` count.
*   **After**:
    1.  Apply `Personality` modifiers to input values (e.g., if "Loner", `social_inv` input is reduced).
    2.  Apply `Personality` modifiers to Consideration Curves (overwrite parameters).

#### `SocialSystem` (New)
*   Handles `interact_social` effects.
*   Calculates success chance:
    *   `Base Chance` + `Compatibility` + `Current Mood` + `Relationship Affinity`.
*   Updates `Relations` component on both parties.

## 4. Emergent Behavior Examples

1.  **The Bully**:
    *   **Trait**: "Mean" (Likes negative interactions), "Strong" (High Health).
    *   **Behavior**: Utility AI prioritizes "Fight" or "Insult" actions because "Mean" trait boosts the weight of aggressive actions or derives "Fun" from them.
    *   **Outcome**: Terrorizes weaker Yukkuris.

2.  **The Best Friends**:
    *   **Scenario**: Two Yukkuris share the "Otaku" trait (high compatibility).
    *   **Behavior**: High compatibility -> High initial Affinity -> High success rate for "Talk".
    *   **Loop**: They talk -> Affinity up -> More likely to talk again -> They stick together.

3.  **The Loner**:
    *   **Trait**: "Loner".
    *   **Behavior**: Social need decays slowly. Even when low, the "Loner" curve modifier means the AI doesn't score "Talk" highly.
    *   **Outcome**: Wanders alone, ignores social gatherings.

## 5. Rationale

*   **Composition over Inheritance**: Using ECS components (`Personality`, `Relations`) allows mixing and matching without complex class hierarchies.
*   **Data-Driven**: Traits defined in TOML allow designers/modders to create complex personalities without coding.
*   **Utility AI Integration**: The existing Utility AI is perfect for this. Traits simply modify the *curves* and *weights* of considerations, naturally biasing behavior without hard-coded "If Loner then..." logic strings.
