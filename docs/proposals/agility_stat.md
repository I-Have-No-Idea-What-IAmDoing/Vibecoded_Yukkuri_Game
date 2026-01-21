# Proposal: Agility Stat for Yukkuris (Revised V4)

## 1. Overview
This proposal introduces an **Agility** stat to the `YukkuriStats` component. It acts as a global physical multiplier affecting movement, flight, animation speed, combat evasion, fall safety, and perceptual reaction time.

## 2. Goals
-   **Differentiation**: Distinguish between "clumsy/slow" and "nimble/reactive" Yukkuris.
-   **Game Feel**: Agile Yukkuris look and act faster.
-   **Survivability**: Multifaceted survival benefits.

## 3. Data Structure Changes
### `game/yukkuri_components.py`
```python
@dataclass(slots=True)
class YukkuriStats(Component):
    agility: float = 1.0  # Default 1.0. Range: 0.5 (Slow) to 2.0 (Fast)

@dataclass(slots=True)
class TargetInfo:
    # ...
    detected_at: float = 0.0  # Timestamp when first seen
```

## 4. Systems Integration

### 4.1. Movement & Physics
-   **Steering**: Multiply `max_speed` by `agility`.
-   **Kinematic**: Multiply `acceleration` by `agility`.

### 4.2. Flight System
-   **Performance**: Multiply `vertical_speed` by `agility`.
-   **Efficiency**: Divide `fly_cost`/`hover_cost` by `agility`.
-   **Safety**: Divide Fall Damage/Stress by `agility`.

### 4.3. Animation System
-   **Visuals**: Multiply playback speed by `agility` (Capped at 1.5x).

### 4.4. Interaction (Combat)
-   **Evasion**: If `target.agility > predator.agility * 1.5`, avoidance succeeds (spawn "Miss!" text).

### 4.5. Perception System (Reflexes)
-   **Logic**: Instead of changing update frequency, we implement **Reaction Buffering**.
-   **Mechanism**:
    -   New targets entering the field of view are timestamped (`detected_at`).
    -   AI "Census" (counting threats/food) ignores targets until `(now - detected_at) > (BaseReactionTime / Agility)`.
    -   *BaseReactionTime* = 0.5s.
    -   *Agility 2.0* -> 0.25s delay.
    -   *Agility 0.5* -> 1.0s delay.
-   **Result**: Agile Yukkuris notice and react to threats faster without changing system tick rates.

## 5. Relationship with Athletics Skill
-   **Synergy**: Agility (Hardware) accelerates learning of Athletics (Software).

## 6. Implementation Plan
1.  **Data**: Add `agility` to `YukkuriStats`, `detected_at` to `TargetInfo`.
2.  **Movement**: Update Steering/Kinematic systems.
3.  **Flight**: Update FlightSystem.
4.  **Animation**: Update AnimationSystem with cap.
5.  **Combat**: Update InteractionSystem (Dodge).
6.  **Perception**: Update `PerceptionSystem` to implement Reaction Buffering logic in `_update_blackboard`.
