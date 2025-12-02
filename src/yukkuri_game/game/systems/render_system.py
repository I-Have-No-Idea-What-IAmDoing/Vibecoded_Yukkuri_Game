"""
Render System Module.
"""
import pygame
from loguru import logger
from ...engine.ecs import System, World
from ...engine.resource_manager import ResourceManager
from ..components import Transform, Sprite, Selectable, FloatingText, PhysicsBody, VisualTransform
from ..yukkurrium import Yukkurrium, WorldRenderer

class RenderSystem(System):
    """
    System responsible for rendering the game world and entities.

    Attributes:
        renderer (WorldRenderer): The world renderer.
    """

    def __init__(self, screen: pygame.Surface, world: World):
        """
        Initializes the RenderSystem.

        Args:
            screen (pygame.Surface): The target Pygame surface.
            world (World): The ECS World instance (used to locate services).
        """
        yukkurrium = world.services.get(Yukkurrium)
        rm = world.services.get(ResourceManager)
        self.renderer = WorldRenderer(screen, yukkurrium, rm)

    @property
    def screen(self) -> pygame.Surface:
        return self.renderer.screen

    @screen.setter
    def screen(self, value: pygame.Surface) -> None:
        self.renderer.screen = value

    def update(self, world: World, dt: float) -> None:
        """
        Renders the world grid and all visible entities.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.

        Returns:
            None
        """
        self.renderer.render(world)
