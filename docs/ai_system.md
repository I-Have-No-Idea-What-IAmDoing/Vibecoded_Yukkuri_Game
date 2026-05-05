# Unified AI Architecture

The Yukkuri Game uses a **Unified AI Architecture** that decouples decision-making (Brain), perception (Senses), and movement (Motor). This modular approach supports complex, data-driven behaviors while maintaining high performance.

## Architecture Layers

### 1. Perception Layer ("The Senses")
*   **System**: `PerceptionSystem`
*   **Data**: `Blackboard`
*   **Function**:
    *   Scans the environment using spatial hashing (via `VisibilitySystem`).
    *   Populates the **Blackboard** with visible targets (`TargetInfo`).
    *   Resolves **Social Context** (Friendly, Hostile, Neutral) based on:
        *   **Species interactions**: Predator vs Prey tags.
        *   **Family ties**: Parents/Children are friendly.
        *   **Individual relationships**: Affinity scores in `RelationshipRegistry`.
    *   Maintains **Short-Term Memory** of entities that leave the field of view.

### 2. Cognitive Layer ("The Brain")
*   **System**: `BehaviorSystem`, `UtilitySelector`
*   **Data**: `ArchetypeConfig`, `actions.toml`, `yukkuri.toml` (Archetypes)
*   **Function**:
    *   **Archetypes**: Defines personality bias, goals, and fears via TOML configuration (`data/archetypes/*.toml`).
    *   **Utility AI**: `UtilitySelector` reads the `Blackboard` and entity stats (Hunger, Stress) to score potential actions.
    *   **Behavior Tree**: Executes the chosen action (e.g., `MoveToTarget`, `Interact`) as a sequence of leaf nodes.
    *   **Traits**: Dynamic modifiers that override Utility AI curves and stat decay rates at runtime.

### 2a. Predator & Prey Dynamics
*   **Predator Component**: Defines `prey_tags` (what it eats) and `hunger_threshold`.
*   **Hunting Loop**:
    1.  **FindPrey**: Scans `Blackboard` for entities with matching tags.
    2.  **Chase**: Issues `MoveCommand` to interception point.
    3.  **Attack/Eat**: Damages prey upon contact (`dps`); consumes it to restore hunger.
*   **Prey Response**:
    *   **Fear**: Sees entities with `Predator` component or `predator_tags` as Threats.
    *   **Flee**: `UtilitySelector` prioritizes `FLEE` goal when threats are near.

### 2b. Flight AI
*   **Flight Component**: Manages `altitude`, `stamina`, and `FlightState`.
*   **Navigation**:
    *   **Takeoff**: Ascends to `max_altitude` before traveling.
    *   **Cruising**: Moves at `max_altitude` to ignore ground obstacles (mostly).
    *   **Landing**: Descends when reaching destination or `stamina` is critical.
    *   **Swooping**: Attacks drop altitude temporarily.

### 3. Motor Layer ("The Driver")
*   **System**: `SteeringSystem`
*   **Data**: `MoveCommand`, `SteeringComponent`
*   **Function**:
    *   **Decoupled Movement**: Cognitive layer issues high-level **MoveCommands** (e.g., "Go to (100, 200) with priority 2").
    *   **Force-Based Steering**: Calculates physics forces for:
        *   **Seek/Arrival**: Moving towards target.
        *   **Separation**: Avoiding crowding with neighbors.
        *   **Obstacle Avoidance**: Steering around static geometry.
    *   **Physics Integration**: Applies final velocity to `PhysicsBody`.


## Personality System

The personality system determines how Yukkuris behave socially and react to their environment. It is built on three core pillars: **Personality Axes**, **Traits**, and **Social Compatibility**.

### 1. Personality Component
Every Yukkuri has a `Personality` component that defines its base temperament using a 4-axis system. Each axis ranges from **-100 to +100**:

*   **Kindness**: Selfish (-100) <-> Kind (+100)
*   **Energy**: Lazy (-100) <-> Energetic (+100)
*   **Bravery**: Cowardly (-100) <-> Brave (+100)
*   **Greed**: Generous (-100) <-> Greedy (+100)

### 2. Traits (`TraitDefinition`)
Traits (loaded from `data/traits/traits.toml`) are named attributes like "SCUM" or "GLUTTON" that modify a Yukkuri's stats and behavior.

