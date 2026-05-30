"""
Core Engine Plugins.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from loguru import logger

from .ecs import Plugin, World
from .systems.time import TimeSystem
from .systems.physics import PhysicsSystem
from .systems.spatial import SpatialSystem, SpatialService
from .systems.lod import LODSystem
from .rendering.system import RenderingSystem
from .camera import Camera

if TYPE_CHECKING:
    import pygame
    from .rendering.pipeline import RenderPipeline



class CoreSimulationPlugin(Plugin):
    """
    Plugin that registers core simulation systems (Time, Physics, Spatial, LOD).
    """

    def __init__(
        self,
        gravity: tuple[float, float] = (0, 0),
        world_settings: Any = None,
    ) -> None:
        """Initialises the plugin.

        Args:
            gravity: Gravity vector applied to the physics system.
            world_settings: Optional world settings (width, height, sector_size).
        """
        self.gravity = gravity
        self.world_settings = world_settings


    def register(self, world: World) -> None:
        """Registers simulation systems (Time, Physics, Spatial, LOD) into the world.

        Args:
            world: The ECS World instance.
        """
        # Resolve world dimensions

        width = 4000.0
        height = 4000.0
        sector_size = 500.0
        
        if self.world_settings:
            width = getattr(self.world_settings, "width", width)
            height = getattr(self.world_settings, "height", height)
            sector_size = getattr(self.world_settings, "sector_size", sector_size)

        from ..engine.protocols import ISpatialService
        from ..engine.protocols import IPhysicsService

        # Spatial Service is needed by many systems
        spatial_service = SpatialService(width, height, sector_size)
        world.services.register(spatial_service, ISpatialService)

        # Simulation Systems
        world.add_system(TimeSystem())
        
        physics_system = PhysicsSystem(gravity=self.gravity)
        world.add_system(physics_system)
        world.services.register(physics_system, IPhysicsService)
        
        world.add_system(SpatialSystem(width=width, height=height, sector_size=sector_size))
        world.add_system(LODSystem())


class CoreRenderingPlugin(Plugin):
    """
    Plugin that registers the RenderingSystem and Camera.
    """

    def __init__(
        self,
        screen: "pygame.Surface | None",
        settings: Any = None,
        pipeline: "RenderPipeline | None" = None,
    ) -> None:
        """Initialises the plugin.

        Args:
            screen: The pygame display surface.
            settings: Optional world settings passed to the Camera.
            pipeline: Optional custom render pipeline. When provided,
                the game-specific gameplay passes (including the UIPass
                that draws the placement ghost sprite) are used instead
                of the default engine-level passes.
        """
        self.screen = screen
        self.settings = settings
        self.pipeline = pipeline

    def register(self, world: World) -> None:
        """Registers Camera and RenderingSystem into the world.

        Args:
            world: The ECS World instance.
        """
        logger.debug("CoreRenderingPlugin.register called")
        camera = Camera(self.settings)
        world.services.register(camera, Camera)
        logger.debug(f"Camera registered in services: {world.services.try_get(Camera)}")

        if self.screen is not None:
            rendering_system = RenderingSystem(
                self.screen, world, pipeline=self.pipeline
            )
            world.add_system(rendering_system)
            world.services.register(rendering_system, RenderingSystem)

