from dataclasses import dataclass, field
from typing import Dict, Optional
import pymunk

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
class Animation:
    """
    Data class defining an animation sequence.

    Attributes:
        name (str): The name of the animation.
        start_frame (int): The starting frame index in the sprite sheet.
        frame_count (int): The number of frames in this animation.
        frame_duration (float): Duration of each frame in seconds.
        loop (bool): Whether the animation should loop.
        row (int): The row index in the sprite sheet (default 0).
    """
    name: str
    start_frame: int
    frame_count: int
    frame_duration: float
    loop: bool = True
    row: int = 0

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

    # Animation support
    frame_count: int = 1
    frame_duration: float = 0.1
    current_frame: int = 0
    timer: float = 0.0
    loop: bool = True
    is_animating: bool = True

    # Advanced Animation support
    animations: Dict[str, Animation] = field(default_factory=dict)
    current_animation: Optional[str] = None
    row: int = 0
    start_frame: int = 0 # Starting frame offset in the sprite sheet

    # Internal state for animation switching
    _last_animation: Optional[str] = None

@dataclass
class Selectable:
    """
    Component indicating that an entity can be selected by the user.

    Attributes:
        selected (bool): Whether the entity is currently selected. Defaults to False.
    """
    selected: bool = False