*   **Axis Shifts**: Permanent offsets to the personality axes (e.g., `SCUM` adds -50 Kindness, +50 Greed).
*   **Stat Modifiers**: Multipliers for stat decay/regeneration (e.g., `happiness_decay = 1.2`).
*   **AI Modifiers**: Overrides for Utility AI scoring curves (e.g., making "Eat" more urgent).
*   **Social Modifiers**: Bonuses or penalties to compatibility with other traits.

### 3. Social Compatibility
The `SocialSystem` calculates an **Action/Opinion Score** (`affinity`) to determine if two Yukkuris are friends or enemies.

**Compatibility Formula**:
1.  **Base Score**: Starts at 100.
2.  **Axis Difference**: Subtracts the average difference between their personality axes (similar personalities get along better).
3.  **Trait Modifiers**: Applies specific bonuses/penalties defined in TOML (e.g., `compatibility = { NICE = -50.0 }`).

### 4. Emotional State
The `EmotionalState` component tracks dynamic feelings, which combine with Bravery to produce complex moods:
*   **Happiness** (-100 to 100) & **Stress** (0 to 100).
*   **Derived Emotions**:
    *   **Rage**: High Stress + High Bravery.
    *   **Terror**: High Stress + Low Bravery.
    *   **Excited**: High Happiness + High Stress.

---



## Gossip System

The **Gossip System** allows AI agents to learn about events they did not personally witness, creating a dynamic reputation network.

### 1. Witnessing
When a significant event (Social Interaction, Fight, etc.) occurs, the `GossipSystem` identifies nearby entities using the **SpatialService**.
*   **Visual Witness**: Must have Line of Sight to the event.
*   **Auditory Witness**: Range based on sound magnitude (e.g. `Scream` > `Talk`).

### 2. Propagation
Witnessed events are stored in a `GossipQueue` (Priority Queue). When two entities interact socially (`Talk`, `Greet`):
*   They exchange **Gossip Packets**.
*   **Decay**: Information value decays with each transmission (hearsay is less reliable).
*   **Hearing Bonus**: Entities prioritize information from their own "Interest Group" (Family/Pack).

---

## Family System

The **Family System** simulates bonding and cooperative survival mechanics ("Take it easy together").

### 1. Formation
Families form dynamically when two un-affiliated entities achieve high social standing:
*   **Affinity** > 80.
*   **Trust** > 80.
*   Triggers family creation with a shared `family_group_id`.

### 2. Benefits
Family members within close proximity (visual range) receive passive buffs:
*   **Happiness/Stress**: Constant low-level regeneration.
*   **Resource Sharing**:
    *   **Food**: If one eats, nearby hungry family members receive satisfaction (simulated sharing).
    *   **Sleep**: Shared sleeping spots provide bonus energy recovery.

---

## Skill System

The **Skill System** manages long-term progression and specialization.

### 1. Mechanics
*   **XP Gain**: `Base * Passion * Intelligence * SoftCapMod`.
*   **Soft Caps**: Leveling slows down drastically after reaching a cap determined by Passion.
*   **Decay**: Skills lose XP over time if not used ("rusting").

### 2. Passion
Passion acts as a multiplier affecting both learning speed and interest cap:
*   **Apathetic (0.5x)**: Low cap, slow learning.
*   **Normal (1.0x)**: Standard progression.
*   **Burning (2.5x)**: Removes soft caps, rapid learning, grants Happiness when practicing.

---

## Performance & Scalability

To support large populations, the AI system integrates with LOD & Spatial Partitioning.

### Level of Detail (LOD) Throttling
The `BehaviorSystem` adjusts the tick rate of AI agents based on their `LODComponent` level (assigned by `LODSystem` based on distance/visibility):
*   **High (Level 0)**: Full update rate (e.g., 10 ticks/sec).
*   **Medium (Level 1)**: Reduced rate (e.g., 2x slower).
*   **Low (Level 2)**: Heavily throttled (e.g., 5x slower).
*   **Culled (Level 3)**: Minimal updates (e.g., 10x slower) or paused.

### Stable State Optimization
Entities in a `SUCCESS` state (e.g., reached destination, finished eating) are marked as "Stable" and ticked less frequently until their state changes to `RUNNING` or `FAILURE`.

