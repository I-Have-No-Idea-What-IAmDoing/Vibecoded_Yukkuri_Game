"""
Typed Event Definitions.
"""

from dataclasses import dataclass
from typing import Any
from .event_bus import Event


# Input Events
@dataclass(frozen=True)
class ActionEvent(Event):
    action: str
    context: str


@dataclass(frozen=True)
class MoveEvent(ActionEvent):
    x: float
    y: float


# Entity Events
@dataclass(frozen=True)
class EntityCreatedEvent(Event):
    entity_id: int


@dataclass(frozen=True)
class EntityDestroyedEvent(Event):
    entity_id: int


@dataclass(frozen=True)
class ComponentAddedEvent(Event):
    entity_id: int
    component_type: type[Any]
    component: Any


@dataclass(frozen=True)
class ComponentRemovedEvent(Event):
    entity_id: int
    component_type: type[Any]
    component: Any


# Gameplay Events
@dataclass(frozen=True)
class PauseEvent(Event):
    paused: bool


@dataclass(frozen=True)
class SpeedChangeEvent(Event):
    speed: float


@dataclass(frozen=True)
class PhysicsFixedUpdateEvent(Event):
    dt: float


@dataclass(frozen=True)
class WorldClearedEvent(Event):
    pass


@dataclass(frozen=True)
class InventoryChangedEvent(Event):
    entity_id: int
    item_type_id: str
    delta: int
