"""
Vision and perception components.
"""

from dataclasses import dataclass
from enum import Enum, auto

class FlickerStyle(Enum):
    """
    Enumeration of light source flicker patterns.
    """
    NONE = auto()
    FIRE = auto()
    PULSE = auto()


@dataclass(slots=True)
class Vision:
    """
    Component defining an entity's perception capabilities.
    """
    range: float = 200.0
    fov: float = 360.0


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
