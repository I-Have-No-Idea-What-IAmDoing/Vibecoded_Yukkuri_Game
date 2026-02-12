"""
Typed Event Definitions.
"""

from dataclasses import dataclass
from typing import Any
from .event_bus import Event


# Input Events
@dataclass(frozen=True)
class ActionEvent(Event):
    """
    Event triggered for a generic action.

    Attributes:
        action (str): The name of the action.
        context (str): The context in which the action occurred.
    """

    action: str
    context: str


@dataclass(frozen=True)
class MoveEvent(ActionEvent):
    """
    Event triggered for movement actions.

    Attributes:
        x (float): The x-coordinate of the movement vector.
        y (float): The y-coordinate of the movement vector.
    """

    x: float
    y: float


# Entity Events
@dataclass(frozen=True)
class EntityCreatedEvent(Event):
    """
    Event triggered when a new entity is created.

    Attributes:
        entity_id (int): The ID of the newly created entity.
    """

    entity_id: int


@dataclass(frozen=True)
class EntityDestroyedEvent(Event):
    """
    Event triggered when an entity is destroyed.

    Attributes:
        entity_id (int): The ID of the destroyed entity.
    """

    entity_id: int


@dataclass(frozen=True)
class ComponentAddedEvent(Event):
    """
    Event triggered when a component is added to an entity.

    Attributes:
        entity_id (int): The ID of the entity.
        component_type (type[Any]): The type of the component added.
        component (Any): The instance of the component added.
    """

    entity_id: int
    component_type: type[Any]
    component: Any


@dataclass(frozen=True)
class ComponentRemovedEvent(Event):
    """
    Event triggered when a component is removed from an entity.

    Attributes:
        entity_id (int): The ID of the entity.
        component_type (type[Any]): The type of the component removed.
        component (Any): The instance of the component removed.
    """

    entity_id: int
    component_type: type[Any]
    component: Any


# Gameplay Events
@dataclass(frozen=True)
class PhysicsFixedUpdateEvent(Event):
    """
    Event triggered after a fixed physics timestep.

    Attributes:
        dt (float): The delta time of the physics step.
    """

    dt: float


@dataclass(frozen=True)
class WorldClearedEvent(Event):
    """
    Event triggered when the world is cleared.
    """

    pass


@dataclass(frozen=True)
class InventoryChangedEvent(Event):
    """
    Event triggered when an inventory item quantity changes.

    Attributes:
        entity_id (int): The ID of the entity owning the inventory.
        item_type_id (str): The ID of the item type.
        delta (int): The change in quantity (positive or negative).
    """

    entity_id: int
    item_type_id: str
    delta: int
