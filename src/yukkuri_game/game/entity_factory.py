"""
Entity Factory Module.
"""

from typing import Optional, Tuple, List
from ..engine.ecs import World
from .prefabs.yukkuri import create_yukkuri
from .prefabs.item import create_item, create_poop
from .prefabs.effects import create_floating_text


class EntityFactory:
    """
    Factory for creating entities within the game world.
    Delegates specific entity creation logic to prefab functions.

    Attributes:
        world (World): The ECS world instance.
    """

    def __init__(self, world: World) -> None:
        """
        Initializes the EntityFactory.

        Args:
            world (World): The ECS world instance.
        """
        self.world = world

    def create_yukkuri(
        self,
        type_id: str,
        x: float,
        y: float,
        age: float = 0.0,
        parents: Optional[List[int]] = None,
    ) -> int:
        """
        Creates a Yukkuri entity.

        Args:
            type_id (str): The type identifier of the Yukkuri (e.g., 'reimu').
            x (float): The initial x-coordinate.
            y (float): The initial y-coordinate.
            age (float, optional): The initial age of the Yukkuri. Defaults to 0.0.
            parents (Optional[List[int]], optional): List of parent entity IDs. Defaults to None.

        Returns:
            int: The ID of the created entity.
        """
        return create_yukkuri(self.world, type_id, x, y, age, parents)

    def create_item(self, type_id: str, x: float, y: float) -> int:
        """
        Creates an Item entity.

        Args:
            type_id (str): The type identifier of the item.
            x (float): The initial x-coordinate.
            y (float): The initial y-coordinate.

        Returns:
            int: The ID of the created entity.
        """
        return create_item(self.world, type_id, x, y)

    def create_poop(self, x: float, y: float) -> int:
        """
        Creates a Poop entity.

        Args:
            x (float): The initial x-coordinate.
            y (float): The initial y-coordinate.

        Returns:
            int: The ID of the created entity.
        """
        return create_poop(self.world, x, y)

    def create_floating_text(
        self, x: float, y: float, text: str, color: Tuple[int, int, int], size: int = 20
    ) -> int:
        """
        Creates a floating text effect entity.

        Args:
            x (float): The initial x-coordinate.
            y (float): The initial y-coordinate.
            text (str): The text to display.
            color (Tuple[int, int, int]): The RGB color of the text.
            size (int, optional): The font size. Defaults to 20.

        Returns:
            int: The ID of the created entity.
        """
        return create_floating_text(self.world, x, y, text, color, size)
