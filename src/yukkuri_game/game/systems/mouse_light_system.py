"""
Mouse Light System.
"""

import pygame
from ...engine.ecs import System, World
from ...engine.input_manager import InputManager
from ..components import Transform, LightSource
from ..services import InputService
from ..camera import Camera


class MouseLightSystem(System):
    """
    System that attaches a light source to the mouse cursor.
    """

    def __init__(self) -> None:
        super().__init__()
        self.camera: Camera
        self.input_service: InputService
        self.light_entity = -1
        self.enabled = False  # Default to disabled

    def initialize(self) -> None:
        """Called when the system is added to the world."""
        self.camera = self.ecs_world.services.get(Camera)
        self.input_service = self.ecs_world.services.get(InputService)
        self.light_entity = self._create_mouse_light()

    def _create_mouse_light(self) -> int:
        """Creates the mouse light entity."""
        # Use context to ensure we are creating entity in the correct world
        with self.ecs_world.context():
            entity = self.ecs_world.create_entity()
            self.ecs_world.add_component(entity, Transform(x=0, y=0))
            self.ecs_world.add_component(
                entity,
                LightSource(
                    radius=300.0,
                    color=(255, 255, 255),
                    intensity=0.0,  # Start invisible
                ),
            )
        return entity

    def toggle(self) -> None:
        """Toggles the mouse light."""
        self.enabled = not self.enabled
        # Update intensity based on enabled state
        with self.ecs_world.context():
            light = self.ecs_world.get_component(self.light_entity, LightSource)
            if light:
                light.intensity = 0.8 if self.enabled else 0.0

    def update(self, world: World, dt: float) -> None:
        if not self.enabled:
            return

        # Update position to mouse world position
        # Use the passed 'world' instance which is the current context
        input_manager = world.services.try_get(InputManager)

        if input_manager:
            mx, my = input_manager.get_mouse_position()

            surface = pygame.display.get_surface()
            if surface:
                sw, sh = surface.get_size()
                wx, wy = self.camera.screen_to_world(mx, my, sw, sh)

                transform = world.get_component(self.light_entity, Transform)
                if transform:
                    transform.x = wx
                    transform.y = wy
