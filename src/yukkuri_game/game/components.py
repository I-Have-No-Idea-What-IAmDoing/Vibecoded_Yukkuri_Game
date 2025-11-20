from dataclasses import dataclass

@dataclass
class Transform:
    x: float
    y: float
    scale: float = 1.0

@dataclass
class Velocity:
    dx: float
    dy: float

@dataclass
class Sprite:
    image_name: str
    width: int
    height: int
    layer: int = 0

@dataclass
class Selectable:
    selected: bool = False
