import random
from ...engine.ecs import System, World
from ...engine.event_bus import EventBus
from ..yukkuri_components import YukkuriStats, AIState, Dead
from ..components import Sprite, Transform, PhysicsBody
from ..events import EntityDiedEvent, EntityGrewEvent
from ...config import LifecycleSettings
from typing import TYPE_CHECKING
from loguru import logger

if TYPE_CHECKING:
    from ..entity_factory import EntityFactory

class LifecycleSystem(System):
    """
    System responsible for handling lifecycle events: Death, Growth, and Breeding.

    Attributes:
        settings (LifecycleSettings): The configuration settings.
        factory (EntityFactory): Factory to create new entities (babies).
    """

    def __init__(self, settings: LifecycleSettings, entity_factory: "EntityFactory"):
        """
        Initializes the LifecycleSystem.

        Args:
            settings (LifecycleSettings): Lifecycle settings.
            entity_factory (EntityFactory): Entity factory instance.
        """
        self.settings = settings
        self.factory = entity_factory

    def update(self, world: World, dt: float) -> None:
        """
        Updates the lifecycle state of entities.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.

        Returns:
            None
        """
        self._handle_death(world)
        self._handle_growth(world)
        self._handle_breeding(world)

    def _handle_death(self, world: World) -> None:
        """
        Handles death logic for entities with 0 health.

        Args:
            world (World): The ECS World.

        Returns:
            None
        """
        event_bus = world.services.try_get(EventBus)

        for entity, (stats,) in world.get_components_tuple(YukkuriStats):
            # Skip if already dead
            if world.has_component(entity, Dead):
                continue

            if stats.health <= 0:
                stats.health = 0
                logger.info(f"{stats.name} has died.")

                # Tag as Dead
                world.add_component(entity, Dead())

                # Emit Event
                if event_bus:
                    transform = world.get_component(entity, Transform)
                    pos = (transform.x, transform.y) if transform else (0, 0)
                    event_bus.publish(EntityDiedEvent(entity, pos))

                # Disable AI
                if world.has_component(entity, AIState):
                    world.remove_component(entity, AIState)

                # Change Sprite
                sprite = world.get_component(entity, Sprite)
                if sprite:
                    # Try to change to dead sprite if available, otherwise tint or rotate
                    # For now, let's append "_dead" to the image name if possible,
                    # but we can't easily check file existence here without ResourceManager.
                    # As a safe fallback, we can flip it upside down (rotate 180)
                    sprite.rotation = 180.0
                    sprite.flip_y = True
                    # If we had a dead sprite, we'd do: sprite.image_name = sprite.image_name.replace(".png", "_dead.png")

    def _handle_growth(self, world: World) -> None:
        """
        Handles growth logic based on age.

        Args:
            world (World): The ECS World.

        Returns:
            None
        """
        for entity, (stats, transform) in world.get_components_tuple(YukkuriStats, Transform):
            if world.has_component(entity, Dead):
                continue

            # Growth Stages: Baby -> Child -> Adult

            # Baby -> Child
            if stats.growth_stage == "Baby" and stats.age >= self.settings.baby_age_threshold:
                self._grow_entity(world, entity, stats, transform, "Child", 1.5)

            # Child -> Adult
            elif stats.growth_stage == "Child" and stats.age >= self.settings.child_age_threshold:
                self._grow_entity(world, entity, stats, transform, "Adult", 4.0 / 3.0)

    def _grow_entity(self, world: World, entity: int, stats: YukkuriStats, transform: Transform, new_stage: str, scale_multiplier: float) -> None:
        """
        Performs the growth transition.

        Args:
            world (World): The ECS World.
            entity (int): The entity ID.
            stats (YukkuriStats): The entity's stats.
            transform (Transform): The entity's transform.
            new_stage (str): The new growth stage.
            scale_multiplier (float): The scale multiplier.

        Returns:
            None
        """
        logger.info(f"{stats.name} is growing from {stats.growth_stage} to {new_stage}!")

        stats.growth_stage = new_stage

        # Scale Transform
        transform.scale *= scale_multiplier

        # Adjust Stats
        if new_stage == "Child":
            stats.max_health += 50

        stats.health += 50 # Heal on growth
        if stats.health > stats.max_health:
            stats.health = stats.max_health

        # Adjust Physics Body if it exists
        physics = world.get_component(entity, PhysicsBody)
        if physics:
            # We can't easily resize a shape in Pymunk without recreating it or scaling it.
            # But we can't scale a circle shape directly easily?
            # Actually, `shape.unsafe_set_radius` exists for circles.
            if hasattr(physics.shape, "unsafe_set_radius"):
                 # Original radius was 20.
                 # Baby: 10, Child: 15, Adult: 20
                 if new_stage == "Child":
                     physics.shape.unsafe_set_radius(15)
                 elif new_stage == "Adult":
                     physics.shape.unsafe_set_radius(20)
            elif hasattr(physics.shape, "unsafe_set_vertices"): # Box
                pass # Complex

        # Emit Event
        event_bus = world.services.try_get(EventBus)
        if event_bus:
            event_bus.publish(EntityGrewEvent(entity, new_stage, (transform.x, transform.y)))

    def _handle_breeding(self, world: World) -> None:
        """
        Handles breeding logic.

        Args:
            world (World): The ECS World.

        Returns:
            None
        """
        for entity, (stats, transform) in world.get_components_tuple(YukkuriStats, Transform):
            if world.has_component(entity, Dead):
                continue

            # Must be Adult to breed
            if stats.growth_stage != "Adult":
                continue

            if (stats.happiness >= self.settings.breeding_happiness_threshold and
                stats.energy >= self.settings.breeding_energy_threshold):

                # Chance to breed
                if random.random() < self.settings.breeding_chance:
                    self._breed(world, entity, stats, transform)

    def _breed(self, world: World, parent_entity: int, parent_stats: YukkuriStats, parent_transform: Transform) -> None:
        """
        Executes breeding action.

        Args:
            world (World): The ECS World.
            parent_entity (int): The parent entity ID.
            parent_stats (YukkuriStats): The parent's stats.
            parent_transform (Transform): The parent's transform.

        Returns:
            None
        """
        logger.info(f"{parent_stats.name} is breeding!")

        # Reduce energy
        parent_stats.energy -= self.settings.breeding_cost

        # Spawn Baby
        # Offset position slightly
        offset_x = random.uniform(-20, 20)
        offset_y = random.uniform(-20, 20)

        child_id = self.factory.create_yukkuri(
            type_id=parent_stats.type_id,
            x=parent_transform.x + offset_x,
            y=parent_transform.y + offset_y,
            age=0.0 # Explicitly 0
        )

        # Ensure child is Baby (should be default, but handled in factory now)
