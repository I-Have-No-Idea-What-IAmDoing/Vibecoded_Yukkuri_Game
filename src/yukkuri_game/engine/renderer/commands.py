"""
Render Commands Module.
"""

from dataclasses import dataclass
from typing import Any

import pygame

from ..components import FlickerStyle


@dataclass(slots=True)
class RenderCommand:
    """
    Base class for all render commands.
    """
    layer: int
    z_index: float  # For sorting within a layer (usually y-coordinate)


@dataclass(slots=True)
class SpriteCommand(RenderCommand):
    """
    Command to draw a sprite.
    """
    image: pygame.Surface
    position: tuple[float, float]  # Screen coordinates
    rotation: float = 0.0
    scale: float = 1.0
    flip_x: bool = False
    flip_y: bool = False
    color: tuple[int, int, int] | None = None  # Tint
    alpha: int = 255
    selected: bool = False
    cache_key: tuple[Any, ...] | None = None


@dataclass(slots=True)
class TextCommand(RenderCommand):
    """
    Command to draw text.
    """
    text: str
    position: tuple[float, float]  # Screen coordinates
    size: int
    color: tuple[int, int, int]
    alpha: int = 255
    font_name: str | None = None


@dataclass(slots=True)
class LightCommand(RenderCommand):
    """
    Command to update/draw a light source.
    """
    entity_id: int  # To track persistence/updates
    position: tuple[float, float]  # Screen coordinates
    radius: float
    color: tuple[int, int, int, int]
    intensity: float
    flicker_style: FlickerStyle | None = None
    soft_shadows: bool = True
    static: bool = False


@dataclass(slots=True)
class ShadowCommand(RenderCommand):
    """
    Command to draw a simple blob shadow.
    """
    position: tuple[float, float]  # Screen coordinates
    radius: tuple[float, float]  # x, y radius
    color: tuple[int, int, int, int] = (0, 0, 0, 100)


@dataclass(slots=True)
class OccluderCommand(RenderCommand):
    """
    Command to define an occluder polygon.
    """
    entity_id: int
    vertices: list[tuple[float, float]]  # Screen coordinates
    static: bool = False
