"""
Persistence Components.
"""
from dataclasses import dataclass
import uuid

@dataclass
class StableIDComponent:
    """
    Component for persistent identity.
    """
    id: str

    @staticmethod
    def create_new() -> 'StableIDComponent':
        return StableIDComponent(id=str(uuid.uuid4()))

@dataclass
class Persistable:
    """
    Marker component for entities that should be saved.
    """
    pass
