"""
Render Commands Module.

This module defines the data structures (commands) used to communicate rendering
operations from the game logic (or RenderSystem) to the Renderer and Backend.
"""

from dataclasses import dataclass
from typing import Any

import pygame

from ..components import FlickerStyle


@dataclass
class RenderCommand:
    """
    Base class for all render commands.

    Attributes:
        layer (int): The sorting layer (lower is drawn first).
        z_index (float): The sorting index within the layer (usually Y-coordinate).
    """

    layer: int
    z_index: float  # For sorting within a layer (usually y-coordinate)


@dataclass
class SpriteCommand(RenderCommand):
    """
    Command to draw a sprite.

    Attributes:
        image (pygame.Surface): The sprite image.
        position (tuple[float, float]): Screen coordinates (x, y).
        rotation (float): Rotation in degrees. Defaults to 0.0.
        scale (float): Scale factor. Defaults to 1.0.
        flip_x (bool): Whether to flip horizontally. Defaults to False.
        flip_y (bool): Whether to flip vertically. Defaults to False.
        color (tuple[int, int, int] | None): RGB tint color. Defaults to None.
        alpha (int): Transparency value (0-255). Defaults to 255.
        selected (bool): Whether to draw selection outline. Defaults to False.
        cache_key (tuple[Any, ...] | None): Key for caching optimizations. Defaults to None.
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


@dataclass
class TextCommand(RenderCommand):
    """
    Command to draw text.

    Attributes:
        text (str): The string to render.
        position (tuple[float, float]): Screen coordinates (x, y).
        size (int): Font size.
        color (tuple[int, int, int]): RGB text color.
        alpha (int): Transparency value (0-255). Defaults to 255.
        font_name (str | None): Name of the system font. Defaults to None.
    """

    text: str
    position: tuple[float, float]  # Screen coordinates
    size: int
    color: tuple[int, int, int]
    alpha: int = 255
    font_name: str | None = None


@dataclass
class LightCommand(RenderCommand):
    """
    Command to update/draw a light source.

    Attributes:
        entity_id (int): Unique ID to track persistence/updates.
        position (tuple[float, float]): Screen coordinates (x, y).
        radius (float): Light radius in pixels.
        color (tuple[int, int, int, int]): RGBA light color.
        intensity (float): Light intensity multiplier.
        flicker_style (FlickerStyle | None): Flicker animation style. Defaults to None.
        soft_shadows (bool): Whether to render soft shadows. Defaults to True.
        static (bool): Whether the light is static (cachable). Defaults to False.
    """

    entity_id: int  # To track persistence/updates
    position: tuple[float, float]  # Screen coordinates
    radius: float
    color: tuple[int, int, int, int]
    intensity: float
    flicker_style: FlickerStyle | None = None
    soft_shadows: bool = True
    static: bool = False


@dataclass
class ShadowCommand(RenderCommand):
    """
    Command to draw a simple blob shadow.

    Attributes:
        position (tuple[float, float]): Screen coordinates (x, y).
        radius (tuple[float, float]): Radius (x, y) for the ellipse.
        color (tuple[int, int, int, int]): RGBA shadow color. Defaults to (0, 0, 0, 100).
    """

    position: tuple[float, float]  # Screen coordinates
    radius: tuple[float, float]  # x, y radius
    color: tuple[int, int, int, int] = (0, 0, 0, 100)


@dataclass
class OccluderCommand(RenderCommand):
    """
    Command to define an occluder polygon.

    Attributes:
        entity_id (int): Unique ID of the occluder entity.
        vertices (list[tuple[float, float]]): List of polygon vertices in screen coordinates.
        static (bool): Whether the occluder is static. Defaults to False.
    """

    entity_id: int
    vertices: list[tuple[float, float]]  # Screen coordinates
    static: bool = False
