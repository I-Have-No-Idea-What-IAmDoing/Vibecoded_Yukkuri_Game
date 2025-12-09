"""
Render System Module.
"""

import pygame
from loguru import logger
from pygame_light2d import LightingEngine
from ...engine.ecs import System, World
from ...engine.resource_manager import ResourceManager
from ..camera import Camera
from ..renderer import WorldRenderer


class RenderSystem(System):
    """
    System responsible for rendering the game world and entities.

    Attributes:
        renderer (WorldRenderer): The world renderer.
    """

    def __init__(self, screen: pygame.Surface, world: World, lights_engine: LightingEngine = None):
        """
        Initializes the RenderSystem.

        Args:
            screen (pygame.Surface): The target Pygame surface.
            world (World): The ECS World instance (used to locate services).
            lights_engine (LightingEngine): The lighting engine to use.
        """
        camera = world.services.get(Camera)
        rm = world.services.get(ResourceManager)
        self.renderer = WorldRenderer(screen, camera, rm, lights_engine)

    @property
    def screen(self) -> pygame.Surface:
        return self.renderer.screen

    @screen.setter
    def screen(self, value: pygame.Surface) -> None:
        self.renderer.screen = value

    def update(self, world: World, alpha: float) -> None:
        """
        Renders the world grid and all visible entities.

        Args:
            world (World): The ECS World.
            alpha (float): Interpolation alpha (0.0 to 1.0).

        Returns:
            None
        """
        logger.trace(f"Rendering frame with alpha {alpha}")
        self.renderer.render(world, alpha=alpha)
