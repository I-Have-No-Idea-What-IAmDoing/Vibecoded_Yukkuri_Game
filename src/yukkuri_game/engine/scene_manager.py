"""
Scene Manager Module.
"""
from typing import Optional, List, TYPE_CHECKING
import pygame

if TYPE_CHECKING:
    from .scene import Scene

class SceneManager:
    """
    Manages a stack of Scene objects.
    """
    def __init__(self) -> None:
        self._scenes: List['Scene'] = []

    @property
    def current_scene(self) -> Optional['Scene']:
        return self._scenes[-1] if self._scenes else None

    def push(self, scene: 'Scene') -> None:
        """
        Push a new scene onto the stack.

        Args:
            scene (Scene): The scene to push.
        """
        # Note: We might want to call on_exit (suspend) on the current scene
        # but the proposal says "Each Scene owns its own ECS World", so they are independent.
        # Suspending is not strictly required unless we want to pause logic.
        self._scenes.append(scene)
        scene.on_enter()

    def pop(self) -> None:
        """Pop the current scene from the stack."""
        if self._scenes:
            scene = self._scenes.pop()
            scene.on_exit()
            # If there is a scene below, we might want to "resume" it.
            # Currently `on_enter` is for initialization, maybe `on_resume`?
            # For now, we assume simple stack behavior.

    def replace(self, scene: 'Scene') -> None:
        """
        Replace the current scene with a new one.

        Args:
            scene (Scene): The new scene.
        """
        if self._scenes:
            self.pop()
        self.push(scene)

    def update(self, dt: float) -> None:
        """
        Update the current scene.

        Args:
            dt (float): Delta time in seconds.
        """
        if self.current_scene:
            self.current_scene.update(dt)

    def render(self) -> None:
        """Render the current scene."""
        if self.current_scene:
            self.current_scene.render()

    def handle_event(self, event: pygame.event.Event) -> None:
        """
        Handle events in the current scene.

        Args:
            event: The pygame event.
        """
        if self.current_scene:
            self.current_scene.handle_event(event)
