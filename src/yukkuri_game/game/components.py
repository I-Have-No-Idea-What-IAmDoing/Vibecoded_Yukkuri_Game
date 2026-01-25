"""
Module defining core game components.

This module contains generic components used across the engine and game logic,
excluding Yukkuri-specific components which are defined in `yukkuri_components.py`.
Most components are implemented as slotted dataclasses for memory optimization.
"""

from dataclasses import dataclass, field
from enum import Enum, auto

import pymunk
from pymunk.vec2d import Vec2d as Vector2

from ..engine.data_models import AnimationDefinition
from ..engine.types import EntityID


@dataclass(slots=True)
class LODComponent:
    """
    Manages Level of Detail (LOD) for update frequency optimization.

    Entities with lower LOD levels are updated less frequently to save performance.

    Attributes:
        level (int): The current LOD level. Defaults to 2.
            0: High (Every frame)
            1: Medium (Every 2nd frame)
            2: Low (Every 4th frame)
            3: Culled (No updates)
    """

    level: int = 2


@dataclass(slots=True)
class PhysicsBody:
    """
    Component representing the physical body of an entity in the Pymunk space.

    Attributes:
        body (pymunk.Body): The physics body instance.
        shape (pymunk.Shape): The collision shape attached to the body.
        base_radius (float | None): The original radius of the shape, used for
            resizing logic (e.g. Totem Pole stacking). Defaults to None.
    """

    body: pymunk.Body
    shape: pymunk.Shape
    base_radius: float | None = None

    def __post_init__(self) -> None:
        """Initializes base_radius from the shape if not provided."""
        if self.base_radius is None and isinstance(self.shape, pymunk.Circle):
            self.base_radius = self.shape.radius


@dataclass(slots=True)
class Transform:
    """
    Component representing world space position, rotation, and scale.

    Attributes:
        x (float): The x-coordinate in world space.
        y (float): The y-coordinate in world space.
        rotation (float): Rotation angle in radians. Defaults to 0.0.
        scale (float): Scale factor. Defaults to 1.0.
        prev_x (float | None): X-coordinate from the previous frame (for interpolation). Defaults to None.
        prev_y (float | None): Y-coordinate from the previous frame. Defaults to None.
        prev_rotation (float | None): Rotation from the previous frame. Defaults to None.
    """

    x: float
    y: float
    rotation: float = 0.0
    scale: float = 1.0
    prev_x: float | None = None
    prev_y: float | None = None
    prev_rotation: float | None = None

    def __post_init__(self) -> None:
        """Initializes previous positions to current values to prevent interpolation jumps."""
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

    Attributes:
        dx (float): Velocity along the x-axis in pixels/second.
        dy (float): Velocity along the y-axis in pixels/second.
    """

    dx: float
    dy: float


@dataclass(slots=True)
class Sprite:
    """
    Component containing visual asset data for rendering.

    Attributes:
        image_name (str): The filename of the image asset in the texture atlas.
        width (int): Width of the sprite in pixels.
        height (int): Height of the sprite in pixels.
        layer (int): Rendering layer order (higher renders on top). Defaults to 0.
        flip_x (bool): Whether to flip the sprite horizontally. Defaults to False.
        flip_y (bool): Whether to flip the sprite vertically. Defaults to False.
        alpha (int): Transparency level (0-255). Defaults to 255 (opaque).
        frame_count (int): Total number of animation frames. Defaults to 1.
        frame_duration (float): Duration of each frame in seconds. Defaults to 0.1.
        current_frame (int): The current frame index. Defaults to 0.
        timer (float): Accumulator for animation timing. Defaults to 0.0.
        loop (bool): Whether the animation should loop. Defaults to True.
        is_animating (bool): Whether the animation is currently playing. Defaults to True.
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

    Attributes:
        animations (dict[str, AnimationDefinition]): Map of animation names to definitions.
        current_animation (str): Name of the currently playing animation. Defaults to "default".
        current_frame_index (int): Index into the current animation's frame list. Defaults to 0.
        timer (float): Timer for the current frame. Defaults to 0.0.
        finished (bool): True if a non-looping animation has completed. Defaults to False.
        speed (float): Playback speed multiplier. Defaults to 1.0.
        next_animation (str | None): Animation to transition to after completion. Defaults to None.
        forward (bool): Direction flag for ping-pong animations. Defaults to True.
    """

    animations: dict[str, AnimationDefinition]
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

    Attributes:
        selected (bool): Whether the entity is currently selected. Defaults to False.
    """

    selected: bool = False


@dataclass(slots=True)
class FloatingText:
    """
    Component representing floating text for visual feedback (e.g. damage numbers).

    Attributes:
        text (str): The text content to display.
        color (tuple[int, int, int]): RGB color of the text.
        lifetime (float): Remaining time to live in seconds.
        max_lifetime (float): Initial lifetime duration.
        velocity_y (float): Vertical float speed in pixels/second.
        size (int): Font size. Defaults to 20.
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
    Component representing a request to interact with another entity.
    Processed by systems to initiate social or physical interactions.

    Attributes:
        target_id (EntityID): The ID of the target entity.
        consume (bool): Whether to consume the target (e.g. eat item). Defaults to True.
        action (str): The specific interaction action (e.g. "Talk", "Eat"). Defaults to "DEFAULT".
    """

    target_id: EntityID
    consume: bool = True
    action: str = "DEFAULT"


