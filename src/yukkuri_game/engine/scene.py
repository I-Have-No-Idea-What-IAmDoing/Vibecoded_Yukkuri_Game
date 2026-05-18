"""
Scene Management Module.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar

import pygame
from loguru import logger

from .ecs import World
from .event_manager import EventManager
from .input_manager import InputManager
from .resource_manager import ResourceManager
from .serializer import WorldSerializer
from yukkuri_game.engine.components import Persistable, StableIDComponent

if TYPE_CHECKING:
    from .application import Application


@dataclass
class SceneContext:
    """
    Holds data injected into a scene from the global state.
    """

    data: dict[str, Any] = field(default_factory=dict)


class Scene(ABC):
    """
    Abstract Base Class for all game scenes.
    Each scene has its own ECS World.
    """

    # Declarative injections mapping keys to expected types/classes
    # e.g. { "player_inventory": InventoryComponent }
    INJECTIONS: ClassVar[dict[str, type]] = {}

    def __init__(self, application: "Application"):
        """
        Initializes a Scene.

        Args:
            application (Application): The main application instance.
        """
        self.application = application
        self.world = World()
        self.registered_components: set[type] = {Persistable, StableIDComponent}

        # Register global services
        # Note: application.resources is instance of ResourceManager
        if hasattr(application, "resources"):
            self.world.services.register(application.resources, ResourceManager)
        if hasattr(application, "input_manager"):
            self.world.services.register(application.input_manager, InputManager)
        if hasattr(application, "event_manager"):
            self.world.services.register(application.event_manager, EventManager)

    def register_component(self, component_type: type) -> None:
        """
        Register a component type for serialization support.

        Must be called during setup/init for any component that might be saved/loaded.

        Args:
            component_type (type): The component type to register.
        """
        self.registered_components.add(component_type)

    def setup(self, context: SceneContext) -> None:
        """
        Called after initialization to inject dependencies and setup the world.

        Args:
            context (SceneContext): The context containing injected data.

        Returns:
            None
        """
        pass

    @abstractmethod
    def on_enter(self) -> None:
        """
        Called when the scene becomes active.

        Returns:
            None
        """
        pass

    @abstractmethod
    def on_exit(self) -> None:
        """
        Called when the scene is no longer active.

        Returns:
            None
        """
        pass

    @abstractmethod
    def update(self, dt: float) -> None:
        """
        Update scene logic.

        Args:
            dt (float): Delta time in seconds.

        Returns:
            None
        """
        self.world.update(dt)

    @abstractmethod
    def render(self, alpha: float) -> None:
        """
        Renders the scene.

        Args:
            alpha (float): Interpolation factor (0.0 to 1.0).
        """
        pass

    @abstractmethod
    def handle_event(self, event: pygame.event.Event) -> None:
        """
        Handle input events.

        Args:
            event (pygame.event.Event): The pygame event.

        Returns:
            None
        """
        pass

    def save(self, filepath: str) -> None:
        """
        Save the scene state to a file.

        Use explicitly registered types to ensure serializer knows about
        components even if they aren't currently active on any entity.

        Args:
            filepath (str): The path to the file to save to.

        Returns:
            None

        Raises:
            IOError: If saving fails.
        """
        serializer = WorldSerializer(self.world, self.registered_components)
        try:
            serializer.save_to_file(filepath)
        except Exception as e:
            # Re-raise to let the caller (SceneManager or UI) handle the failure
            raise OSError(f"Failed to save scene to {filepath}") from e

    def load(self, filepath: str) -> None:
        """
        Load the scene state from a file.

        Args:
            filepath (str): The path to the file to load from.

        Returns:
            None

        Raises:
            IOError: If loading fails.
        """
        if not self.registered_components:
            # Warn developer if they forgot to register components
            logger.warning(
                f"Loading scene {self.__class__.__name__} "
                "with no registered components. "
                "Deserialization may fail."
            )

        serializer = WorldSerializer(self.world, self.registered_components)
        try:
            serializer.load_from_file(filepath)
        except Exception as e:
            raise OSError(f"Failed to load scene from {filepath}") from e

    def destroy(self) -> None:
        """
        Cleans up the scene and destroys its ECS World.
        """
        if self.world:
            self.world.destroy()
