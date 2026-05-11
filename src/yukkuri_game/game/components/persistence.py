"""
Persistence components.
"""

from dataclasses import dataclass

@dataclass(slots=True)
class StableIDComponent:
    """
    Component for persistent identity.
    """
    id: int


@dataclass(slots=True)
class Persistable:
    """
    Marker component for entities that should be saved to disk.
    """
    pass
