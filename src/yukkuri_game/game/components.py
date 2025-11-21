from dataclasses import dataclass
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
    frame_width: int = 0
    frame_height: int = 0
    frame_count: int = 1
    current_frame: int = 0
    animation_speed: float = 0.1
    timer: float = 0.0

@dataclass
class Selectable:
    """
    Component indicating that an entity can be selected by the user.

    Attributes:
        selected (bool): Whether the entity is currently selected. Defaults to False.
    """
    selected: bool = False
