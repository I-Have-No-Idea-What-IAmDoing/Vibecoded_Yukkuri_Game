"""
Module handling the game world rendering logic.
"""

import pygame
import pygame_light2d as pl2d
from typing import Optional
from pygame_light2d import LightingEngine
from ..engine.ecs import World
from ..engine.resource_manager import ResourceManager
from .components import (
    Transform,
    Sprite,
    Selectable,
    FloatingText,
    PhysicsBody,
    VisualTransform,
)
from .camera import Camera
from .surface_cache import SurfaceCache
from .render_backends import RenderBackend, PygameRenderBackend, Light2DRenderBackend


class WorldRenderer:
    """
    Handles the pure drawing logic for the game world.

    Attributes:
        screen (pygame.Surface): The surface to render to.
        camera (Camera): The world view manager.
        rm (ResourceManager): The resource manager for fetching assets.
        backend (RenderBackend): The rendering backend strategy.
        surface_cache (SurfaceCache): The surface cache.
    """

    def __init__(
        self,
        screen: pygame.Surface,
        camera: Camera,
        resource_manager: ResourceManager,
        lights_engine: Optional[LightingEngine] = None,
        texture_cache_max_size: int = 500
    ):
        """
        Initializes the WorldRenderer.

        Args:
            screen (pygame.Surface): The target Pygame surface.
            camera (Camera): The world view manager.
            resource_manager (ResourceManager): The resource manager.
            lights_engine (LightingEngine, optional): The lighting engine instance.
            texture_cache_max_size (int): The maximum number of textures to keep in memory (for Light2D).
        """
        self.screen = screen
        self.camera = camera
        self.rm = resource_manager

        # Initialize Surface Cache
        self.surface_cache = SurfaceCache(self.rm)

        # Initialize Backend
        if lights_engine:
            self.backend: RenderBackend = Light2DRenderBackend(
                lights_engine, screen, texture_cache_max_size
            )
        else:
            self.backend: RenderBackend = PygameRenderBackend(screen)

    def render(self, world: World, alpha: float = 1.0) -> None:
        """
        Renders the world grid and all visible entities.

        Args:
            world (World): The ECS World.
            alpha (float): Interpolation factor (0.0 to 1.0).
        """
        self.backend.clear()

        # Render background grid
        sw, sh = self.screen.get_size()
        self.backend.draw_grid(self.camera, sw, sh)

        # Render entities
        entities = world.get_entities_with(
            Transform, Sprite, PhysicsBody, VisualTransform
        )
        # Sort by Y for depth (ground position)
        entities.sort(key=lambda e: getattr(world.get_component(e, Transform), "y", 0))

        for ent in entities:
            self._render_entity(world, ent, alpha)

        # Render Floating Text
        self._render_floating_text(world, sw, sh)

    def _render_entity(
        self, world: World, ent: int, alpha: float
    ) -> None:
        """
        Prepares and delegates entity rendering to the backend.

        Args:
            world (World): The ECS World.
            ent (int): Entity ID.
            alpha (float): Interpolation factor.
        """
        transform = world.get_component(ent, Transform)
        sprite = world.get_component(ent, Sprite)
        visual_transform = world.get_component(ent, VisualTransform)
        selectable = world.get_component(ent, Selectable)

        if not (transform and sprite and visual_transform):
            return

        is_selected = selectable.selected if selectable else False

        self.backend.draw_entity(
            self.camera,
            self.surface_cache,
            transform,
            sprite,
            visual_transform,
            is_selected,
            alpha
        )

    def _render_floating_text(self, world: World, sw: int, sh: int) -> None:
        """
        Renders floating text entities.

        Args:
            world (World): The ECS World.
            sw (int): Screen width.
            sh (int): Screen height.
        """
        for entity, (transform, text_comp) in world.get_components_tuple(
            Transform, FloatingText
        ):
            self.backend.draw_floating_text(
                self.camera,
                transform,
                text_comp,
                sw,
                sh
            )