@dataclass(slots=True)
class MovementController:
    """
    Component holding movement state and commands for physics-based entities.

    Attributes:
        target_velocity (Vector2): Desired velocity vector. Defaults to (0, 0).
        acceleration (float): Acceleration rate in pixels/sec^2. Defaults to 500.0.
        friction (float): Friction coefficient for damping. Defaults to 10.0.
        current_velocity (Vector2): Current processing velocity. Defaults to (0, 0).
        visual_bob_timer (float): Timer for bobbing animation logic. Defaults to 0.0.
        bob_height (float): Amplitude of the bobbing motion. Defaults to 10.0.
        bob_speed (float): Frequency of the bobbing motion. Defaults to 5.0.
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
class Mount:
    """
    Component for handling hierarchical entity attachment (e.g. stacking).

    Attributes:
        parent_id (EntityID): The ID of the parent entity this is mounted to. Defaults to -1.
        children_ids (list[EntityID]): List of IDs of entities mounted to this one. Defaults to empty list.
        mount_point_offset (Vector2): Offset from the parent's position. Defaults to (0, 0).
        layer_order (int): Relative sorting order within the stack. Defaults to 0.
        structure_dirty (bool): Flag indicating the hierarchy needs update. Defaults to True.
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

    Entities with this component are searching for a valid physical location
    to materialize, preventing immediate collision with the mount parent.

    Attributes:
        time_in_pending (float): Duration spent in dismount state. Defaults to 0.0.
    """

    time_in_pending: float = 0.0


@dataclass(slots=True)
class Vision:
    """
    Component defining an entity's perception capabilities.

    Attributes:
        range (float): Maximum vision distance. Defaults to 200.0.
        fov (float): Field of view in degrees. Defaults to 360.0.
    """

    range: float = 200.0
    fov: float = 360.0


@dataclass(slots=True)
class VisualTransform:
    """
    Component for visual-only transformations, decoupled from physics.
    Used for effects like sprite bobbing, flight altitude, and shadow offsets.

    Attributes:
        vertical_offset (float): Visual Y-axis offset (e.g. for hopping). Defaults to 0.0.
        shadow_position (Vector2): Offset for the drop shadow. Defaults to (0, 0).
        has_drop_shadow (bool): Whether this entity casts a drop shadow. Defaults to False.
    """

    vertical_offset: float = 0.0
    shadow_position: Vector2 = field(default_factory=lambda: Vector2(0, 0))
    has_drop_shadow: bool = False


class FlickerStyle(Enum):
    """
    Enumeration of light source flicker patterns.
    """

    NONE = auto()
    FIRE = auto()
    PULSE = auto()


@dataclass(slots=True)
class LightSource:
    """
    Component defining a point light source attached to an entity.

    Attributes:
        radius (float): Lighting radius in pixels. Defaults to 300.0.
        color (tuple[int, int, int]): RGB color of the light. Defaults to (255, 255, 220).
        intensity (float): Base intensity/brightness multiplier. Defaults to 1.0.
        flicker_style (FlickerStyle): The flicker animation pattern. Defaults to FlickerStyle.NONE.
        soft_shadows (bool): Whether to render soft shadow edges. Defaults to True.
        static (bool): Optimization flag. If True, shadows are cached aggressively. Defaults to False.
        _flicker_offset (float): Internal time offset for flicker noise generation. Defaults to 0.0.
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

    Attributes:
        polygon (list[tuple[float, float]] | None): Custom hull vertices.
            If None, the PhysicsBody shape is used. Defaults to None.
        static (bool): Optimization flag. If True, occlusion geometry is cached. Defaults to False.
    """

    polygon: list[tuple[float, float]] | None = None
    static: bool = False


@dataclass(slots=True)
class SteeringComponent:
    """
    Component for handling autonomous steering behaviors.
    Includes logic for seeking, separation, and obstacle avoidance.

    Attributes:
        max_speed (float): Maximum movement speed. Defaults to 150.0.
        max_force (float): Maximum steering force applied per frame. Defaults to 300.0.
        mass (float): Simulated mass for inertia. Defaults to 1.0.
        current_steering_force (Vector2): The accumulated force vector. Defaults to (0, 0).
        seek_weight (float): Weight for seek behavior. Defaults to 1.0.
        separation_weight (float): Weight for separation behavior. Defaults to 1.5.
        avoidance_weight (float): Weight for obstacle avoidance. Defaults to 2.0.
        arrival_radius (float): Distance at which to slow down when arriving. Defaults to 25.0.
        time_stuck (float): Timer tracking how long the entity has been stuck. Defaults to 0.0.
        pursuit_enabled (bool): Whether to use predictive pursuit logic. Defaults to False.
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

    This component acts as an interface between the AI (Goal System) and
    the Physics/Steering execution layer.

    Attributes:
        target_pos (Vector2): The destination coordinates. Defaults to (0, 0).
        target_entity_id (int | None): Entity to track/follow. Defaults to None.
        speed_multiplier (float): Modifier for movement speed (0.0 to 1.0+). Defaults to 1.0.
        altitude (float): Desired flight altitude (for flying entities). Defaults to 0.0.
        use_pathfinding (bool): If True, requests a path. If False, steers directly. Defaults to True.
        expiration (float): Game time when this command becomes invalid. 0 for indefinite. Defaults to 0.0.
        priority (int): Priority level (0=Critical, 1=High, 2=Normal). Defaults to 2.
    """

    target_pos: Vector2 = field(default_factory=lambda: Vector2(0, 0))
    target_entity_id: int | None = None
    speed_multiplier: float = 1.0
    altitude: float = 0.0
    use_pathfinding: bool = True
    expiration: float = 0.0
    priority: int = 2
