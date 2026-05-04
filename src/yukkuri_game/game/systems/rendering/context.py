"""
Rendering Context.
"""

from dataclasses import dataclass, field
from typing import List, Tuple

from ....engine.ecs import World
from ...camera import Camera
from ...renderer.renderer import Renderer
from ...components import Transform
from ...surface_cache import SurfaceCache


@dataclass
class RenderContext:
    """Shared state for the rendering pipeline."""

    world: World
    renderer: Renderer
    camera: Camera
    sw: int
    sh: int
    alpha: float
    surface_cache: SurfaceCache

    # Populated by CullingPass: list of (entity_id, transform, ix, iy, screen_x, screen_y)
    visible_render_data: List[Tuple[int, Transform, float, float, float, float]] = field(
        default_factory=list
    )
