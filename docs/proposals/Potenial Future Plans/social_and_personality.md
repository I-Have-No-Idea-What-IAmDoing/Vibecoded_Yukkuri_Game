# Proposal: Social & Personality Expansion

## 1. Current System vs. Proposed Expansion

### Current System Status
The game currently implements a robust **SocialSystem** that tracks quantitative data:
- **Metrics**: `Affinity`, `Trust`, `Fear`, and `Familiarity` (0-100 scales).
- **Memory**: A "Headline" system that stores specific events (e.g., "Hit me", "Fed me") which decay over time.
- **Compatibility**: Calculated algorithmically based on the 4 Personality Axes (Kindness, Energy, Bravery, Greed). Similar personalities have higher base affinity.

### The Limitation
While the backend tracks these numbers detailedly, they lack **categorical consequences**. A Yukkuri with 80 Affinity acts largely the same as one with 40 Affinity, just with different thresholds for accepting interactions. There is no concept of "Group Mood" or ecosystem-wide social dynamics.

### The Proposal
We will layer **Named Relationship States** and **Passive Emotional Influence** on top of the existing Engine.

---

## 2. Relationship States (The Network)
Transform raw numbers into meaningful social categories that enable unique behaviors.

### Implementation Details
We will introduce specific buckets determined by the existing `Affinity` and `Trust` scores.

| State | Condition | Exclusive Behaviors |
| :--- | :--- | :--- |
| **Soulmate** | Affinity > 90, Trust > 90 | Sleep together (pile up), Grooming, Joint-Action (Explore together). |
| **Friend** | Affinity > 50, Trust > 30 | Share Food (`Feed` action), Lower social decay rate. |
| **Rival** | Affinity < 0, Competitiveness > 50 | Will actively race to items, steal food if hungry. |
| **Enemy** | Affinity < -50 | Will attack on sight, `Hit`, `Chase`. |

**New Component**: `SocialLabels` mapping `EntityID -> Enum(State)`.

---

## 3. Explicit Trait Compatibility
Enhance the algorithmic compatibility with hand-crafted drama.

### Implementation Details
Currently, compatibility is: `100 - (Axis_Difference / 4)`. We will add a **Modifier Table** in `data/traits/interactions.toml` for specific trait pairings to create "Narrative Archetypes".

- **The Bully Dynamic**: `Predator` trait + `Weak` trait = High interaction frequency but High `Fear` generation (Bullying).
- **The Echo Chamber**: `Arrogant` + `Arrogant` = Rapid `Affinity` gain initially, but massive penalty on first disagreement.
- **Opposites Attract**: `Lazy` + `Hyper` = Special interaction "Carry" where the Hyper Yukkuri drags the Lazy one around.

---

## 4. Mood Contagion (Vibe System)
A completely new system where emotions are broadcast to the environment, making population management strategic.

### Implementation Details
- **Emotional Broadcasting**: Every Entity emits an invisible "Aura" based on their `EmotionalState`.
    - *Example*: A Yukkuri with Happiness > 90 emits `Radius: 100px, Effect: +1 Happiness/sec`.
    - *Example*: A Yukkuri with Stress > 90 (Crying) emits `Radius: 300px, Effect: +2 Stress/sec`.
- **Herd Mentality**: If >50% of visible Yukkuris are "Panicked", the observer receives a massively increased Fear gain.

### Gameplay Impact
Players must quarantine "Bad Apples" (stressed/crying Yukkuris) before they start a chain reaction that depresses the entire tank. Conversely, placing a "Saint" (High kindness/happiness) in the center can calm a rowdy group.

---

## Technical Requirements
1. **Update `SocialSystem.py`**:
    - Add `_update_relationship_states(world)` to map raw stats to the new Enums.
    - Inject "State-Based" Interaction logic (e.g., `if state == ENEMY: force_interaction("Attack")`).
2. **New `AuraSystem`**:
    - A lightweight spatial query system to apply passive modifiers based on neighbors' emotional states.
3. **Data Updates**:
    - Expand `traits.toml` with specific `interacts_with = { "TraitName": modifier }` blocks.
