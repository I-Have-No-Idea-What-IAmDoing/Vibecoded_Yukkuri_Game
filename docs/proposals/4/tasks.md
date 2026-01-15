# Implementation Plan: Unified AI Architecture (Final)

## Phase 1: Foundation & Tooling
- [ ] **Data & Config**
    - [ ] Create `ai_config.toml` (Archetypes, detailed Stats).
    - [ ] Define `GoalComponent`, `Blackboard`, `StaminaComponent`, `SocialComponent`.
    - [ ] Define `PersonalityComponent` and `NeedsComponent` (Add Energy).
    - [ ] **Events**: Define `DamageTakenEvent`, `GoalFailureEvent` in `events.py`.
    - [ ] **Config Validator**: Implement `ArchetypeSchema` with `Pydantic` or custom checks.
        - [ ] Add Safe Loader with defaults/logging.
- [ ] **Debug System** (High Priority)
    - [ ] Create `AIDebugSystem`.
    - [ ] Implement `render_social_lines`, `render_stamina_bar`, `render_goal_vector`.
    - [ ] Add `toggle_debug_overlay` keybind.
    - [ ] Implement `MoveCommand` expiration logic.

## Phase 2: The Motor Layer
- [ ] **Navigation Infrastructure**
    - [ ] Implement `AsyncPathfindingManager` with Priority Queue & Budget.
- [ ] **Steering & Physics**
    - [ ] Implement `SteeringSystem` (Seek, Separate, Avoid).
    - [ ] **StuckMonitor**: Detect low displacement vs high velocity. Implement Unwedge/Teleport.
    - [ ] **Flight**: Implement `FlyingLocomotion` with States (`Takeoff`, `Land`).
    - [ ] **Stamina**: Implement drain/regen logic in `LocomotionSystem` (Run/Fly).
    - [ ] **Grounded**: Implement terrain adhesion.
    - [ ] **Events**: Publish `StaminaDepletedEvent`.

## Phase 3: Perception, Social & LOD
- [ ] **Sensing Engine**
    - [ ] Implement `PerceptionSystem` with Spatial Hashing.
    - [ ] Add **Vision Bonuses** based on Altitude.
- [ ] **Social Brain**
    - [ ] Implement `SocialContext` logic (Query `RelationshipRegistry`).
    - [ ] Override `Friend`/`Foe` logic based on Affinity > 50.
    - [ ] Load relationships from `ai_config.toml`.
    - [ ] Implement `Personality` bias in utility scoring.
- [ ] **LOD Manager**
    - [ ] Create `LODSystem` (Tier 0-3).
    - [ ] Implement `ProximityManager` for global wakeup checks.
    - [ ] **Watchdog**: Implement `StateValidationSystem` (1Hz invariant checks).

## Phase 4: Strategy & Decision
- [ ] **Primitives**
    - [ ] `ChannelAction` (Generic interact with visual bar).
        - [ ] Subscribe to `DamageTakenEvent` for interrupts.
    - [ ] `EatAction` (Uses Channeling, applies Vulnerable).
    - [ ] `SwoopAction` (Flight specific attack).
- [ ] **Strategies**
    - [ ] `HuntStrategy`: Patrol -> Swoop -> Channel Eat.
        - [ ] Handle `GoalFailureEvent`.
    - [ ] `SocializeStrategy`: Seek Friend -> Channel Rub/Play.
- [ ] **Utility**
    - [ ] Implement `UtilitySystem` with Social inputs.

## Phase 5: Cleanup
- [ ] Remove legacy `behavior.py` classes.
- [ ] Run Performance Benchmark (100 vs 500 entities).

