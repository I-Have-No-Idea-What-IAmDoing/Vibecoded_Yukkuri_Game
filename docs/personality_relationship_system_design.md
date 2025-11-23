# Yukkuri Personality and Relationship System Design

## 1. Overview
This document outlines the design for a complex personality and relationship system for the Yukkuri Game. The goal is to move beyond simple stats (Hunger, Happiness) and introduce distinct personalities, dynamic relationships, and social behaviors that mimic the "Yukkuri" lore (e.g., "Gesu", "Nice", "Deibu").

## 2. Core Concepts

### 2.1 Personality
Personality defines how a Yukkuri reacts to the world and makes decisions. It is composed of:
*   **Traits**: Discrete tags that modify behavior (e.g., `SELFISH`, `BRAVE`, `GLUTTON`).
*   **Values**: A set of core values (0-100) determining priorities.
*   **Attitude**: A transient state influenced by recent events and personality (e.g., `ARROGANT`, `SCARED`).

### 2.2 Relationships
Relationships track how a Yukkuri feels about specific other entities. This is bidirectional but asymmetric (A likes B, B hates A).
*   **Affinity**: General like/dislike (-100 to 100).
*   **Trust**: Confidence in the other's non-harmful intent (0 to 100).
*   **Fear**: Dominance hierarchy measure (0 to 100).
*   **Memory**: A log of significant interactions with that entity.

### 2.3 Family & Lineage
Explicit tracking of biological relationships:
*   **Parents**: IDs of parents.
*   **Children**: IDs of offspring.
*   **Mate**: ID of current partner.
*   **Family Group**: A social grouping ID to identify "clan" members.

## 3. Architecture

### 3.1 New Components
We will introduce new ECS components in `yukkuri_components.py`.

#### `Personality`
```python
@dataclass
class Personality:
    traits: Set[str]  # "GESU", "NICE", "PREDATOR"
    values: Dict[str, float] # "compassion": 10.0, "bravery": 50.0
    attitude: str = "NEUTRAL"
```

#### `RelationshipRegistry`
```python
@dataclass
class RelationshipRegistry:
    # Map entity_id to Relationship data
    relationships: Dict[int, RelationshipData]
    # Family data
    parents: List[int]
    children: List[int]
    mate_id: Optional[int]
```

#### `RelationshipData` (Helper Class)
```python
@dataclass
class RelationshipData:
    affinity: float = 0.0 # -100 (Hate) to 100 (Love)
    trust: float = 0.0
    fear: float = 0.0
    last_interaction_time: float = 0.0
    familiarity: float = 0.0 # Increases with time spent together
```

### 3.2 AI Integration
The `UtilitySelector` and `UtilityAIEngine` must be updated to use these new components.

#### Context Updates
The `context` dictionary passed to the `UtilityAIEngine` will now include:
*   `trait_<TRAIT_NAME>`: 1.0 if present, 0.0 otherwise.
*   `value_<VALUE_NAME>`: The float value.
*   `rel_nearest_affinity`: Affinity of the nearest Yukkuri.
*   `rel_nearest_fear`: Fear of the nearest Yukkuri.

#### Utility Modifiers
Actions in `actions.toml` (or equivalent) will have new curves/scorers based on traits.
*   *Example*: `StealFood` action:
    *   Base utility: Low.
    *   Modifier: `trait_GESU` -> Multiplies score by 2.0.
    *   Modifier: `value_compassion` -> Inverted curve (high compassion = low score).

## 4. Social Dynamics

### 4.1 First Impressions
When encountering a new entity, a base relationship is formed based on:
*   **Visuals**: Species match? (Same type = +Affinity).
*   **Personality**: `GESU` types might despise "weaker" looking ones.
*   **Charisma**: Maybe a `charm` stat derived from `quality_score`.

### 4.2 Interaction & Memory
Actions will trigger relationship updates.
*   **Share Food**: Target Affinity +, Trust +.
*   **Attack**: Target Affinity -, Fear ++.
*   **Play**: Target Affinity +, Fun +.

### 4.3 Hierarchy (The "Easy" System)
Yukkuris often obsess over "Easy" (life being easy/good).
*   **Bullying**: `GESU` types gain happiness/stress-relief by bullying low-fear targets.
*   **Begging**: Low-pride types will beg high-affinity/high-food targets.

## 5. New Behaviors (Examples)

1.  **Greeting**: Upon seeing a friend (High Affinity).
2.  **Threaten/Puff-up**: Upon seeing a low-affinity, low-fear target (Assertion of dominance).
3.  **Flee**: High fear target nearby.
4.  **Grooming/Rubbing**: Bonding activity for mates/family.
5.  **Teaching**: Parents teaching children (increases child's values/stats).

## 6. Data Structures & Configuration

### 6.1 Traits Definitions
Traits should be defined in a data file (JSON/TOML) to allow easy tweaking.
```toml
[traits.GESU]
conflict_bonus = 1.5
social_penalty = 0.5
initial_values = { compassion = 0.0, greed = 80.0 }

[traits.NICE]
conflict_bonus = 0.5
social_bonus = 1.5
initial_values = { compassion = 80.0, greed = 20.0 }
```

### 6.2 Interaction Matrix
The Interaction Matrix defines how specific social actions performed by an Actor affect the Relationship metrics (Affinity, Trust, Fear) held by the Receiver towards the Actor.

**Format**: `Action Name | Target Impact (Affinity/Trust/Fear) | Notes`

| Action Type | Affinity Change | Trust Change | Fear Change | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **Share Food** | +15.0 | +10.0 | -5.0 | High impact if Receiver is hungry. |
| **Grooming** | +5.0 | +2.0 | -2.0 | Small, frequent bonding. Requires high base affinity. |
| **Play** | +10.0 | +5.0 | -5.0 | 'Rub-rub' or chase. |
| **Attack (Light)** | -20.0 | -10.0 | +10.0 | Bumping, biting without serious intent. |
| **Attack (Heavy)** | -50.0 | -30.0 | +30.0 | Severe damage. Permanent trust damage. |
| **Insult** | -5.0 | -2.0 | +2.0 | "Ugly!", "Can't take it easy!". |
| **Theft** | -15.0 | -20.0 | +5.0 | Stealing food/objects. High trust hit. |
| **Rape/Force** | -100.0 | -100.0 | +80.0 | Extreme "Gesu" behavior. Creates "Trauma". |
| **Begging** | -5.0 | -5.0 | 0.0 | Annoyance. Receiver loses respect (Fear may drop if they were scared). |
| **Puff-Up** | -5.0 | 0.0 | +5.0 | Intimidation. Fear change depends on relative strength. |

#### 6.2.1 Trait Modifiers
Traits can multiply these base values.

*   **Receiver is `NAIVE`**: Trust gains x 2.0, Trust losses x 0.5.
*   **Receiver is `COWARD`**: Fear gains x 2.0.
*   **Receiver is `PRIDEFUL`**: Insults cause Affinity x 3.0 loss.
*   **Receiver is `GESU`**: Acts of kindness (Sharing) may be viewed as weakness (Fear -5.0) rather than friendship, or exploited.
