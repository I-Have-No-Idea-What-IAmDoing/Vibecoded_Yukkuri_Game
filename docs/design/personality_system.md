# Personality System Design

## Overview
The Personality System adds depth to Yukkuri behavior by differentiating individuals through distinct **Traits** and transient **Moods**. Instead of all Yukkuris reacting identically to hunger or social needs, personality traits will modulate their utility curves, leading to diverse behaviors.

## Core Components

### 1. Personality Traits
Traits are semi-permanent attributes assigned at birth or developed over time. They are values ranging from -1.0 to 1.0 (or 0 to 100), influencing specific Utility AI considerations.

#### Proposed Traits (Big Five adapted for Yukkuris):
*   **Greed (vs. Generosity):** Influences desire for items, food hoarding, and sharing.
    *   *High Greed:* Increases utility of `Eat` and `TakeItem` actions even when not starving.
    *   *Low Greed:* Increases utility of `Share` actions.
*   **Arrogance (vs. Humility):** Influences social dominance, aggression, and reaction to punishment.
    *   *High Arrogance:* Increases utility of `Attack` or `Mock` actions. Decreases effectiveness of discipline.
    *   *Low Arrogance:* Increases utility of `Flee` or `Apologize`.
*   **Sociality (vs. Solitary):** Influences the need for interaction.
    *   *High Sociality:* Decays `Social` stat faster, increases utility of `Play` and `Talk`.
    *   *Low Sociality:* Decays `Social` stat slower, prefers `Wander` or `Sleep`.
*   **Activity (vs. Laziness):** Influences movement and energy usage.
    *   *High Activity:* Prefers movement actions; bored easily.
    *   *Low Activity:* Prefers `Sleep` and `Idle`.
*   **Kindness (vs. Malice):** Influences reaction to others' distress.
    *   *High Kindness:* Increases utility of `Help` or `Comfort` when seeing low-health allies.
    *   *Low Kindness:* Might mock or ignore distressed allies.

### 2. Moods (Transient State)
Moods are short-term emotional states derived from Stats (`Hunger`, `Stress`, `Happiness`) and recent Events.

*   **Happy:** High Happiness, Low Stress. Boosts positive social interactions.
*   **Angry:** High Stress, Low Happiness (or High Hunger). Increases aggression.
*   **Scared:** High Stress, Low Health. Increases avoidance behaviors.
*   **Depressed:** Very Low Happiness. Reduces overall action weights (lethargy).

## Integration with Utility AI

The `UtilityAIEngine` uses `Consideration` curves to score actions. The Personality System will inject modifiers into the `context` passed to `calculate_utility`.

### Mechanism
1.  **Context Injection:** Before selecting an action, the system calculates "Effective Stats" based on Traits.
    *   `effective_hunger = actual_hunger * (1 + Greed_Factor)`
2.  **Curve Modification:** We can define specific Considerations that look at Traits directly.
    *   Action: `StealFood`
    *   Consideration: `Greed` (Linear curve). High Greed -> High score for stealing.

## Data Structure

```python
@dataclass
class Personality:
    # Traits (-1.0 to 1.0)
    greed: float = 0.0
    arrogance: float = 0.0
    sociality: float = 0.0
    activity: float = 0.0
    kindness: float = 0.0

    # Current Mood
    mood: str = "Neutral"
```

## Generation
*   **Random Generation:** Gaussian distribution centered on 0.0 for standard types.
*   **Type Bias:** Certain Yukkuri types (e.g., Marisa vs Reimu) might have shifted means (e.g., Marisas might be more Arrogant on average).
