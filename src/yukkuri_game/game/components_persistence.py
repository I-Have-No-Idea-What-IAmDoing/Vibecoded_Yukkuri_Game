"""
Persistence Components.
"""
from dataclasses import dataclass

@dataclass
class StableIDComponent:
    """
    Component for persistent identity.
    Ensures that entities retain their identity across save/load cycles.

    Attributes:
        id (int): The unique stable identifier.
    """
    id: int

@dataclass
class Persistable:
    """
    Marker component for entities that should be saved to disk.
    Entities without this component are considered transient and will not be serialized.
    """
    pass
