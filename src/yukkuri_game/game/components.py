"""
Module defining core game components.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
import pymunk
from pymunk.vec2d import Vec2d as Vector2
from ..engine.data_models import AnimationDefinition
from ..engine.types import EntityID


@dataclass(slots=True)
class PhysicsBody:
    """
    Component representing the physical body of an entity in the pymunk space.

    Attributes:
        body (pymunk.Body): The physics body.
        shape (pymunk.Shape): The physics shape.
        base_radius (Optional[float]): The original radius of the shape (for Totem Pole resizing).
    """

    body: pymunk.Body
    shape: pymunk.Shape
    base_radius: float | None = None

    def __post_init__(self) -> None:
        if self.base_radius is None and isinstance(self.shape, pymunk.Circle):
            self.base_radius = self.shape.radius


@dataclass(slots=True)
class Transform:
    """
    Component representing the position and scale of an entity in the world.

    Attributes:
        x (float): The x-coordinate of the entity.
        y (float): The y-coordinate of the entity.
        scale (float): The scale factor of the entity. Defaults to 1.0.
    """

    x: float
    y: float
    rotation: float = 0.0
    scale: float = 1.0
    prev_x: float | None = None
    prev_y: float | None = None
    prev_rotation: float | None = None

    def __post_init__(self) -> None:
        """Initialize prev positions to current positions to avoid jumps."""
        if self.prev_x is None:
            self.prev_x = self.x
        if self.prev_y is None:
            self.prev_y = self.y
        if self.prev_rotation is None:
            self.prev_rotation = self.rotation


@dataclass(slots=True)
class Velocity:
    """
    Component representing the velocity of an entity.

    Attributes:
        dx (float): The velocity along the x-axis.
        dy (float): The velocity along the y-axis.
    """

    dx: float
    dy: float


@dataclass(slots=True)
class Sprite:
    """
    Component representing the graphical sprite of an entity.

    Attributes:
        image_name (str): The filename of the image asset.
        width (int): The width of the sprite in pixels.
        height (int): The height of the sprite in pixels.
        layer (int): The rendering layer order. Defaults to 0.
    """

    image_name: str
    width: int
    height: int
    layer: int = 0
    flip_x: bool = False
    flip_y: bool = False

    # Simple/Direct animation fields (used when entity has no Animator component)
    # Also used by Animator as the output frame index for rendering
    frame_count: int = 1
    frame_duration: float = 0.1
    current_frame: int = 0
    timer: float = 0.0
    loop: bool = True
    is_animating: bool = True


@dataclass(slots=True)
class Animator:
    """
    Component for handling advanced animations.

    Attributes:
        animations (Dict[str, AnimationDefinition]): Available animations.
        current_animation (str): Name of the currently playing animation.
        current_frame_index (int): Index in the animation's frame list.
        timer (float): Timer for the current frame.
        finished (bool): Whether the animation has finished (for non-looping).
    """

    animations: dict[str, AnimationDefinition]
    current_animation: str = "default"
    current_frame_index: int = 0
    timer: float = 0.0
    finished: bool = False
    speed: float = 1.0
    next_animation: str | None = None
    forward: bool = True  # Direction for ping-pong loops


@dataclass(slots=True)
class Selectable:
    """
    Component indicating that an entity can be selected by the user.

    Attributes:
        selected (bool): Whether the entity is currently selected. Defaults to False.
    """

    selected: bool = False


@dataclass(slots=True)
class FloatingText:
    """
    Component representing floating text for visual feedback.

    Attributes:
        text (str): The text to display.
        color (tuple[int, int, int]): The color of the text.
        lifetime (float): The remaining time to live in seconds.
        velocity_y (float): The speed at which the text floats up (pixels/second).
        size (int): The font size.
    """

    text: str
    color: tuple[int, int, int]
    lifetime: float
    max_lifetime: float
    velocity_y: float
    size: int = 20


@dataclass(slots=True)
class InteractionRequest:
    """
    Component requesting an interaction with another entity.

    Attributes:
        target_id (EntityID): The ID of the target entity.
        consume (bool): Whether to consume the target (e.g. eat it).
        action (str): The specific action (e.g. "Talk", "Eat").
    """

    target_id: EntityID
    consume: bool = True
    action: str = "DEFAULT"


@dataclass(slots=True)
class MovementController:
    """A simple component that holds movement commands and visual state."""

    # Safety Fix: Use default_factory for mutable Vector2
    target_velocity: Vector2 = field(default_factory=lambda: Vector2(0, 0))

    # New fields for Kinematic Controller
    acceleration: float = 500.0
    friction: float = 10.0
    current_velocity: Vector2 = field(default_factory=lambda: Vector2(0, 0))

    # --- Visual Tuning ---
    visual_bob_timer: float = 0.0
    bob_height: float = 10.0
    bob_speed: float = 5.0


@dataclass(slots=True)
class Mount:
    """
    Component for handling parent-child relationships in the hierarchy.
    Tracks parent and children entities, mount offsets, and render layering.
    """

    parent_id: EntityID = EntityID(-1)
    children_ids: list[EntityID] = field(default_factory=list)
    mount_point_offset: Vector2 = field(default_factory=lambda: Vector2(0, 0))
    layer_order: int = 0
    structure_dirty: bool = True


@dataclass(slots=True)
class PendingDismount:
    """
    Component for entities that are in the process of dismounting (Ghost Mode).
    Entities in this state are searching for a valid physical location to materialize.
    """

    time_in_pending: float = 0.0


@dataclass(slots=True)
class Vision:
    """
    Component for visibility calculation.
    """

    range: float = 200.0
    fov: float = 360.0  # in degrees


@dataclass(slots=True)
class VisualTransform:
    """Holds visual-only transform data, decoupling rendering from physics."""

    vertical_offset: float = 0.0
    # Safety Fix: Use default_factory for mutable Vector2
    shadow_position: Vector2 = field(default_factory=lambda: Vector2(0, 0))
    has_drop_shadow: bool = False


class FlickerStyle(Enum):
    NONE = auto()
    FIRE = auto()
    PULSE = auto()


# --- Lighting Components ---


@dataclass(slots=True)
class LightSource:
    """
    Component defining a point light source.
    """

    radius: float = 300.0
    color: tuple[int, int, int] = (255, 255, 220)
    intensity: float = 1.0
    flicker_style: FlickerStyle = FlickerStyle.NONE
    # If True, enables soft shadow rendering (blurred edges)
    soft_shadows: bool = True
    # If True, the light and its shadows are cached (for static lights)
    static: bool = False
    # Internal state for flickering
    _flicker_offset: float = 0.0


@dataclass(slots=True)
class Occluder:
    """
    Component defining a light-blocking shape (Hull).
    """

    # If None, defaults to the entity's PhysicsBody shape or Sprite rect
    polygon: list[tuple[float, float]] | None = None
    # optimization: If True, the occluder geometry is assumed to be static (e.g. walls)
    # and can be cached more aggressively.
    static: bool = False


@dataclass(slots=True)
class SteeringComponent:
    """
    Component for handling steering behaviors (Seek, Separation, etc.).
    """

    max_speed: float = 150.0
    max_force: float = 300.0
    mass: float = 1.0

    # Current accumulated force
    current_steering_force: Vector2 = field(default_factory=lambda: Vector2(0, 0))

    # Tuning weights
    seek_weight: float = 1.0
    separation_weight: float = 1.5
    avoidance_weight: float = 2.0
    arrival_radius: float = 25.0

    # Stuck detection
    time_stuck: float = 0.0
    
    # Pursuit Mode
    pursuit_enabled: bool = False
