"""
Core Engine Plugins.
"""

from loguru import logger
from .ecs import Plugin, World
from .systems.time import TimeSystem
from .systems.physics import PhysicsSystem
from .systems.spatial import SpatialSystem, SpatialService
from .systems.lod import LODSystem
from .rendering.system import RenderingSystem
from .camera import Camera


class CoreSimulationPlugin(Plugin):
    """
    Plugin that registers core simulation systems (Time, Physics, Spatial, LOD).
    """

    def __init__(self, gravity=(0, 0), world_settings=None):
        self.gravity = gravity
        self.world_settings = world_settings

    def register(self, world: World) -> None:
        # Resolve world dimensions
        width = 4000.0
        height = 4000.0
        sector_size = 500.0
        
        if self.world_settings:
            width = getattr(self.world_settings, "width", width)
            height = getattr(self.world_settings, "height", height)
            sector_size = getattr(self.world_settings, "sector_size", sector_size)

        # Spatial Service is needed by many systems
        spatial_service = SpatialService(width, height, sector_size)
        world.services.register(spatial_service, SpatialService)

        # Simulation Systems
        world.add_system(TimeSystem())
        
        physics_system = PhysicsSystem(gravity=self.gravity)
        world.add_system(physics_system)
        world.services.register(physics_system, PhysicsSystem)
        
        world.add_system(SpatialSystem(width=width, height=height, sector_size=sector_size))
        world.add_system(LODSystem())


class CoreRenderingPlugin(Plugin):
    """
    Plugin that registers the RenderingSystem and Camera.
    """

    def __init__(self, screen, settings=None):
        self.screen = screen
        self.settings = settings

    def register(self, world: World) -> None:
        logger.debug("CoreRenderingPlugin.register called")
        camera = Camera(self.settings)
        world.services.register(camera, Camera)
        logger.debug(f"Camera registered in services: {world.services.try_get(Camera)}")

        rendering_system = RenderingSystem(self.screen, world)
        world.add_system(rendering_system)
