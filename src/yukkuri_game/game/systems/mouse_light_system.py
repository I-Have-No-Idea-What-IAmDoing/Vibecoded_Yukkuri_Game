"""
Mouse Light System.
"""

import pygame
from ..engine.system import System
from ..engine.ecs import World
from ..engine.input_manager import InputManager
from ..game.components import Transform, LightSource
from ..game.services import InputService
from ..game.camera import Camera


class MouseLightSystem(System):
    """
    System that attaches a light source to the mouse cursor.
    """

    def __init__(self, world: World, camera: Camera):
        super().__init__(world)
        self.camera = camera
        self.input_service = world.services.get(InputService)
        self.light_entity = self._create_mouse_light()
        self.enabled = False  # Default to disabled

    def _create_mouse_light(self) -> int:
        """Creates the mouse light entity."""
        entity = self.world.create_entity()
        self.world.add_component(entity, Transform(x=0, y=0))
        self.world.add_component(
            entity,
            LightSource(
                radius=300.0,
                color=(255, 255, 255),
                intensity=0.8,
            ),
        )
        return entity

    def toggle(self) -> None:
        """Toggles the mouse light."""
        self.enabled = not self.enabled
        # Update intensity based on enabled state
        light = self.world.get_component(self.light_entity, LightSource)
        if light:
            light.intensity = 0.8 if self.enabled else 0.0

    def update(self, dt: float) -> None:
        if not self.enabled:
            return

        # Update position to mouse world position
        # InputService tracks drag positions, but InputManager has raw mouse pos.
        # We can access InputManager via world services if needed, or use Pygame directly.
        # But InputSystem updates InputService.drag_current_pos? No, only when dragging.

        # Best way is to ask InputManager.
        input_manager = self.world.services.try_get(InputManager)

        if input_manager:
            mx, my = input_manager.get_mouse_position()

            # Need screen dimensions for conversion
            # We can get them from Camera if it stores them, or assume standard resolution?
            # Camera.screen_to_world needs screen_w, screen_h.
            # We can try to get surface size.
            surface = pygame.display.get_surface()
            if surface:
                sw, sh = surface.get_size()
                wx, wy = self.camera.screen_to_world(mx, my, sw, sh)

                transform = self.world.get_component(self.light_entity, Transform)
                if transform:
                    transform.x = wx
                    transform.y = wy
