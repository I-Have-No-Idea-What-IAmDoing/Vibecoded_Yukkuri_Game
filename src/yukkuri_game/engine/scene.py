"""
Scene Management Module.
"""
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional, Dict, Any, Type, ClassVar
from dataclasses import dataclass, field
import pygame
from .ecs import World

if TYPE_CHECKING:
    from .application import Application

@dataclass
class SceneContext:
    """
    Holds data injected into a scene from the global state.
    """
    data: Dict[str, Any] = field(default_factory=dict)

class Scene(ABC):
    """
    Abstract Base Class for all game scenes.
    Each scene has its own ECS World.
    """

    # Declarative injections mapping keys to expected types/classes
    # e.g. { "player_inventory": InventoryComponent }
    INJECTIONS: ClassVar[Dict[str, Type]] = {}

    def __init__(self, application: 'Application'):
        self.application = application
        self.world = World()

    def setup(self, context: SceneContext) -> None:
        """
        Called after initialization to inject dependencies and setup the world.

        Args:
            context (SceneContext): The context containing injected data.
        """
        pass

    @abstractmethod
    def on_enter(self) -> None:
        """Called when the scene becomes active."""
        pass

    @abstractmethod
    def on_exit(self) -> None:
        """Called when the scene is no longer active."""
        pass

    @abstractmethod
    def update(self, dt: float) -> None:
        """
        Update scene logic.

        Args:
            dt (float): Delta time in seconds.
        """
        self.world.update(dt)

    @abstractmethod
    def render(self) -> None:
        """Render the scene."""
        pass

    @abstractmethod
    def handle_event(self, event: pygame.event.Event) -> None:
        """
        Handle input events.

        Args:
            event: The pygame event.
        """
        pass

    def save(self, filepath: str) -> None:
        """
        Save the scene state to a file.
        """
        pass

    def load(self, filepath: str) -> None:
        """
        Load the scene state from a file.
        """
        pass
