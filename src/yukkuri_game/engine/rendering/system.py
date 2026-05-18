"""
Rendering System Module.
"""

from typing import Optional

import pygame

from ..ecs import System, World
from ..camera import Camera
from .context import RenderContext
from .pipeline import RenderPipeline
from .surface_cache import SurfaceCache
from ..renderer.renderer import Renderer
from ..renderer.pygame_backend import PygameBackend
from ..resource_manager import ResourceManager
from .passes.culling_pass import CullingPass
from .passes.background_pass import BackgroundPass
from .passes.shadow_pass import ShadowPass
from .passes.sprite_pass import SpritePass
from .passes.light_pass import LightPass
from .passes.occluder_pass import OccluderPass
from .passes.ui_pass import UIPass


class RenderingSystem(System):
    """
    ECS system responsible for rendering the game world.
    """

    def __init__(
        self,
        screen: pygame.Surface,
        world: World,
        pipeline: Optional[RenderPipeline] = None,
        lights_engine: Optional[any] = None,
    ) -> None:
        self.screen = screen
        self.backend = PygameBackend(screen, lights_engine=lights_engine)
        self.renderer = Renderer(self.backend)
        self.surface_cache: Optional[SurfaceCache] = None

        if pipeline is None:
            self.pipeline = RenderPipeline(
                [
                    CullingPass(),
                    BackgroundPass(),
                    ShadowPass(),
                    SpritePass(),
                    LightPass(),
                    OccluderPass(),
                    UIPass(),
                ]
            )
        else:
            self.pipeline = pipeline

    def update(self, world: World, dt: float) -> None:
        """Rendering system does not have a simulation update loop."""
        pass

    def set_ambient_light(self, color: tuple[int, int, int, int]) -> None:
        """Sets the ambient light color."""
        self.renderer.set_ambient_light(color)

    def render(self, world: World, alpha: float) -> None:
        """Renders the world."""
        if self.surface_cache is None:
            rm = world.services.get(ResourceManager)
            self.surface_cache = SurfaceCache(rm)

        camera = world.services.get(Camera)
        sw, sh = self.screen.get_size()
        
        # Ensure camera matrices are updated for this frame
        camera.update_matrices(sw, sh, alpha)

        context = RenderContext(
            world=world,
            renderer=self.renderer,
            camera=camera,
            surface_cache=self.surface_cache,
            sw=sw,
            sh=sh,
            alpha=alpha,
        )

        self.renderer.clear_screen((30, 30, 30))
        self.pipeline.execute(context)
        self.renderer.render()
