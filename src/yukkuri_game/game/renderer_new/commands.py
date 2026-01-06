from dataclasses import dataclass
from typing import Tuple, Optional, Any, List
import pygame
from ..components import FlickerStyle


@dataclass
class RenderCommand:
    """Base class for all render commands."""

    layer: int
    z_index: float  # For sorting within a layer (usually y-coordinate)


@dataclass
class SpriteCommand(RenderCommand):
    """Command to draw a sprite."""

    image: pygame.Surface
    position: Tuple[float, float]  # Screen coordinates
    rotation: float = 0.0
    scale: float = 1.0
    flip_x: bool = False
    flip_y: bool = False
    color: Optional[Tuple[int, int, int]] = None  # Tint
    alpha: int = 255
    selected: bool = False
    cache_key: Optional[Tuple[Any, ...]] = None


@dataclass
class TextCommand(RenderCommand):
    """Command to draw text."""

    text: str
    position: Tuple[float, float]  # Screen coordinates
    size: int
    color: Tuple[int, int, int]
    alpha: int = 255
    font_name: Optional[str] = None


@dataclass
class LightCommand(RenderCommand):
    """Command to update/draw a light source."""

    entity_id: int  # To track persistence/updates
    position: Tuple[float, float]  # Screen coordinates
    radius: float
    color: Tuple[int, int, int, int]
    intensity: float
    flicker_style: Optional[FlickerStyle] = None


@dataclass
class ShadowCommand(RenderCommand):
    """Command to draw a simple blob shadow."""

    position: Tuple[float, float]  # Screen coordinates
    radius: Tuple[float, float]  # x, y radius
    color: Tuple[int, int, int, int] = (0, 0, 0, 100)


@dataclass
class OccluderCommand(RenderCommand):
    """Command to define an occluder polygon."""

    entity_id: int
    vertices: List[Tuple[float, float]]  # Screen coordinates
