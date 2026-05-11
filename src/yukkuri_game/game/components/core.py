"""
Core game components.
"""

from dataclasses import dataclass

@dataclass(slots=True)
class LODComponent:
    """
    Manages Level of Detail (LOD) for update frequency optimization.
    """
    level: int = 2


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
    from ...engine.data_models import AnimationDefinition
    
    animations: dict[str, "AnimationDefinition"]
    current_animation: str = "default"
    current_frame_index: int = 0
    timer: float = 0.0
    finished: bool = False
    speed: float = 1.0
    next_animation: str | None = None
    forward: bool = True


@dataclass(slots=True)
class Selectable:
    """
    Component identifying an entity as selectable by player input.
    """
    selected: bool = False


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
class VisualTransform:
    """
    Component for visual-only transformations, decoupled from physics.
    """
    from pymunk.vec2d import Vec2d as Vector2
    
    vertical_offset: float = 0.0
    shadow_position: "Vector2" = None # Will be initialized in __post_init__
    has_drop_shadow: bool = False

    def __post_init__(self) -> None:
        from pymunk.vec2d import Vec2d as Vector2
        if self.shadow_position is None:
            self.shadow_position = Vector2(0, 0)


@dataclass(slots=True)
class Dead:
    """Tag component identifying that the entity is deceased."""
    pass


@dataclass(slots=True)
class Poop:
    """Tag component identifying identifying the entity as excrement."""
    pass
