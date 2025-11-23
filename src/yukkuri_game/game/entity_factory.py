import pymunk
from typing import Any
from typing import Any, Optional, TYPE_CHECKING
from ..engine.ecs import World
from .components import Transform, Sprite, Selectable, PhysicsBody, FloatingText
from .yukkuri_components import YukkuriStats, AIState, ItemStats, Poop, Personality, RelationshipRegistry

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

    def _get_attr(self, data: Any, key: str, default: Any = None) -> Any:
        """
        Helper to get an attribute from either a dict or an object (msgspec struct).

        Args:
            data (Any): The data object (dict or struct).
            key (str): The key/attribute name.
            default (Any): Default value if not found.

        Returns:
            Any: The value of the attribute.
        """
        if isinstance(data, dict):
            return data.get(key, default)
        return getattr(data, key, default)

    def create_yukkuri(self, type_id: str, x: float, y: float, age: float = 0.0) -> int:
        """
        Creates a Yukkuri entity.

        Args:
            type_id (str): The type identifier for the Yukkuri (e.g., "reimu").
            x (float): The initial x-coordinate.
            y (float): The initial y-coordinate.
            age (float): The initial age of the Yukkuri. Defaults to 0.0 (Baby).

        Returns:
            int: The ID of the created entity.

        Raises:
            ValueError: If the yukkuri type_id is unknown.
        """
        from .services import TraitService
        import random

        data = self.rm.yukkuri_types.get(type_id)
        if not data:
            raise ValueError(f"Unknown yukkuri type: {type_id}")

        entity = self.world.create_entity()

        image = self._get_attr(data, 'image', "yukkuri_default.png")
        width = self._get_attr(data, 'width', 64)
        height = self._get_attr(data, 'height', 64)
        max_health = self._get_attr(data, 'max_health', 100)

        # Determine growth stage and scale based on age
        # Note: These thresholds should match LifecycleSettings, but we don't have access to config here easily without dependency injection.
        # Ideally, pass config or use constants. For now, assuming Baby < 100, Child < 300
        # Wait, if we create an adult directly, we should scale it.
        # But if the sprite is for an adult (usually), we should scale DOWN for babies.

        scale = 1.0
        radius = 20
        growth_stage = "Baby"

        # Simple logic: if age > 300 -> Adult. If age > 100 -> Child. Else Baby.
        # Baby: scale 0.5. Child: scale 0.75. Adult: scale 1.0.
        if age >= 300:
            growth_stage = "Adult"
            scale = 1.0
            radius = 20
        elif age >= 100:
            growth_stage = "Child"
            scale = 0.75
            radius = 15
        else:
            growth_stage = "Baby"
            scale = 0.5
            radius = 10

            # Reduce stats for babies
            max_health *= 0.5

        # Animation properties
        frame_count = self._get_attr(data, 'frame_count', 1)
        frame_duration = self._get_attr(data, 'frame_duration', 0.1)
        loop = self._get_attr(data, 'loop', True)

        # Core Components
        self.world.add_component(entity, Transform(x=x, y=y, scale=scale))
        self.world.add_component(entity, Sprite(
            image_name=image,
            width=width,
            height=height,
            frame_count=frame_count,
            frame_duration=frame_duration,
            loop=loop,
            is_animating=(frame_count > 1)
        ))
        self.world.add_component(entity, Selectable())

        # Yukkuri Stats
        stats = YukkuriStats(
            name=f"{type_id}_{entity}",
            type_id=type_id,
            max_health=max_health,
            health=max_health,
            age=age,
            growth_stage=growth_stage
        )
        self.world.add_component(entity, stats)

        # Personality & Relationships
        trait_service = self.world.services.try_get(TraitService)
        personality = Personality()

        # Basic Genetics / Randomization
        if trait_service:
            all_traits = list(trait_service.traits.get("traits", {}).keys())
            if all_traits:
                # Chance to have a trait
                if random.random() < 0.3: # 30% chance for a random trait
                    # Avoid conflicts logic would go here, but for now pick one
                    t = random.choice(all_traits)
                    personality.traits.add(t)

            # Randomize values
            personality.values["Compassion"] = random.uniform(0, 100)
            personality.values["Greed"] = random.uniform(0, 100)

        self.world.add_component(entity, personality)
        self.world.add_component(entity, RelationshipRegistry())

        # AI
        self.world.add_component(entity, AIState())

        # Physics
        if self.physics_system:
            mass = 10
            inertia = pymunk.moment_for_circle(mass, 0, radius)
            body = pymunk.Body(mass, inertia)
            body.position = x, y
            shape = pymunk.Circle(body, radius)
            shape.elasticity = 0.5
            shape.friction = 0.5

            self.physics_system.space.add(body, shape)
            self.world.add_component(entity, PhysicsBody(body=body, shape=shape))

        return entity

    def create_floating_text(self, x: float, y: float, text: str, color: tuple[int, int, int], size: int = 20, lifetime: float = 2.0, velocity_y: float = -50.0) -> int:
        """
        Creates a floating text entity.

        Args:
            x (float): X position.
            y (float): Y position.
            text (str): The text to display.
            color (tuple[int, int, int]): The color of the text.
            size (int): Font size.
            lifetime (float): Duration in seconds.
            velocity_y (float): Vertical speed (pixels/sec), negative is up.

        Returns:
            int: The entity ID.
        """
        entity = self.world.create_entity()
        self.world.add_component(entity, Transform(x=x, y=y))
        self.world.add_component(entity, FloatingText(
            text=text,
            color=color,
            lifetime=lifetime,
            max_lifetime=lifetime,
            velocity_y=velocity_y,
            size=size
        ))
        # No Selectable component, as text shouldn't be selectable.
        return entity

    def create_poop(self, x: float, y: float) -> int:
        """
        Creates a Poop entity.

        Args:
            x (float): The x-coordinate.
            y (float): The y-coordinate.

        Returns:
            int: The ID of the created entity.
        """
        entity = self.world.create_entity()

        self.world.add_component(entity, Transform(x=x, y=y))

        # Use a placeholder image if "poop.png" doesn't exist (handled by Sprite/ResourceManager if robust,
        # but here we hardcode a name. Assuming asset exists or will fallback)
        # Ideally this should be in data, but for now hardcoded is fine as per instructions.
        self.world.add_component(entity, Sprite(
            image_name="poop.png",
            width=32,
            height=32
        ))
        self.world.add_component(entity, Selectable())
        self.world.add_component(entity, Poop())

        # Physics
        if self.physics_system:
            mass = 1
            radius = 10
            inertia = pymunk.moment_for_circle(mass, 0, radius)
            body = pymunk.Body(mass, inertia)
            body.position = x, y
            shape = pymunk.Circle(body, radius)
            shape.elasticity = 0.2
            shape.friction = 0.8
            self.physics_system.space.add(body, shape)
            self.world.add_component(entity, PhysicsBody(body=body, shape=shape))

        return entity

    def create_item(self, type_id: str, x: float, y: float) -> int:
        """
        Creates an Item entity.

        Args:
            type_id (str): The type identifier for the Item (e.g., "cookie").
            x (float): The initial x-coordinate.
            y (float): The initial y-coordinate.

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

        # Animation properties
        frame_count = self._get_attr(data, 'frame_count', 1)
        frame_duration = self._get_attr(data, 'frame_duration', 0.1)
        loop = self._get_attr(data, 'loop', True)

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
            height=height,
            frame_count=frame_count,
            frame_duration=frame_duration,
            loop=loop,
            is_animating=(frame_count > 1)
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
