"""
Module defining the LifecycleSystem logic.
"""
import random
from ...engine.ecs import System, World
from ...engine.event_bus import EventBus
from ..yukkuri_components import YukkuriStats, Needs, AIState, Dead, EmotionalState
from ..components import Sprite, Transform, PhysicsBody
from ..events import EntityDiedEvent, EntityGrewEvent
from ...config import LifecycleSettings
from ..prefabs.yukkuri import create_yukkuri
from typing import TYPE_CHECKING
from loguru import logger

class LifecycleSystem(System):
    """
    System responsible for handling lifecycle events: Death, Growth, and Breeding.

    Attributes:
        settings (LifecycleSettings): The configuration settings.
    """

    def __init__(self, settings: LifecycleSettings):
        """
        Initializes the LifecycleSystem.

        Args:
            settings (LifecycleSettings): Lifecycle settings.
        """
        self.settings = settings

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

        for entity, (stats, needs) in world.get_components_tuple(YukkuriStats, Needs):
            # Skip if already dead
            if world.has_component(entity, Dead):
                continue

            if needs.health <= 0:
                needs.health = 0
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
                    sprite.flip_y = True

    def _handle_growth(self, world: World) -> None:
        """
        Handles growth logic based on age.

        Args:
            world (World): The ECS World.

        Returns:
            None
        """
        for entity, (stats, needs, transform) in world.get_components_tuple(YukkuriStats, Needs, Transform):
            if world.has_component(entity, Dead):
                continue

            # Growth Stages: Baby -> Child -> Adult

            # Baby -> Child
            if stats.growth_stage == "Baby" and stats.age >= self.settings.baby_age_threshold:
                self._grow_entity(world, entity, stats, needs, transform, "Child", 1.5)

            # Child -> Adult
            elif stats.growth_stage == "Child" and stats.age >= self.settings.child_age_threshold:
                self._grow_entity(world, entity, stats, needs, transform, "Adult", 4.0 / 3.0)

    def _grow_entity(self, world: World, entity: int, stats: YukkuriStats, needs: Needs, transform: Transform, new_stage: str, scale_multiplier: float) -> None:
        """
        Performs the growth transition.

        Args:
            world (World): The ECS World.
            entity (int): The entity ID.
            stats (YukkuriStats): The entity's stats.
            needs (Needs): The entity's needs.
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
            needs.max_health += 50

        needs.health += 50 # Heal on growth
        if needs.health > needs.max_health:
            needs.health = needs.max_health

        # Adjust Physics Body if it exists
        physics = world.get_component(entity, PhysicsBody)
        if physics:
            # We can't easily resize a shape in Pymunk without recreating it or scaling it.
            # But we can't scale a circle shape directly easily?
            # Actually, `shape.unsafe_set_radius` exists for circles.
            if hasattr(physics.shape, "unsafe_set_radius"):
                 # Scale the radius proportionally
                 # This supports non-standard sized entities (e.g. giants, minis) correctly
                 new_radius = physics.shape.radius * scale_multiplier
                 physics.shape.unsafe_set_radius(new_radius)
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
        for entity, (stats, needs, transform) in world.get_components_tuple(YukkuriStats, Needs, Transform):
            if world.has_component(entity, Dead):
                continue

            # Must be Adult to breed
            if stats.growth_stage != "Adult":
                continue

            emotional = world.get_component(entity, EmotionalState)
            happiness = 0.0
            if emotional:
                happiness = emotional.happiness

            if (happiness >= self.settings.breeding_happiness_threshold and
                needs.energy >= self.settings.breeding_energy_threshold):

                # Chance to breed
                if random.random() < self.settings.breeding_chance:
                    self._breed(world, entity, stats, needs, transform)

    def _breed(self, world: World, parent_entity: int, parent_stats: YukkuriStats, parent_needs: Needs, parent_transform: Transform) -> None:
        """
        Executes breeding action.

        Args:
            world (World): The ECS World.
            parent_entity (int): The parent entity ID.
            parent_stats (YukkuriStats): The parent's stats.
            parent_needs (Needs): The parent's needs.
            parent_transform (Transform): The parent's transform.

        Returns:
            None
        """
        logger.info(f"{parent_stats.name} is breeding!")

        # Reduce energy
        parent_needs.energy -= self.settings.breeding_cost

        # Spawn Baby
        # Offset position slightly
        offset_x = random.uniform(-20, 20)
        offset_y = random.uniform(-20, 20)

        create_yukkuri(
            world,
            type_id=parent_stats.type_id,
            x=parent_transform.x + offset_x,
            y=parent_transform.y + offset_y,
            age=0.0,
            parents=[parent_entity]
        )
