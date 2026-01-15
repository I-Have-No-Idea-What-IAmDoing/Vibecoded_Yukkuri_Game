# Critique of Proposal 4: The Unified AI Architecture

## Strengths

1.  **Strong Synthesis**: Successfully combines the **Layered ECS** of Proposal 2 with the **Centralized Perception** of Proposal 3.
2.  **Explicit Data Flow**: The `Sensors -> Blackboard -> Utility -> Behavior -> Motor` pipeline is clear and enforceable.
3.  **Flight Integration**: The inclusion of flight mechanics and stamina states is a significant addition that feels naturally integrated into the specific "Motor" layer.
4.  **Failure Cascades**: Explicitly defining what happens when `MoveToTarget` fails prevents the common "stuck AI" problem.

## Areas for Improvement

### 1. The "Sleep" Gap in Needs
*   **Issue**: The Archetype configuration lists `SLEEP` as a high-priority action, and `NeedsComponent` lists `Hunger` and `Stress`. However, there is no `Energy` or `Sleepiness` value defined in the `NeedsComponent`.
*   **Risk**: Without a variable tracking energy, the `SLEEP` priority cannot be dynamically scored by the Utility System.
*   **Suggestion**: Add `energy` (0-100) to `NeedsComponent`. Low energy increases the score of `SLEEP` actions.

### 2. LOD "Wakeup" Mechanism
*   **Issue**: Tier 3 (Dormant) entities have "Sensing: Disabled". If sensing is disabled, they cannot detect when the player or another entity approaches to transition *back* to Tier 2 or 1.
*   **Risk**: Distant entities might remain frozen even when the player stands right next to them if they were previously categorized as "Far".
*   **Suggestion**: Introduce a lightweight **Global Partition System** or **Proximity Manager** that runs entirely separate from the entity sensing to forcefully update Tiers based on player distance, even if the entity's internal sensing is off.

### 3. Flight Stamina vs. Ground Exertion
*   **Issue**: `Stamina` is currently described primarily for Flight. However, high-intensity ground actions (Fleeing from predators) should likely also consume resources.
*   **Risk**: A ground-based Yukkuri could run away indefinitely without tiring, while a flying one gets tired.
*   **Suggestion**: Generalize `StaminaComponent` to cover all physical exertion. Walking/Idle recovers stamina. Run/Fly/Flee drains it.

### 4. Social Nuance (Personalities)
*   **Issue**: The Social Context table uses `Affinity` and `FamilyID`. It misses the "Personality" aspect (e.g., "Scum" vs "Nice") which is core to Yukkuri gameplay.
*   **Risk**: All Yukkuris of the same type will behave identically towards the player.
*   **Suggestion**: Add a `PersonalityComponent` (e.g., `arrogance`, `kindness`). This feeds into the `UtilitySystem`—an arrogant Yukkuri might score `DemandFood` higher than `BegForFood`.

### 5. Command Expiration
*   **Issue**: `CommandComponents` persist until overwritten. If a lag spike occurs or a logic error prevents an update, a `MoveCommand` might persist longer than intended.
*   **Suggestion**: Add a `creation_time` or `expiration` to commands. The Motor system should discard stale commands (> 0.5s old).

## Verdict
Proposal 4 is **Excellent** and ready for implementation, pending the minor additions of **Energy/Sleep Needs**, a **Wakeup Mechanism** for LOD, and **Personality** factors in the Utility layer.
