"""
Scene Management Module.
"""
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional, Dict, Any, Type, ClassVar, Set
from dataclasses import dataclass, field
import pygame
from .ecs import World
from .resource_manager import ResourceManager
from .input_manager import InputManager
from .event_manager import EventManager
from .serializer import WorldSerializer
from ..game.components_persistence import Persistable, StableIDComponent

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
        self.registered_components: Set[Type] = {Persistable, StableIDComponent}

        # Register global services
        # Note: application.resources is instance of ResourceManager
        if hasattr(application, 'resources'):
            self.world.services.register(application.resources, ResourceManager)
        if hasattr(application, 'input_manager'):
            self.world.services.register(application.input_manager, InputManager)
        if hasattr(application, 'event_manager'):
            self.world.services.register(application.event_manager, EventManager)

    def register_component(self, component_type: Type) -> None:
        """
        Register a component type for serialization support.
        Must be called during setup/init for any component that might be saved/loaded.
        """
        self.registered_components.add(component_type)

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
        # Use explicitly registered types to ensure serializer knows about
        # components even if they aren't currently active on any entity.
        serializer = WorldSerializer(self.world, self.registered_components)
        try:
            serializer.save_to_file(filepath)
        except Exception as e:
            # Re-raise to let the caller (SceneManager or UI) handle the failure
            raise IOError(f"Failed to save scene to {filepath}") from e

    def load(self, filepath: str) -> None:
        """
        Load the scene state from a file.
        """
        if not self.registered_components:
            # Warn developer if they forgot to register components
            print(f"Warning: Loading scene {self.__class__.__name__} with no registered components. deserialization may fail.")

        serializer = WorldSerializer(self.world, self.registered_components)
        try:
            serializer.load_from_file(filepath)
        except Exception as e:
            raise IOError(f"Failed to load scene from {filepath}") from e
