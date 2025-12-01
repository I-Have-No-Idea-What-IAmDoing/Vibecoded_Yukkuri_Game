"""
Persistence Components.
"""
from dataclasses import dataclass

@dataclass
class StableIDComponent:
    """
    Component for persistent identity.
    """
    id: int

@dataclass
class Persistable:
    """
    Marker component for entities that should be saved.
    """
    pass