---

## Key Components

| Component | Description |
| :--- | :--- |
| `GoalComponent` | Stores the current high-level goal (e.g., EAT, SLEEP) and queue. |
| `Blackboard` | Per-agent storage for perception results (visible targets, memory). |
| `MoveCommand` | Transient component representing a movement request. Consumed by `SteeringSystem`. |
| `ArchetypeConfig` | Static configuration loaded from TOML, defining personality and tags. |

---

## Configuration

### 1. Actions (`data/ai/actions.toml`)
Defines the available actions and their utility scoring curves.
```toml
[actions.Eat]
weight = 2.0
[[actions.Eat.considerations]]
input = "hunger"
curve = "linear"
```

### 2. Archetypes (`data/archetypes/*.toml`)
Defines personality profiles for different Yukkuri types.
```toml
archetype_id = "predator"
[priorities]
list = ["HUNT", "EAT", "SLEEP"]
[prey_tags]
tags = ["Food", "PreyType"]
```

### 3. Traits (`data/traits/traits.toml`)
Traits are modular personality modifiers that can be assigned to any Yukkuri. They integrate with the AI system in four ways:

1.  **AI Modifiers**: Override utility scoring curves for specific considerations.
2.  **Stat Modifiers**: Alter the decay or regeneration rates of stats (e.g., Hunger, Happiness).
3.  **Social Modifiers**: Define compatibility with other traits (affecting `affinity` calculations).
4.  **Skill Modifiers**: Boost learning speed or caps for specific skills.

#### Example: "Glutton" Trait
A "Glutton" yukkuri gets hungry faster and prioritizes eating even when not starving.

```toml
[traits.GLUTTON]
name = "Glutton"

# 1. Stat Modifier: Hunger decays 50% faster
[traits.GLUTTON.stat_modifiers]
hunger_decay = 1.5

# 2. AI Modifier: Changes "Survival/Eat" consideration
[traits.GLUTTON.ai_modifiers]
"Survival/Eat" = { curve = "logit", params = { k = 2.0 } }
```

In the `UtilitySelector`, if an entity has the `GLUTTON` trait, the **"Survival/Eat"** consideration uses the **logit** curve defined here instead of the default curve from `actions.toml`. This makes the desire to eat ramp up much more aggressively.

## Adding New Behaviors

### 1. Define the Action (`data/ai/actions.toml`)
Add your new action entry here. This defines how the Utility AI scores it.

```toml
[actions.Dance]
weight = 1.5
endpoint = "Dance"  # Matches the Action class name or registered ID
cooldown = 10.0

[[actions.Dance.considerations]]
input = "happiness"
curve = "logistic"  # Happy yukkuris dance!
slope = 1.0
exponent = 1.0
```

### 2. Implement Logic (`game/ai/behavior.py`)
Create a class that inherits from `Action` (or `BaseAction`).

```python
class Dance(Action):
    def on_enter(self, entity: EntityID, blackboard: Blackboard) -> None:
        # Start animation, set state
        self.animator.play(entity, "dance")
        
    def update(self, entity: EntityID, dt: float, blackboard: Blackboard) -> Status:
        # Return RUNNING while active, SUCCESS when done
        if self.timer > 5.0:
            return Status.SUCCESS
        return Status.RUNNING
```

### 3. Register the Action
Ensure your action class is registered in the factory or `BehaviorRegistry` so the system can instantiate it by name.

### 4. Update Archetypes (`data/archetypes/*.toml`)
If this action should only be available to certain types (e.g., "Flying"), add it to their allowed actions list if your system restricts actions by archetype.

---

## AI Debugging

The **AI Debug Renderer** visualizes the internal state of the AI for debugging purposes.

### Enabling It
Toggle the debug renderer (typically bound to `F3` or a specific debug key in `InputSystem`).

### Visual Legend
| Visual | Color | Meaning |
| :--- | :--- | :--- |
| **Line to Entity** | **Yellow** | The AI's current `target_id`. |
| **Line/Path** | **Cyan** | The current movement path or `MoveCommand` destination. |
| **Line to Friend** | **Green** | Friendly social relationship detected. |
| **Line to Enemy** | **Red** | Hostile/Prey/Threat relationship detected. |
| **Line to Neutral** | **Gray** | Neutral entity in perception range. |
