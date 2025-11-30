"""
Scene Management Module.
"""
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional
import pygame
from .ecs import World

if TYPE_CHECKING:
    from .application import Application

class Scene(ABC):
    """
    Abstract Base Class for all game scenes.
    Each scene has its own ECS World.
    """

    def __init__(self, application: 'Application'):
        self.application = application
        self.world = World()

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
