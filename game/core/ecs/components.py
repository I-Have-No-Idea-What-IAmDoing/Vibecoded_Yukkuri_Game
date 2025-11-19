"""
Core components for the entity-component system.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any

from game.core.data.schemas import BehaviorSchema


@dataclass
class Needs:
    """Stores the needs of a yukkuri."""
    values: Dict[str, float] = field(default_factory=dict)


@dataclass
class Personality:
    """Stores the personality traits of a yukkuri."""
    values: Dict[str, float] = field(default_factory=dict)


@dataclass
class Position:
    """Stores the position of an entity."""
    x: int
    y: int


@dataclass
class ItemInfo:
    """Stores information about an item."""
    item_id: str
    tags: List[str] = field(default_factory=list)
    effects: Dict[str, Dict[str, float]] = field(default_factory=dict)
    size: Dict[str, int] = field(default_factory=dict)


@dataclass
class AIProfile:
    """Links a yukkuri to its AI behavior profile."""
    profile_id: str
    behavior: BehaviorSchema


@dataclass
class Blackboard:
    """A simple blackboard for the AI to store its working memory."""
    data: Dict[str, Any] = field(default_factory=dict)
