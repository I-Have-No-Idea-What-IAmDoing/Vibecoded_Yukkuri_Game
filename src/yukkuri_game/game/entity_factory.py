import pymunk
from typing import Any
from typing import Any, Optional, TYPE_CHECKING
from ..engine.ecs import World
from .components import Transform, Sprite, Selectable, PhysicsBody
from .yukkuri_components import YukkuriStats, AIState, ItemStats

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

    def __init__(self, world: World, resource_manager: 'ResourceManager', physics_system: Optional['PhysicsSystem'] = None):
        """
        Initializes the EntityFactory.

        Args:
            world: The ECS World instance.
            resource_manager: The ResourceManager instance.
            physics_system: Optional PhysicsSystem to add bodies to the space.
        """
        self.world = world
        self.rm = resource_manager
        self.physics_system = physics_system

    def _get_attr(self, data: Any, key: str, default: Any = None) -> Any:
        """
        Helper to get an attribute from either a dict or an object (msgspec struct).

        Args:
            data: The data object (dict or struct).
            key: The key/attribute name.
            default: Default value if not found.

        Returns:
            The value of the attribute.
        """
        if isinstance(data, dict):
            return data.get(key, default)
        return getattr(data, key, default)

    def create_yukkuri(self, type_id: str, x: float, y: float) -> int:
        """
        Creates a Yukkuri entity.

        Args:
            type_id: The type identifier for the Yukkuri (e.g., "reimu").
            x: The initial x-coordinate.
            y: The initial y-coordinate.

        Returns:
            int: The ID of the created entity.

        Raises:
            ValueError: If the yukkuri type_id is unknown.
        """
        data = self.rm.yukkuri_types.get(type_id)
        if not data:
            raise ValueError(f"Unknown yukkuri type: {type_id}")

        entity = self.world.create_entity()

        image = self._get_attr(data, 'image', "yukkuri_default.png")
        width = self._get_attr(data, 'width', 64)
        height = self._get_attr(data, 'height', 64)
        max_health = self._get_attr(data, 'max_health', 100)

        # Core Components
        self.world.add_component(entity, Transform(x=x, y=y))
        self.world.add_component(entity, Sprite(
            image_name=image,
            width=width,
            height=height
        ))
        self.world.add_component(entity, Selectable())

        # Yukkuri Stats
        stats = YukkuriStats(
            name=f"{type_id}_{entity}",
            type_id=type_id,
            max_health=max_health,
            health=max_health
        )
        self.world.add_component(entity, stats)

        # AI
        self.world.add_component(entity, AIState())

        # Physics
        if self.physics_system:
            mass = 10
            radius = 20
            inertia = pymunk.moment_for_circle(mass, 0, radius)
            body = pymunk.Body(mass, inertia)
            body.position = x, y
            shape = pymunk.Circle(body, radius)
            shape.elasticity = 0.5
            shape.friction = 0.5

            self.physics_system.space.add(body, shape)
            self.world.add_component(entity, PhysicsBody(body=body, shape=shape))

        return entity

    def create_item(self, type_id: str, x: float, y: float) -> int:
        """
        Creates an Item entity.

        Args:
            type_id: The type identifier for the Item (e.g., "cookie").
            x: The initial x-coordinate.
            y: The initial y-coordinate.

        Returns:
            int: The ID of the created entity.

        Raises:
            ValueError: If the item type_id is unknown.
        """
        data = self.rm.item_types.get(type_id)
        if not data:
            raise ValueError(f"Unknown item type: {type_id}")

        entity = self.world.create_entity()

        self.world.add_component(entity, Transform(x=x, y=y))

        image = self._get_attr(data, 'image', "item_default.png")
        width = self._get_attr(data, 'width', 32)
        height = self._get_attr(data, 'height', 32)

        name = self._get_attr(data, 'name', "Item")
        cost = self._get_attr(data, 'cost', 10)

        nutrition = self._get_attr(data, 'nutrition', 0)
        # Ensure None is treated as 0 if key exists but is None (msgspec optional)
        if nutrition is None: nutrition = 0

        fun = self._get_attr(data, 'fun', 0)
        if fun is None: fun = 0

        comfort = self._get_attr(data, 'comfort', 0)
        if comfort is None: comfort = 0

        is_portable = self._get_attr(data, 'is_portable', False)

        self.world.add_component(entity, Sprite(
            image_name=image,
            width=width,
            height=height
        ))
        self.world.add_component(entity, Selectable())

        stats = ItemStats(
            name=name,
            type_id=type_id,
            cost=cost,
            nutrition=nutrition,
            fun=fun,
            comfort=comfort,
            is_portable=is_portable
        )
        self.world.add_component(entity, stats)

        # Physics
        if self.physics_system:
            mass = 1
            # Use a box for items? or circle? Box is simpler for now given width/height
            inertia = pymunk.moment_for_box(mass, (width, height))
            body = pymunk.Body(mass, inertia)
            body.position = x, y
            # Create a box shape
            shape = pymunk.Poly.create_box(body, (width, height))
            shape.elasticity = 0.5
            shape.friction = 0.5

            self.physics_system.space.add(body, shape)
            self.world.add_component(entity, PhysicsBody(body=body, shape=shape))

        return entity
