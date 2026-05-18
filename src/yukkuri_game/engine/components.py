"""
Core engine components.
"""

from typing import TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum, auto

import pymunk

if TYPE_CHECKING:
    from .data_models import AnimationDefinition


class FlickerStyle(Enum):
    """
    Enumeration of light source flicker patterns.
    """
    NONE = auto()
    FIRE = auto()
    PULSE = auto()


@dataclass(slots=True)
class Transform:
    """
    Component representing world space position, rotation, and scale.
    """
    x: float
    y: float
    rotation: float = 0.0
    scale: float = 1.0
    prev_x: float | None = None
    prev_y: float | None = None
    prev_rotation: float | None = None

    def __post_init__(self) -> None:
        """Initializes previous positions to current values."""
        if self.prev_x is None:
            self.prev_x = self.x
        if self.prev_y is None:
            self.prev_y = self.y
        if self.prev_rotation is None:
            self.prev_rotation = self.rotation


@dataclass(slots=True)
class Velocity:
    """
    Component representing linear velocity.
    """
    dx: float
    dy: float


@dataclass(slots=True)
class Sprite:
    """
    Component containing visual asset data for rendering.
    """
    image_name: str
    width: int
    height: int
    layer: int = 0
    flip_x: bool = False
    flip_y: bool = False
    alpha: int = 255

    # Simple frame-based animation
    frame_count: int = 1
    frame_duration: float = 0.1
    current_frame: int = 0
    timer: float = 0.0
    loop: bool = True
    is_animating: bool = True


@dataclass(slots=True)
class Animator:
    """
    Component for handling complex, state-based animations.
    """
    animations: dict[str, "AnimationDefinition"]
    current_animation: str = "default"
    current_frame_index: int = 0
    timer: float = 0.0
    finished: bool = False
    speed: float = 1.0
    next_animation: str | None = None
    forward: bool = True


@dataclass(slots=True)
class LODComponent:
    """
    Manages Level of Detail (LOD) for update frequency optimization.
    """
    level: int = 2


@dataclass(slots=True)
class StableIDComponent:
    """
    Component for persistent identity.
    """
    id: int


@dataclass(slots=True)
class Persistable:
    """
    Marker component for entities that should be saved to disk.
    """
    pass


@dataclass(slots=True)
class FloatingText:
    """
    Component representing floating text for visual feedback.
    """
    text: str
    color: tuple[int, int, int]
    lifetime: float
    max_lifetime: float
    velocity_y: float
    size: int = 20


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
class LightSource:
    """
    Component defining a point light source attached to an entity.
    """
    radius: float = 300.0
    color: tuple[int, int, int] = (255, 255, 220)
    intensity: float = 1.0
    flicker_style: FlickerStyle = FlickerStyle.NONE
    soft_shadows: bool = True
    static: bool = False
    _flicker_offset: float = 0.0


@dataclass(slots=True)
class Occluder:
    """
    Component defining a geometry that blocks light (Shadow Caster).
    """
    polygon: list[tuple[float, float]] | None = None
    static: bool = False


@dataclass(slots=True)
class Selectable:
    """
    Component identifying an entity as selectable by player input.
    """
    selected: bool = False
    hovered: bool = False


@dataclass(slots=True)
class VisualTransform:
    """
    Component for purely visual offsets or effects.
    """
    vertical_offset: float = 0.0
    shake_timer: float = 0.0
    shake_intensity: float = 0.0
    has_drop_shadow: bool = False
    shadow_position: pymunk.vec2d.Vec2d | None = None

    def __post_init__(self) -> None:
        if self.shadow_position is None:
            self.shadow_position = pymunk.vec2d.Vec2d(0, 0)


@dataclass(slots=True)
class MovementController:
    """
    Component holding movement state and commands for physics-based entities.
    """
    target_velocity: pymunk.vec2d.Vec2d = field(default_factory=lambda: pymunk.vec2d.Vec2d(0, 0))
    acceleration: float = 500.0
    friction: float = 10.0
    current_velocity: pymunk.vec2d.Vec2d = field(default_factory=lambda: pymunk.vec2d.Vec2d(0, 0))
    visual_bob_timer: float = 0.0
    bob_height: float = 10.0
    bob_speed: float = 5.0


@dataclass(slots=True)
class Mount:
    """
    Component for handling hierarchical entity attachment.
    """
    parent_id: int = -1
    children_ids: list[int] = field(default_factory=list)
    mount_point_offset: pymunk.vec2d.Vec2d = field(default_factory=lambda: pymunk.vec2d.Vec2d(0, 0))
    layer_order: int = 0
    structure_dirty: bool = True


class FlightState(Enum):
    """
    Enumeration representing the current flight status.
    """
    GROUNDED = 0
    TAKEOFF = 1
    FLYING = 2
    HOVERING = 3
    LANDING = 4
    SWOOPING = 5
    FALLING = 6


@dataclass(slots=True)
class Flight:
    """
    Component handling flight mechanics and stamina.
    """
    altitude: float = 0.0
    max_altitude: float = 60.0
    vertical_speed: float = 20.0
    stamina: float = 100.0
    max_stamina: float = 100.0
    fly_cost: float = 5.0
    hover_cost: float = 1.0
    recovery_rate: float = 10.0
    state: FlightState = FlightState.GROUNDED
