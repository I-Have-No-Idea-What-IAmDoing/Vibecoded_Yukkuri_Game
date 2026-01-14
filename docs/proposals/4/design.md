# Proposal 4: Unified Mobility and Predation System (Technical Specification)

## 1. Executive Summary

This document serves as the **Technical Specification** for implementing Flying and Predator Yukkuris. It synthesizes the best components of previous proposals into a concrete implementation plan using the existing Entity Component System (ECS).

**Core Dependencies:** `pymunk` (Physics), `pygame_light2d` (Rendering), `py_trees` (AI).

---

## 2. Data & Component Architecture

### 2.1. Mobility Components
**File:** `src/yukkuri_game/game/yukkuri_components.py`

#### `FlightState` (Enum)
```python
class FlightState(Enum):
    GROUNDED = 0   # Walking/Idle on ground
    TAKEOFF = 1    # Ascending (Altitude < Max)
    FLYING = 2     # Cruising (Altitude ~= Max)
    HOVERING = 3   # Stationary in air (Reduced Stamina Cost)
    LANDING = 4    # Descending (Altitude > 0)
    SWOOPING = 5   # Rapid attack descent (Altitude -> 0 temporarily)
    FALLING = 6    # Out of stamina/Stunned. Gravity applies full force.
```

#### `Flight` (Component)
```python
@dataclass(slots=True)
class Flight(Component):
    altitude: float = 0.0          # Current visual height (0.0 to max_altitude)
    max_altitude: float = 60.0     # Target height for cruising
    vertical_speed: float = 20.0   # Units per second for ascent/descent
    
    stamina: float = 100.0
    max_stamina: float = 100.0
    
    # Configuration
    fly_cost: float = 5.0          # Stamina drain/sec while moving in air
    hover_cost: float = 1.0        # Stamina drain/sec while stationary
    recovery_rate: float = 10.0    # Stamina gain/sec while GROUNDED
    
    state: FlightState = FlightState.GROUNDED
```

### 2.2. Behavioral Components
**File:** `src/yukkuri_game/game/yukkuri_components.py`

#### `Predator` (Component)
```python
@dataclass(slots=True)
class Predator(Component):
    # Detection
    prey_tags: set[str] = field(default_factory=set) # e.g., {"Prey", "Weak"}
    prey_sense_radius: float = 300.0                 # Detection range (bypasses some occlusion)
    
    # Drive
    hunger_threshold: float = 60.0    # Hunting starts when hunger > this
    aggression: float = 1.0           # Multiplier for deciding to attack
```

---

## 3. Systems Implementation

### 3.1. Physics & Collision (Pymunk)
**File:** `src/yukkuri_game/game/systems/physics.py` & `collision_constants.py`

We utilize **Collision Bitmasks** to handle "3D" logic in a 2D engine.

**Collision Categories (Bitflags):**
```python
# collision_constants.py
CAT_GROUND_UNIT   = 0b0000_0001
CAT_FLYING_UNIT   = 0b0000_0010
CAT_LOW_OBSTACLE  = 0b0000_0100  # Fences, Small Rocks, Toys
CAT_HIGH_OBSTACLE = 0b0000_1000  # Walls, Buildings, Map Borders
CAT_WATER         = 0b0001_0000  # Water bodies
CAT_SENSOR        = 0b1000_0000  # For vision/interaction checks
```

**Dynamic Mask Updates (`KinematicMovementSystem`):**
In `KinematicMovementSystem.update()`:
1.  Check `Flight` component `state`.
2.  **Case A: GROUNDED / LANDING / TAKEOFF (Low Altitude)**
    *   `shape.filter = ShapeFilter(categories=CAT_GROUND_UNIT, mask=CAT_GROUND_UNIT | CAT_LOW_OBSTACLE | CAT_HIGH_OBSTACLE | CAT_WATER)`
3.  **Case B: FLYING / HOVERING (High Altitude)**
    *   `shape.filter = ShapeFilter(categories=CAT_FLYING_UNIT, mask=CAT_FLYING_UNIT | CAT_HIGH_OBSTACLE)`
4.  **Case C: SWOOPING (Attack)**
    *   `shape.filter = ShapeFilter(categories=CAT_FLYING_UNIT, mask=CAT_GROUND_UNIT | CAT_LOW_OBSTACLE | CAT_HIGH_OBSTACLE)`
    *   *Risk*: Swooping re-enables collisions with low obstacles. Badly timed swoops can cause crashes.

### 3.2. Navigation (Traversal Service)
**File:** `src/yukkuri_game/game/services/navigation_service.py`

The pathfinding grid nodes (A*) must store a `traversal_mask`.

**Node Data:**
*   `access_flags: int` (Bitmask of compatible movement types)
    *   `FLAG_WALK = 0x1`
    *   `FLAG_FLY = 0x2`
    *   `FLAG_SWIM = 0x4`

**Algorithm Update (`find_path`):**
```python
def find_path(self, start, end, capability_mask: int):
    # During neighbor expansion:
    if not (neighbor_node.access_flags & capability_mask):
        continue # Skip nodes this unit cannot traverse
```
*   Ground Unit calls with `FLAG_WALK`.
*   Flying Unit calls with `FLAG_FLY`.

