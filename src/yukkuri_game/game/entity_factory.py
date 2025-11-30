"""
Module responsible for creating game entities.
"""
import pymunk
import random
from typing import Any, Optional, TYPE_CHECKING, List
from ..engine.ecs import World
from .components import (
    Transform, Sprite, Selectable, PhysicsBody, FloatingText,
    MovementController, VisualTransform
)
from .yukkuri_components import (
    YukkuriStats, AIState, ItemStats, Poop, Personality, RelationshipRegistry,
    EmotionalState, PersonalityAxis, GossipQueue
)
from .trait_service import TraitService
from .collision_constants import CollisionCategories
from .prefabs.yukkuri import create_yukkuri

if TYPE_CHECKING:
    from ..engine.resource_manager import ResourceManager
    from .systems.physics import PhysicsSystem

class EntityFactory:
    """
    Factory class for creating game entities.

    Handles the creation of Yukkuris and Items, attaching necessary components.

    Attributes:
        world (World): The ECS World instance where entities are created.
        rm (ResourceManager): The resource manager to fetch entity data.
        physics_system (PhysicsSystem): The physics system instance, used to add bodies to the space.
    """

    def __init__(self, world: World):
        """
        Initializes the EntityFactory.

        Args:
            world (World): The ECS World instance.
        """
        self.world = world
        from ..engine.resource_manager import ResourceManager
        from .systems.physics import PhysicsSystem
        self.rm = world.services.get(ResourceManager)
        self.physics_system = world.services.try_get(PhysicsSystem)

    def _get_trait_service(self) -> Optional[TraitService]:
         """
         Retrieves the TraitService from the world's service locator.

         Returns:
             Optional[TraitService]: The TraitService instance, or None if not found.
         """
         ts = self.world.services.try_get(TraitService)
         if ts is None:
             from loguru import logger
             logger.error("TraitService not found in EntityFactory! Yukkuri created without traits.")
         return ts

    def _get_attr(self, data: Any, key: str, default: Any = None) -> Any:
        """
        Helper to get an attribute from either a dict or an object (msgspec struct).

        Args:
            data (Any): The data object (dict or msgspec.Struct).
            key (str): The attribute key.
            default (Any): The default value if the key is missing.

        Returns:
            Any: The attribute value or the default.
        """
        if isinstance(data, dict):
            return data.get(key, default)
        return getattr(data, key, default)

    def create_yukkuri(self, type_id: str, x: float, y: float, age: float = 0.0, parents: Optional[List[int]] = None) -> int:
        """
        Creates a Yukkuri entity using the prefab.
        """
        return create_yukkuri(self.world, type_id, x, y, age, parents)

    def _add_physics(self, entity: int, shape_type: str, mass: float, position: tuple[float, float],
                 radius_or_size: Any, collision_category: int, collision_mask: int,
                 elasticity: float = 0.5, friction: float = 0.5, set_userdata: bool = False) -> None:
        """
        Adds a physics body to an entity.

        Args:
            entity (int): The entity ID.
            shape_type (str): "circle" or "box".
            mass (float): The mass of the body.
            position (tuple[float, float]): Initial position (x, y).
            radius_or_size (Any): Radius (float) if circle, size (tuple) if box.
            collision_category (int): Bitmask category.
            collision_mask (int): Bitmask mask.
            elasticity (float): Bounciness.
            friction (float): Friction.
            set_userdata (bool): Whether to set body.userdata to entity ID.
        """
        if not self.physics_system:
            return

        if shape_type == "circle":
            radius = float(radius_or_size)
            inertia = pymunk.moment_for_circle(mass, 0, radius)
            body = pymunk.Body(mass, inertia)
            shape = pymunk.Circle(body, radius)
        elif shape_type == "box":
            width, height = radius_or_size
            inertia = pymunk.moment_for_box(mass, (width, height))
            body = pymunk.Body(mass, inertia)
            shape = pymunk.Poly.create_box(body, (width, height))
        else:
            raise ValueError(f"Unknown shape type: {shape_type}")

        body.position = position
        shape.elasticity = elasticity
        shape.friction = friction
        shape.filter = pymunk.ShapeFilter(categories=collision_category, mask=collision_mask)

        if set_userdata:
            body.userdata = entity

        self.physics_system.space.add(body, shape)
        self.world.add_component(entity, PhysicsBody(body=body, shape=shape))

    def create_floating_text(self, x: float, y: float, text: str, color: tuple[int, int, int], size: int = 20, lifetime: float = 2.0, velocity_y: float = -50.0) -> int:
        """
        Creates a floating text entity.

        Args:
            x (float): The x-coordinate.
            y (float): The y-coordinate.
            text (str): The text content.
            color (tuple[int, int, int]): The text color.
            size (int): The font size. Defaults to 20.
            lifetime (float): Duration in seconds before the text is removed. Defaults to 2.0.
            velocity_y (float): Vertical velocity in pixels/second. Defaults to -50.0.

        Returns:
            int: The unique ID of the created entity.
        """
        entity = self.world.create_entity()
        self.world.add_component(entity, Transform(x=x, y=y))
        self.world.add_component(entity, FloatingText(
            text=text, color=color, lifetime=lifetime, max_lifetime=lifetime,
            velocity_y=velocity_y, size=size
        ))
        return entity

    def create_poop(self, x: float, y: float) -> int:
        """
        Creates a Poop entity.

        Args:
            x (float): The x-coordinate.
            y (float): The y-coordinate.

        Returns:
            int: The unique ID of the created entity.
        """
        entity = self.world.create_entity()
        self.world.add_component(entity, Transform(x=x, y=y))
        self.world.add_component(entity, Sprite(image_name="poop.png", width=32, height=32))
        self.world.add_component(entity, Selectable())
        self.world.add_component(entity, Poop())
        self.world.add_component(entity, VisualTransform())

        if self.physics_system:
            self._add_physics(
                entity=entity,
                shape_type="circle",
                mass=1,
                position=(x, y),
                radius_or_size=10,
                collision_category=CollisionCategories.POOP,
                collision_mask=CollisionCategories.ALL,
                elasticity=0.2,
                friction=0.8
            )
        return entity

    def create_item(self, type_id: str, x: float, y: float) -> int:
        """
        Creates an Item entity.

        Args:
            type_id (str): The item type identifier.
            x (float): The x-coordinate.
            y (float): The y-coordinate.

        Returns:
            int: The unique ID of the created entity.

        Raises:
            ValueError: If the item type is unknown.
        """
        data = self.rm.item_types.get(type_id)
        if not data:
            raise ValueError(f"Unknown item type: {type_id}")

        entity = self.world.create_entity()
        self.world.add_component(entity, Transform(x=x, y=y))

        image = self._get_attr(data, 'image', "item_default.png")
        width = self._get_attr(data, 'width', 32)
        height = self._get_attr(data, 'height', 32)
        frame_count = self._get_attr(data, 'frame_count', 1)
        frame_duration = self._get_attr(data, 'frame_duration', 0.1)
        loop = self._get_attr(data, 'loop', True)

        self.world.add_component(entity, Sprite(
            image_name=image, width=width, height=height, frame_count=frame_count,
            frame_duration=frame_duration, loop=loop, is_animating=(frame_count > 1)
        ))
        self.world.add_component(entity, Selectable())
        self.world.add_component(entity, VisualTransform())

        stats = ItemStats(
            name=self._get_attr(data, 'name', "Item"),
            type_id=type_id,
            cost=self._get_attr(data, 'cost', 10),
            nutrition=self._get_attr(data, 'nutrition', 0) or 0,
            fun=self._get_attr(data, 'fun', 0) or 0,
            comfort=self._get_attr(data, 'comfort', 0) or 0,
            is_portable=self._get_attr(data, 'is_portable', False)
        )
        self.world.add_component(entity, stats)

        if self.physics_system:
             self._add_physics(
                entity=entity,
                shape_type="box",
                mass=1,
                position=(x, y),
                radius_or_size=(width, height),
                collision_category=CollisionCategories.ITEM,
                collision_mask=CollisionCategories.WALL | CollisionCategories.POOP | CollisionCategories.ITEM,
                elasticity=0.5,
                friction=0.5
            )

        return entity
