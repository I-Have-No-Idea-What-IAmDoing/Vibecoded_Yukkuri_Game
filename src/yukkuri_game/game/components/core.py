"""
Core game components.
"""

from dataclasses import dataclass

from ...engine.persistence_registry import persistent


@persistent
@dataclass(slots=True)
class Dead:
    """Tag component identifying that the entity is deceased."""
    pass


@persistent
@dataclass(slots=True)
class Poop:
    """Tag component identifying identifying the entity as excrement."""
    pass
