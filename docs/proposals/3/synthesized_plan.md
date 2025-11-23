# Synthesized Personality and Relationship System Plan

## 1. Overview

This plan synthesizes the strengths of previous proposals to create a robust, data-driven system for Yukkuri personalities and social dynamics. It combines the **rich social modeling** (Trust, Fear, Family) from Proposal 0/1 with the **flexible, data-driven trait system** (TOML modifiers, Curve overrides) of Proposal 2, while incorporating deep Yukkuri lore (Abuser/Victim dynamics, "Easy" state).

## 2. Core Concepts

### 2.1 Personality
Personality is the lens through which a Yukkuri perceives the world. It is defined by:
*   **Traits**: Discrete characteristics (e.g., `GESU`, `NOBLE`, `GLUTTON`) loaded from data files. Traits apply modifiers to:
    *   **Stats**: Decay rates, max values (e.g., Gluttons get hungry faster).
    *   **AI**: Modifying utility curves (e.g., Loners care less about social needs).
    *   **Social**: Compatibility with other traits.
*   **Values**: A set of sliding scales (0-100) representing core beliefs (e.g., `Compassion`, `Greed`). These act as multipliers for specific types of actions.
*   **Mood**: A transient emotional state (e.g., `Confident`, `Scared`, `Furious`) derived from recent history, physical needs, and the "Easy" state. Mood acts as a **filter**, altering how events are perceived (e.g., a "Furious" Yukkuri might interpret a "Greeting" as a "Taunt").

### 2.2 Relationships
Relationships are bidirectional but asymmetric records of how one Yukkuri views another.
*   **Metrics**:
    *   **Affinity (-100 to 100)**: Like/Dislike.
    *   **Trust (0 to 100)**: Confidence in safety/honesty.
    *   **Fear (0 to 100)**: Submission/Dominance metric. Critical for bully/victim dynamics.
    *   **Familiarity (0 to 100)**: Depth of knowledge about the other.
*   **Memory**: A history of significant interactions `(Timestamp, Actor, Action, EmotionalImpact)` that decay over time but shape the metrics above.
    *   **Trauma**: Memories with extreme negative impact that do not decay normally (e.g., "Abused by Humans").
*   **Lineage**: Biological ties (Parents, Children, Siblings).
*   **Family Group (Clan)**: The social unit. Yukkuris can adopt others, form "families" of unrelated individuals, or be exiled. This dictates resource sharing (nests, food).

### 2.3 Emergent Social Dynamics
Behavior emerges from the interplay of Personality and Relationships:
*   **Bullying**: High `Greed` + `Sadist` trait + Target with High `Fear`/Low `Strength`.
*   **Friendship**: High `Compatibility` -> Positive Interactions -> High `Affinity`.
*   **Hierarchy**: Established through `Fear` and `Badge` status (Gold Badge > No Badge).
*   **"Easy" State (Yukkuri Shiteite ne!)**: The core drive. High "Easy" leads to singing, dancing, and arrogance. Low "Easy" leads to stress and desperation.

## 3. Architecture & Data Structures

### 3.1 ECS Components (`src/yukkuri_game/game/yukkuri_components.py`)

#### `Personality`
```python
@dataclass
class Personality:
    traits: Set[str]             # IDs referencing TOML data
    values: Dict[str, float]     # "compassion": 50.0
    mood: str = "NEUTRAL"        # Current Mood State
    mood_score: float = 0.0      # Intensity of the mood
```

#### `RelationshipRegistry`
```python
@dataclass
class RelationshipRegistry:
    relationships: Dict[int, RelationshipData]
    # Biological Lineage
    biological_parents: List[int]
    biological_children: List[int]
    # Social Group
    family_group_id: Optional[int] = None
    mate_id: Optional[int] = None
```

#### `RelationshipData` (Helper)
```python
@dataclass
class MemoryRecord:
    timestamp: float
    actor_id: int
    action_type: str
    impact: float
    permanent: bool = False # For trauma

@dataclass
class RelationshipData:
    affinity: float = 0.0
    trust: float = 0.0
    fear: float = 0.0
    familiarity: float = 0.0
    memories: List[MemoryRecord] # Short list of recent impactful events
```

### 3.2 Data Configuration

#### `data/traits/traits.toml`
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

#### `data/ai/interactions.toml`
Defines the social consequences of actions.
```toml
[interaction.Hit]
base_impact = -20.0  # Immediate happiness hit
social_impact = { affinity = -10.0, fear = 5.0, trust = -10.0 }

[interaction.Hit.modifiers]
# If the victim is "Weak", fear increases more
"trait:WEAK" = { fear = 15.0 }
# If the victim is "Proud", affinity drops more (hatred)
"trait:PROUD" = { affinity = -30.0 }
```

## 4. Implementation Roadmap

### Phase 1: Foundations (Data & Components)
1.  **Trait & Interaction Data System**:
    *   Design `traits.toml` and `interactions.toml` schemas.
    *   Implement `TraitService` to load, validate, and **cache** these definitions for performance.
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
    *   Use cached overrides to avoid deep dictionary lookups every frame.

### Phase 3: Social Logic
1.  **Interaction System**:
    *   Implement `SocialSystem` that processes events.
    *   When Action X happens, look up `interactions.toml`.
    *   Apply `SocialEffect` to `RelationshipData`.
2.  **Memory & Decay**:
    *   Implement a system to decay relationship values over time (towards neutral).
    *   Process "Memories" to have lasting impacts on Trust/Fear.
3.  **Family Logic**:
    *   Implement `FamilyManager` to handle "Take it easy together" logic (nest sharing, food sharing).

### Phase 4: UI & Debugging
1.  **Inspector**:
    *   Visualizing the invisible: Show Traits, Values, Mood, and Relationship lines in the debug UI.
2.  **Feedback**:
    *   Visual cues (emoticons/balloons) when relationships shift significantly.

## 5. Key Advantages of Synthesized Plan
*   **Lore Accuracy**: Captures the specific "Gesu" vs "Noble" and "Predator" vs "Prey" dynamics of Yukkuri.
*   **Depth**: "Mood" and "Trauma" add layers of behavioral complexity beyond simple stat tracking.
*   **Performance**: Caching overrides ensures the deep simulation doesn't kill framerate.
