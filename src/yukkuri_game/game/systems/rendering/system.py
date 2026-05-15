"""
Rendering System.
"""

from typing import Any
import pygame

from ....engine.ecs import System, World
from ....engine.resource_manager import ResourceManager
from ...camera import Camera
from ...surface_cache import SurfaceCache
from ...renderer.renderer import Renderer
from ...renderer.backend import RenderBackend
from ...renderer.pygame_backend import PygameBackend

from .context import RenderContext
from .pipeline import RenderPipeline
from .passes import (
    BackgroundPass,
    CullingPass,
    ShadowPass,
    SpritePass,
    LightPass,
    OccluderPass,
    UIPass,
)


class RenderingSystem(System):
    """
    Main entry point for the Pass-Based Rendering Pipeline.
    Manages the camera, renderer, and executes the rendering passes.
    """

    def __init__(
        self, screen: pygame.Surface, world: World, lights_engine: Any = None
    ):
        self.screen = screen
        self.rm = world.services.get(ResourceManager)
        self.camera = world.services.get(Camera)
        self.surface_cache = SurfaceCache(self.rm, max_size=2000)

        backend: RenderBackend = PygameBackend(screen)
        self.renderer = Renderer(backend)

        # Initialize the pipeline with ordered passes
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

    @property
    def lights_enabled(self) -> bool:
        """Helper to check if lights are enabled."""
        light_pass = self.pipeline.get_pass(LightPass)
        return light_pass.lights_enabled if light_pass else False

    @lights_enabled.setter
    def lights_enabled(self, value: bool) -> None:
        """Helper to toggle lighting on/off."""
        light_pass = self.pipeline.get_pass(LightPass)
        if light_pass:
            light_pass.lights_enabled = value

    def set_ambient_light(self, color: tuple[int, int, int, int]) -> None:
        """Sets global ambient lighting on the backend."""
        self.renderer.set_ambient_light(color)

    def render(self, world: World, alpha: float) -> None:
        """Main render loop."""
        sw, sh = self.screen.get_size()
        correction_x = 1.0
        correction_y = 1.0

        if self.lights_enabled:
            # Check for native resolution scaling if backend supports it
            engine = getattr(self.renderer.backend, "engine", None)
            if engine and hasattr(engine, "_native_res"):
                native_res: tuple[int, int] = getattr(engine, "_native_res")
                nw, nh = native_res
                current_w, current_h = self.screen.get_size()

                if nw > 0 and nh > 0 and current_w > 0 and current_h > 0:
                    stretch_x = current_w / nw
                    stretch_y = current_h / nh
                    correction_x = stretch_y / stretch_x  # Pre-squash X for widescreen.

                sw, sh = nw, nh

        self.camera.set_aspect_correction(correction_x, correction_y)
        self.camera.update_matrices(sw, sh, alpha)

        # 1. Clear Screen
        self.renderer.clear_screen((50, 50, 50))  # Dark grey background

        # 2. Setup Context
        context = RenderContext(
            world=world,
            renderer=self.renderer,
            camera=self.camera,
            sw=sw,
            sh=sh,
            alpha=alpha,
            surface_cache=self.surface_cache,
        )

        # 3. Execute Pipeline
        self.pipeline.execute(context)

        # 4. Render to Backend
        self.renderer.render()
