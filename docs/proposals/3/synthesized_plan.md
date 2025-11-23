# Synthesized Personality and Relationship System Plan

## 1. Overview

This plan synthesizes the strengths of previous proposals to create a robust, data-driven system for Yukkuri personalities and social dynamics. It combines the **rich social modeling** (Trust, Fear, Family) from Proposal 0/1 with the **flexible, data-driven trait system** (TOML modifiers, Curve overrides) of Proposal 2.

## 2. Core Concepts

### 2.1 Personality
Personality is the lens through which a Yukkuri perceives the world. It is defined by:
*   **Traits**: Discrete characteristics (e.g., `GESU`, `NOBLE`, `GLUTTON`) loaded from data files. Traits apply modifiers to:
    *   **Stats**: Decay rates, max values (e.g., Gluttons get hungry faster).
    *   **AI**: Modifying utility curves (e.g., Loners care less about social needs).
    *   **Social**: Compatibility with other traits.
*   **Values**: A set of sliding scales (0-100) representing core beliefs (e.g., `Compassion`, `Greed`). These act as multipliers for specific types of actions.
*   **Attitude**: A transient emotional state (e.g., `Confident`, `Scared`) derived from recent history and current status.

### 2.2 Relationships
Relationships are bidirectional but asymmetric records of how one Yukkuri views another.
*   **Metrics**:
    *   **Affinity (-100 to 100)**: Like/Dislike.
    *   **Trust (0 to 100)**: Confidence in safety/honesty.
    *   **Fear (0 to 100)**: Submission/Dominance metric.
    *   **Familiarity (0 to 100)**: Depth of knowledge about the other.
*   **Memory**: A history of significant interactions that decay over time but shape the metrics above.
*   **Lineage**: Explicit tracking of biological ties (Parents, Children, Mates) which influences base Affinity and Duty.

### 2.3 Emergent Social Dynamics
Behavior emerges from the interplay of Personality and Relationships:
*   **Bullying**: High `Greed` + `Sadist` trait + Target with High `Fear`.
*   **Friendship**: High `Compatibility` -> Positive Interactions -> High `Affinity`.
*   **Hierarchy**: Established through `Fear` and `Strength` differentials.

## 3. Architecture & Data Structures

### 3.1 ECS Components (`src/yukkuri_game/game/yukkuri_components.py`)

#### `Personality`
```python
@dataclass
class Personality:
    traits: Set[str]             # IDs referencing TOML data
    values: Dict[str, float]     # "compassion": 50.0
    attitude: str = "NEUTRAL"
```

#### `RelationshipRegistry`
```python
@dataclass
class RelationshipRegistry:
    relationships: Dict[int, RelationshipData]
    # Lineage
    parents: List[int]
    children: List[int]
    mate_id: Optional[int] = None
    family_group_id: Optional[int] = None
```

#### `RelationshipData` (Helper)
```python
@dataclass
class RelationshipData:
    affinity: float = 0.0
    trust: float = 0.0
    fear: float = 0.0
    familiarity: float = 0.0
    memories: List[MemoryRecord] # Short list of recent impactful events
```

### 3.2 Data Configuration (`data/traits/traits.toml`)

We adopt the data-driven approach from Proposal 2.

```toml
[traits.GESU]
name = "Gesu"
description = "Selfish and cruel. Gains happiness from others' suffering."
conflicts = ["NICE"]

[traits.GESU.stat_modifiers]
happiness_decay = 1.2  # Harder to stay happy
stress_recovery = 1.5  # Recovers stress fast (usually by abusing others)

[traits.GESU.ai_modifiers]
# Overrides the curve for 'Empathy' consideration to be non-existent or inverted
"Social/Empathy" = { curve = "linear", params = { m = -1.0 } }

[traits.GESU.social_modifiers]
compatibility = { NICE = -50.0, GESU = 10.0 }
```

## 4. Implementation Roadmap

### Phase 1: Foundations (Data & Components)
1.  **Trait Data System**:
    *   Design `traits.toml` schema.
    *   Implement `TraitService` to load and validate traits.
2.  **Component Implementation**:
    *   Add `Personality` and `RelationshipRegistry` to `yukkuri_components.py`.
    *   Define `RelationshipData` and `MemoryRecord` structures.
3.  **Factory Integration**:
    *   Update `EntityFactory` to generate personalities.
    *   Implement genetics/randomization logic (e.g., Child inherits traits from parents).

### Phase 2: AI Engine Upgrades
1.  **Context Injection**:
    *   Update `UtilitySelector` to flatten `Personality` data into the context (`trait_GESU=1.0`, `val_greed=80`).
2.  **Curve Overrides (The "Secret Sauce")**:
    *   Modify `UtilityAIEngine` to accept `TraitService`.
    *   Before scoring a Consideration, check if the entity's active traits define an override for that Consideration.
    *   If so, use the Trait's curve/parameters instead of the default. This allows "Loner" to fundamentally change how "Social Need" is valued without complex code branching.

### Phase 3: Social Logic
1.  **Interaction Matrix**:
    *   Define a system where Actions (Eat, Hit, Play) produce `SocialEffects`.
    *   `SocialEffect` -> Updates Affinity/Trust/Fear on the target.
2.  **Memory & Decay**:
    *   Implement a system to decay relationship values over time (towards neutral).
    *   Process "Memories" to have lasting impacts on Trust/Fear.

### Phase 4: UI & Debugging
1.  **Inspector**:
    *   Visualizing the invisible: Show Traits, Values, and Relationship lines in the debug UI.
2.  **Feedback**:
    *   Visual cues (emoticons) when relationships shift significantly.

## 5. Key Advantages of Synthesized Plan
*   **Depth**: Retains the "Trust/Fear" axis which is critical for Yukkuri lore (abuser vs victim dynamics).
*   **Flexibility**: Uses the TOML-based Curve Override system to allow massive behavioral differences without hardcoding logic in Python.
*   **Simulation**: Tracks lineage for "Family" behavior, adding emotional weight to gameplay.
