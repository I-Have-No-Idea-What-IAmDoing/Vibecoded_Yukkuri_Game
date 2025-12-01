"""
Entity Factory.
"""
from typing import Any, Optional, Tuple, List
from ..engine.ecs import World
from .prefabs.yukkuri import create_yukkuri
from .prefabs.item import create_item, create_poop
from .prefabs.effects import create_floating_text

class EntityFactory:
    """
    Factory for creating entities.
    Delegates to prefabs.
    """
    def __init__(self, world: World):
        self.world = world

    def create_yukkuri(self, type_id: str, x: float, y: float, age: float = 0.0, parents: Optional[List[int]] = None) -> int:
        return create_yukkuri(self.world, type_id, x, y, age, parents)

    def create_item(self, type_id: str, x: float, y: float) -> int:
        return create_item(self.world, type_id, x, y)

    def create_poop(self, x: float, y: float) -> int:
        return create_poop(self.world, x, y)

    def create_floating_text(self, x: float, y: float, text: str, color: Tuple[int, int, int], size: int = 20) -> int:
        return create_floating_text(self.world, x, y, text, color, size)
