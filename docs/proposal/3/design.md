# Design: Hybrid Impulse-Based Movement System

## 1. Introduction

This proposal unifies the architectural clarity of Proposal 1 with the gameplay "feel" of Proposal 2. It rejects the over-engineering of the former and the physics-hacking of the latter, aiming for a pragmatic, robust, and satisfying movement system for Yukkuri entities.

## 2. Core Philosophy

*   **Intent Separation**: The AI should decide *where* to go, not *how* to move the physics body frame-by-frame.
*   **Physics-Driven**: Movement should be physical (impulses/forces), not kinematic (direct position/velocity manipulation), to ensure consistent interaction with the world.
*   **Visual Decoupling**: The "hopping" effect is primarily a visual abstraction overlaying a standard 2D physics object. We do not simulate Z-axis physics.

## 3. Architecture

We retain a simplified ECS approach to separate concerns without exploding component count.

### 3.1. Components

#### `MovementRequest` (Intent)
A lightweight component set by the AI (Behavior Tree).
```python
@dataclass
class MovementRequest:
    target_position: Optional[Vector2] = None
    target_entity: Optional[int] = None
    intended_speed: float = 0.0  # 0 to 1 normalized "effort"
    cancel_requested: bool = False
```

#### `Locomotion` (State)
Internal state for the movement system.
```python
@dataclass
class Locomotion:
    # Physics Tuning (Can be modified by Stats, but not coupled to them)
    max_speed: float = 100.0
    acceleration: float = 500.0
    friction_ground: float = 10.0
    friction_air: float = 1.0
    hop_intensity: float = 1.0

    # Internal State
    is_moving: bool = False
    hop_timer: float = 0.0      # For visual squash/stretch and drag variance
    hop_duration: float = 0.5   # Time for one full hop cycle
```

### 3.2. Systems

#### `LocomotionSystem`
This system replaces `SteeringSystem`, `NavigationSystem`, and the physics parts of `MoveToTarget`. It handles the entire pipeline in one cohesive logic block per entity, avoiding synchronization issues.

**Logic Loop per Entity:**
1.  **Resolve Target**: If `target_entity` is present in `MovementRequest`, update `target_position`.
2.  **Determine Desire**: Calculate vector to `target_position`.
3.  **Apply "Hop" Drag**:
    *   Instead of simulated Z-gravity, we use a cyclic drag modifier.
    *   `hop_timer` cycles from 0.0 to `hop_duration`.
    *   **Phase 1 (Push)**: High drag, apply Force/Impulse towards target. (Entity "kicks" the ground).
    *   **Phase 2 (Glide)**: Low drag. (Entity "slides/hops" through the air).
    *   **Phase 3 (Land)**: High drag. (Entity "brakes" on landing).
4.  **Apply Physics**: Use Pymunk's `apply_force` or `apply_impulse`.
    *   *Crucial*: We do *not* touch Z-axis. The entity is always a circle sliding on the ground.
5.  **Visuals**: Write to a `VisualOffset` component (y-axis offset) based on `hop_timer` to simulate the visual arc of the hop.

### 4. Integration with Gameplay

#### 4.1. Stat Integration (The "Bridge")
We do not import `YukkuriStats` into `LocomotionSystem`. Instead, a `StatSyncSystem` runs infrequently (e.g., once per second or on stat change) to update `Locomotion` parameters.
*   `Stats.Energy` low -> reduce `Locomotion.max_speed` and `Locomotion.hop_intensity`.
*   `Stats.Weight` high -> increase `Locomotion.friction_ground` (drag).

#### 4.2. Pathfinding
For long-distance travel, the AI uses a separate service to generate waypoints. The `MovementRequest` is simply updated to the *next waypoint* in the chain. This keeps pathfinding out of the tight physics loop.

## 5. Addressing Previous Critiques

*   **vs. Proposal 1**:
    *   Reduces 4 new systems to 1 (`LocomotionSystem`).
    *   Keeps the `MovementRequest` decoupling but removes the `Path` management overhead from the core loop.
*   **vs. Proposal 2**:
    *   Removes "Z-axis Hell". Physics remains strictly 2D.
    *   Removes "Overshooting" by using cyclic drag rather than ballistic trajectories. The entity can still steer during the "Glide" phase, just with reduced authority (simulating air control), preventing frustration.
    *   Decouples Stats from Physics via the `Locomotion` component data-bag.

## 6. Implementation Plan

1.  **Refactor**: Extract movement logic from `MoveToTarget` into `MovementRequest` component.
2.  **Create**: Implement `LocomotionSystem` with the cyclic drag/impulse model.
3.  **Visuals**: Implement the purely visual Y-offset for sprite rendering based on the hop cycle.
4.  **Tune**: Adjust `friction_ground` vs `friction_air` ratios to get the "bouncy" feel without losing control.