### 3.3. Rendering (Visual Feedback)
**File:** `src/yukkuri_game/game/systems/render_system.py`

**Sprite Offset:**
*   In `_process_entity`, utilize `VisualTransform.vertical_offset`.
*   `VisualTransform.vertical_offset = Flight.altitude` (set by `VisualMovementSystem` or `KinematicMovementSystem`).

**Shadow Scaling Formula:**
To create depth, the shadow must shrink and fade as the entity rises.
```python
# RenderSystem._process_entity
if visual.has_drop_shadow:
    # 0.0 at ground, 1.0 at max_altitude
    height_factor = clamp(flight.altitude / flight.max_altitude, 0.0, 1.0)
    
    # Scale: 100% -> 60% size
    current_shadow_scale = base_shadow_scale * (1.0 - (0.4 * height_factor))
    
    # Alpha: 255 -> 150 opacity
    current_shadow_alpha = 255 * (1.0 - (0.4 * height_factor))
    
    # Render shadow at (world_x, world_y) with calculated scale/alpha
```

---

## 4. AI & Behavior Trees (`py_trees`)
**File:** `src/yukkuri_game/game/ai/behavior.py`

### 4.1. New Goal: `HuntPrey`
**Priority:** High (Below `SelfPreservation`, Above `Wander`).
**Structure:**
*   **Selector**: `HuntPrey`
    *   **Sequence**: `ExecuteHunt`
        *   **Condition**: `IsHungry` (Hunger > `Predator.hunger_threshold`)
        *   **Action**: `FindPrey` (Sets `blackboard.target_id`)
            *   *Logic*: Scan `Vision` for entities with `tags` matching `Predator.prey_tags`.
            *   *Priority*: Closest valid target.
        *   **Selector**: `ApproachAndStrike`
            *   **Sequence**: `AerialAssault` (If Flying)
                *   **Action**: `FlyToTarget` (Ignore obstacles)
                *   **Action**: `Swoop` (Transition state to `SWOOPING`, altitude -> 0)
            *   **Sequence**: `GroundAssault` (If Grounded)
                *   **Action**: `MoveToTarget`
        *   **Action**: `PinAndEat` (See Section 5)

### 4.2. Logic: `FlightControl`
*   **Monitor Stamina**:
    *   If `stamina < 10` AND `state == FLYING` -> Force `Land` behavior.
*   **Obstacle Avoidance**:
*   **Emergency Landing / Falling**:
    *   If `stamina <= 0`: Transition to `FALLING`.
    *   **Falling Logic**:
        *   Apply gravity * 3.0.
        *   If over water (and not Amphibious) -> Drown triggers on splashdown.
        *   If over High Obstacle -> Push to nearest valid navigation node.

---

## 5. Consumption Mechanics (Timed Eating)
**File:** `src/yukkuri_game/game/systems/interaction_system.py`

### Mechanism: `Channeling`
We introduce a "Channeling" concept where an action requires X seconds to complete, disabling movement.

**Action: `EatPrey`**
*   **Requirements**: 
    *   Distance < InteractRange.
    *   Target is `Alive`.
*   **Execution (Per Tick):**
    1.  **Lock**: Predator velocity = 0, Target velocity = 0.
    2.  **State**: Set Predator visual state to `EATING`. Target visual state to `BEING_EATEN` (or `PAIN`).
    3.  **Damage**: Apply `damage_per_tick = (Predator.dps * dt)`.
    4.  **Visual Feedback**:
        *   Emit `BloodParticle` / `CrunchSound`.
        *   Scale Target Sprite: `target_scale *= (current_health / max_health)`.
    5.  **Completion**:
        *   If `Target.health <= 0`:
            *   Destroy Target Entity.
            *   Predator `Hunger -= 50`.
            *   Return `Status.SUCCESS`.
    6.  **Interruption**:
        *   If Predator takes damage -> Break Channel (Return `Status.FAILURE`).
        *   Target is released.

### 5.2. Social Defense (The "Mob")
*   **Response to Predation**:
    *   When an entity enters `BEING_EATEN` state, it broadcasts a "Distress Signal" (Game Event).
    *   Nearby entities with positive `Relationship` (Family/Friends) check bravery.
    *   **Behavior**: `HarassPredator`
        *   Move to Predator.
        *   Attack (Headbox/Body slam).
        *   *Goal*: Interrupt the `EatPrey` channel to save the victim.

---

## 6. Migration Checklist

1.  [ ] **Schema Update**: Add `Flight` and `Predator` configuration to `data/types.toml`.
2.  [ ] **Factory Update**: Update `EntityFactory` to parse and attach new components.
3.  [ ] **Physics Update**: Refactor `KinematicMovementSystem` to support dynamic collision masks.
4.  [ ] **Render Update**: Implement Shadow Scaling and Vertical Offset in `RenderSystem`.
5.  [ ] **AI Update**: Implement `FindPrey`, `Swoop`, and `PinAndEat` behavior nodes.
