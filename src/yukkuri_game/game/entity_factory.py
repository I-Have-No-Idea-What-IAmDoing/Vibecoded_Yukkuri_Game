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
    YukkuriStats, AIState, ItemStats, Poop, Personality,
    RelationshipRegistry, EmotionalState, GossipQueue
)
from .trait_service import TraitService

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
        Creates a Yukkuri entity.

        Constructs a Yukkuri entity with all necessary components including Transform, Sprite,
        Physics, Stats, AI, Personality, and Relations.

        Args:
            type_id (str): The type identifier of the Yukkuri (e.g., 'reimu').
            x (float): The initial x-coordinate.
            y (float): The initial y-coordinate.
            age (float): The initial age of the Yukkuri. Defaults to 0.0.
            parents (Optional[List[int]]): List of parent entity IDs. Defaults to None.

        Returns:
            int: The unique ID of the created entity.

        Raises:
            ValueError: If the type_id is not found in loaded resources.
        """
        data = self.rm.yukkuri_types.get(type_id)
        if not data:
            raise ValueError(f"Unknown yukkuri type: {type_id}")

        entity = self.world.create_entity()

        image = self._get_attr(data, 'image', "yukkuri_default.png")
        width = self._get_attr(data, 'width', 64)
        height = self._get_attr(data, 'height', 64)
        max_health = self._get_attr(data, 'max_health', 100)

        # Determine growth stage and scale based on age
        # This logic should match the LifecycleSystem thresholds
        scale = 1.0
        radius = 20
        growth_stage = "Baby"

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
            max_health *= 0.5

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

        # New Movement & Visual Components
        movement_controller = MovementController()
        if self.rm.tuning:
            visuals = self.rm.tuning.visuals.movement
            movement_controller.bob_height = visuals.bob_height
            movement_controller.bob_speed = visuals.bob_speed
        self.world.add_component(entity, movement_controller)
        self.world.add_component(entity, VisualTransform())

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

        # AI
        self.world.add_component(entity, AIState())

        # Personality & Relationships
        self.world.add_component(entity, RelationshipRegistry())

        # New Social System Components
        self.world.add_component(entity, EmotionalState())
        self.world.add_component(entity, GossipQueue())

        ts = self._get_trait_service()
        traits = set()

        # New Quad-Axis Personality System
        # We need to map old "values" (float) to new "axes" (int -100 to 100).
        # And handle trait inheritance.

        # For now, random initialization of axes
        p_kindness = random.randint(-50, 50) # Neutral bias
        p_energy = random.randint(-50, 50)
        p_bravery = random.randint(-50, 50)
        p_greed = random.randint(-50, 50)

        # Inheritance logic
        if parents and ts:
            parent_personalities = [p for p in (self.world.get_component(pid, Personality) for pid in parents) if p]
            if parent_personalities:
                # 50% chance to inherit each trait from parents
                for pp in parent_personalities:
                    for t in pp.traits:
                        if random.random() < 0.5:
                            traits.add(t)

                # Average axes from parents
                avg_kindness = sum(pp.kindness for pp in parent_personalities) // len(parent_personalities)
                avg_energy = sum(pp.energy for pp in parent_personalities) // len(parent_personalities)
                avg_bravery = sum(pp.bravery for pp in parent_personalities) // len(parent_personalities)
                avg_greed = sum(pp.greed for pp in parent_personalities) // len(parent_personalities)

                p_kindness = max(-100, min(100, avg_kindness + random.randint(-20, 20)))
                p_energy = max(-100, min(100, avg_energy + random.randint(-20, 20)))
                p_bravery = max(-100, min(100, avg_bravery + random.randint(-20, 20)))
                p_greed = max(-100, min(100, avg_greed + random.randint(-20, 20)))

        # Random generation if no parents
        if not parents:
            # Gaussian distribution around 0
            p_kindness = int(max(-100, min(100, random.gauss(0, 40))))
            p_energy = int(max(-100, min(100, random.gauss(0, 40))))
            p_bravery = int(max(-100, min(100, random.gauss(0, 40))))
            p_greed = int(max(-100, min(100, random.gauss(0, 40))))

        # Random mutation or random trait if none inherited
        if ts and (random.random() < 0.1 or not traits):
            all_traits = ts.get_all_trait_ids()
            if all_traits:
                traits.add(random.choice(all_traits))

        personality = Personality(
            kindness=p_kindness,
            energy=p_energy,
            bravery=p_bravery,
            greed=p_greed,
            traits=traits
        )
        self.world.add_component(entity, personality)

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
            body = pymunk.Body(1, pymunk.moment_for_circle(1, 0, 10))
            body.position = x, y
            shape = pymunk.Circle(body, 10)
            shape.elasticity = 0.2
            shape.friction = 0.8
            self.physics_system.space.add(body, shape)
            self.world.add_component(entity, PhysicsBody(body=body, shape=shape))
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
            body = pymunk.Body(1, pymunk.moment_for_box(1, (width, height)))
            body.position = x, y
            shape = pymunk.Poly.create_box(body, (width, height))
            shape.elasticity = 0.5
            shape.friction = 0.5
            self.physics_system.space.add(body, shape)
            self.world.add_component(entity, PhysicsBody(body=body, shape=shape))

        return entity
