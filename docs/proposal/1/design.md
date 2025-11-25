# Yukkuri Movement System Overhaul

## 1. Introduction

The current Yukkuri Movement System has served the game well during initial development, but as the game grows in complexity, several architectural limitations have emerged. Specifically, the tight coupling between high-level decision making (Behavior Trees) and low-level movement execution (Pathfinding, Steering, Physics) makes the system difficult to extend, debug, and optimize.

This proposal outlines a design to overhaul the movement system by adopting a more strictly ECS-compliant architecture. The goal is to separate **Movement Intent** (what the entity wants to do) from **Movement Execution** (how the entity does it).

## 2. Problem Statement

### 2.1. Coupling in `MoveToTarget`
The `MoveToTarget` action node in the Behavior Tree is currently a "god object" for movement. It is responsible for:
- Checking if a target exists.
- Calculating pathfinding (A*).
- Performing stuck detection.
- Calculating steering forces (Seek/Arrive).
- Managing local avoidance (Raycasting).
- Directly manipulating `PhysicsBody` velocity OR `Transform` position.

This violation of the Single Responsibility Principle makes `MoveToTarget` hard to maintain. If we want to add a new movement mode (e.g., "Flying" or "Jumping"), we would have to modify this complex class or create a duplicate.

### 2.2. Physics vs. Transform Duality
The game currently supports entities with and without `PhysicsBody`. The movement logic inside `MoveToTarget` contains branching logic to handle both cases. A unified movement system should abstract this detail so that high-level logic doesn't need to care about the underlying physics implementation.

### 2.3. Frame-Rate Dependent Logic
Some movement calculations, specifically stuck detection and direct transform manipulation, rely on `dt` passed through the blackboard. While this is standard, the logic is scattered inside the Behavior Tree tick, which might not run at the same frequency as the physics simulation.

## 3. Proposed Design

The core of the proposal is to introduce a **Movement Pipeline** that bridges the gap between AI and Physics.

### 3.1. Architecture Overview

1.  **AI System (Behavior Tree)**: Decides *where* to go. It no longer calculates paths or velocities. It simply sets a `MovementRequest` component.
2.  **Navigation System**: Observes `MovementRequest`. If the target has changed, it calculates a path and updates a `Path` component.
3.  **Steering System**: Reads the `Path` and `MovementRequest`. It calculates the desired velocity based on the current waypoint, steering behaviors (Seek, Arrive, Wander), and local avoidance. It updates a `VelocityRequest` or directly applies force to `PhysicsBody`.
4.  **Physics System**: (Existing) Simulates the physics world and syncs `PhysicsBody` to `Transform`.

### 3.2. New Components

#### `MovementRequest`
Represents the intent to move.
```python
@dataclass
class MovementRequest:
    target_position: Optional[Tuple[float, float]] = None
    target_entity_id: Optional[int] = None
    speed: float = 100.0
    stopping_distance: float = 5.0
    movement_type: str = "ground" # ground, fly, etc.
    update_path: bool = True # Flag to trigger pathfinding
```

#### `Path`
Stores the calculated route.
```python
@dataclass
class Path:
    waypoints: List[Tuple[float, float]]
    current_index: int = 0
    status: str = "idle" # idle, moving, completed, unreachable
    stuck_timer: float = 0.0
```

#### `SteeringAgent`
Configuration for steering behaviors (formerly scattered or hardcoded).
```python
@dataclass
class SteeringAgent:
    max_speed: float = 100.0
    max_force: float = 20.0
    mass: float = 1.0
    slowing_radius: float = 50.0
    avoidance_radius: float = 20.0
```

### 3.3. Revised Systems

#### `NavigationSystem`
- **Input**: `MovementRequest`, `Transform`
- **Output**: `Path`
- **Logic**:
    - Checks if `MovementRequest.update_path` is True.
    - If `target_entity_id` is set, updates `target_position` from that entity's Transform.
    - Runs A* pathfinding via `NavigationService`.
    - Sets `Path.waypoints` and resets `Path.current_index`.
    - Sets `MovementRequest.update_path` to False.

#### `SteeringSystem`
- **Input**: `MovementRequest`, `Path`, `Transform`, `PhysicsBody`, `SteeringAgent`
- **Output**: `PhysicsBody.velocity` (or `Velocity` component)
- **Logic**:
    - If `Path.status` is "moving":
        - Get current waypoint.
        - Calculate Steering Force (Seek/Arrive).
        - Run local avoidance (Raycasts against obstacles).
        - Apply force/velocity to `PhysicsBody`.
        - Check for waypoint completion.
        - Check for stuck condition (position delta over time).

### 3.4. Behavior Tree Updates
The `MoveToTarget` action will be significantly simplified.
- **New Logic**:
    1.  Get `MovementRequest` component (or add it if missing).
    2.  Set `MovementRequest.target_entity_id` or `target_position`.
    3.  Monitor `Path.status`.
    4.  Return `RUNNING` while `Path.status` is "moving".
    5.  Return `SUCCESS` if `Path.status` is "completed".
    6.  Return `FAILURE` if `Path.status` is "unreachable" or stuck.

## 4. Rationale

### 4.1. Separation of Concerns
By splitting the logic, the **AI** only cares about *intent* ("I want to go to the food"). The **NavigationSystem** cares about *route planning* ("How do I get there?"). The **SteeringSystem** cares about *execution* ("How do I move my body?"). This makes each system easier to understand and test in isolation.

### 4.2. Reusability
The new `NavigationSystem` and `SteeringSystem` can be used by non-AI entities if needed (e.g., a scripted cutscene character, or a projectile).

### 4.3. Robustness
Centralizing path following and stuck detection in a system (rather than a transient Action node) allows for more robust recovery states. For example, if an entity is stuck, the SteeringSystem can attempt avoidance maneuvers without the AI needing to reset its entire decision tree.

### 4.4. Extensibility
Adding "Flying" Yukkuris becomes easier. We just set `MovementRequest.movement_type = "fly"`. The `NavigationSystem` can skip pathfinding (fly straight), or use a 3D pathfinder. The `SteeringSystem` can ignore ground friction.

## 5. Potential Risks
- **Performance**: Adding more systems and components increases the overhead of the ECS loop. However, `esper` is fast, and the logic being moved is already running every frame; it's just being reorganized.
- **Complexity**: For simple games, this might be over-engineering. But given the "Yukkuri Raising" nature implies complex behaviors and potential physics interactions, the robustness is worth it.
