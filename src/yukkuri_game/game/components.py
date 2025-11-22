from dataclasses import dataclass
from typing import Dict, Optional
import pymunk
from ..engine.data_models import AnimationDefinition

@dataclass
class PhysicsBody:
    """
    Component representing the physical body of an entity in the pymunk space.

    Attributes:
        body (pymunk.Body): The physics body.
        shape (pymunk.Shape): The physics shape.
    """
    body: pymunk.Body
    shape: pymunk.Shape

@dataclass
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
    scale: float = 1.0

@dataclass
class Velocity:
    """
    Component representing the velocity of an entity.

    Attributes:
        dx (float): The velocity along the x-axis.
        dy (float): The velocity along the y-axis.
    """
    dx: float
    dy: float

@dataclass
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

    # Animation support (Legacy / Simple)
    frame_count: int = 1
    frame_duration: float = 0.1
    current_frame: int = 0
    timer: float = 0.0
    loop: bool = True
    is_animating: bool = True

@dataclass
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
    animations: Dict[str, AnimationDefinition]
    current_animation: str = "default"
    current_frame_index: int = 0
    timer: float = 0.0
    finished: bool = False
    speed: float = 1.0
    next_animation: Optional[str] = None
    forward: bool = True  # Direction for ping-pong loops

@dataclass
class Selectable:
    """
    Component indicating that an entity can be selected by the user.

    Attributes:
        selected (bool): Whether the entity is currently selected. Defaults to False.
    """
    selected: bool = False


@dataclass
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

@dataclass
class InteractionRequest:
    """
    Component requesting an interaction with another entity.

    Attributes:
        target_id (int): The ID of the target entity.
        consume (bool): Whether to consume the target (e.g. eat it).
        interaction_type (str): The type of interaction (optional).
    """
    target_id: int
    consume: bool = True
    interaction_type: str = "DEFAULT"
