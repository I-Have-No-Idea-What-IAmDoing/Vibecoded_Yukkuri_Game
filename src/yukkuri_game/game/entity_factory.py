"""
Entity Factory Stub.
"""
from typing import Any
from ..engine.ecs import World

class EntityFactory:
    """
    Factory for creating entities.
    """
    def __init__(self, world: World):
        self.world = world

    def create_yukkuri(self, type_id: str, x: float, y: float) -> int:
        return self.world.create_entity()

    def create_item(self, type_id: str, x: float, y: float) -> int:
        return self.world.create_entity()
