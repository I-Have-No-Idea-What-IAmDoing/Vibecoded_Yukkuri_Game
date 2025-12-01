"""
Scene Manager Module.
"""
from typing import Optional, List, TYPE_CHECKING, Dict, Any
import pygame
from loguru import logger
from .scene import Scene, SceneContext

if TYPE_CHECKING:
    pass

class SceneManager:
    """
    Manages a stack of Scene objects and handles global persistence state.
    """
    def __init__(self) -> None:
        self._scenes: List['Scene'] = []
        self.persistent_data: Dict[str, Any] = {}

    @property
    def current_scene(self) -> Optional['Scene']:
        return self._scenes[-1] if self._scenes else None

    def push(self, scene: 'Scene') -> None:
        """
        Push a new scene onto the stack.

        Args:
            scene (Scene): The scene to push.
        """
        # Resolve injections
        context_data = {}
        for key, expected_type in scene.INJECTIONS.items():
            if key in self.persistent_data:
                context_data[key] = self.persistent_data[key]
            else:
                logger.warning(f"Scene {type(scene).__name__} requested injection '{key}' but it was not found in persistent data.")

        context = SceneContext(data=context_data)

        # Call setup with context
        scene.setup(context)

        self._scenes.append(scene)
        scene.on_enter()

    def pop(self) -> None:
        """Pop the current scene from the stack."""
        if self._scenes:
            scene = self._scenes.pop()
            scene.on_exit()

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

    def set_global_data(self, key: str, value: Any) -> None:
        """
        Sets a global persistent data value.
        """
        self.persistent_data[key] = value

    def get_global_data(self, key: str, default: Any = None) -> Any:
        """
        Gets a global persistent data value.
        """
        return self.persistent_data.get(key, default)
