import pymunk
from ..engine.ecs import World
from .components import Transform, Sprite, Selectable, PhysicsBody
from .yukkuri_components import YukkuriStats, AIState, ItemStats

class EntityFactory:
    """
    Factory class for creating game entities.

    Handles the creation of Yukkuris and Items, attaching necessary components.

    Attributes:
        world (World): The ECS World instance where entities are created.
        rm (ResourceManager): The resource manager to fetch entity data.
    """

    def __init__(self, world: World, resource_manager, physics_system=None):
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

        # Core Components
        self.world.add_component(entity, Transform(x=x, y=y))
        self.world.add_component(entity, Sprite(
            image_name=data.get("image", "yukkuri_default.png"),
            width=data.get("width", 64),
            height=data.get("height", 64)
        ))
        self.world.add_component(entity, Selectable())

        # Yukkuri Stats
        stats = YukkuriStats(
            name=f"{type_id}_{entity}",
            type_id=type_id,
            max_health=data.get("max_health", 100),
            health=data.get("max_health", 100)
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
        self.world.add_component(entity, Sprite(
            image_name=data.get("image", "item_default.png"),
            width=data.get("width", 32),
            height=data.get("height", 32)
        ))
        self.world.add_component(entity, Selectable())

        stats = ItemStats(
            name=data.get("name", "Item"),
            type_id=type_id,
            cost=data.get("cost", 10),
            nutrition=data.get("nutrition", 0),
            fun=data.get("fun", 0),
            comfort=data.get("comfort", 0),
            is_portable=data.get("is_portable", False)
        )
        self.world.add_component(entity, stats)

        # Physics
        if self.physics_system:
            mass = 1
            width = data.get("width", 32)
            height = data.get("height", 32)
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
