"""
Physics and movement components.
"""

from dataclasses import dataclass, field
import pymunk
from pymunk.vec2d import Vec2d as Vector2
from ...engine.types import EntityID

@dataclass(slots=True)
class PhysicsBody:
    """
    Component representing the physical body of an entity in the Pymunk space.
    """
    body: pymunk.Body
    shape: pymunk.Shape
    base_radius: float | None = None

    def __post_init__(self) -> None:
        """Initializes base_radius from the shape if not provided."""
        if self.base_radius is None and isinstance(self.shape, pymunk.Circle):
            self.base_radius = self.shape.radius


@dataclass(slots=True)
class MovementController:
    """
    Component holding movement state and commands for physics-based entities.
    """
    target_velocity: Vector2 = field(default_factory=lambda: Vector2(0, 0))

    # Physics parameters
    acceleration: float = 500.0
    friction: float = 10.0
    current_velocity: Vector2 = field(default_factory=lambda: Vector2(0, 0))

    # Animation parameters
    visual_bob_timer: float = 0.0
    bob_height: float = 10.0
    bob_speed: float = 5.0


@dataclass(slots=True)
class SteeringComponent:
    """
    Component for handling autonomous steering behaviors.
    """
    max_speed: float = 150.0
    max_force: float = 300.0
    mass: float = 1.0

    current_steering_force: Vector2 = field(default_factory=lambda: Vector2(0, 0))

    # Weight Configurations
    seek_weight: float = 1.0
    separation_weight: float = 1.5
    avoidance_weight: float = 2.0
    arrival_radius: float = 25.0

    time_stuck: float = 0.0
    pursuit_enabled: bool = False


@dataclass(slots=True)
class MoveCommand:
    """
    High-level movement directive issued by AI or decision systems.
    """
    target_pos: Vector2 = field(default_factory=lambda: Vector2(0, 0))
    target_entity_id: EntityID | None = None
    speed_multiplier: float = 1.0
    altitude: float = 0.0
    use_pathfinding: bool = True
    expiration: float = 0.0
    priority: int = 2


@dataclass(slots=True)
class InteractionRequest:
    """
    Component representing a request to interact with another entity.
    """
    target_id: EntityID
    consume: bool = True
    action: str = "DEFAULT"


@dataclass(slots=True)
class Mount:
    """
    Component for handling hierarchical entity attachment (e.g. stacking).
    """
    parent_id: EntityID = EntityID(-1)
    children_ids: list[EntityID] = field(default_factory=list)
    mount_point_offset: Vector2 = field(default_factory=lambda: Vector2(0, 0))
    layer_order: int = 0
    structure_dirty: bool = True


@dataclass(slots=True)
class PendingDismount:
    """
    State component for entities in the process of dismounting (Ghost Mode).
    """
    time_in_pending: float = 0.0
