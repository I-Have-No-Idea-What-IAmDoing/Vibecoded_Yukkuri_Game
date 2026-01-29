"""
Lifecycle System - Birth, Growth, and Death.

Manages the lifecycle state machine for Yukkuri entities including:
-   Death detection and corpse conversion.
-   Age-based growth stage transitions (Baby → Child → Adult).
-   Asexual reproduction (breeding) based on happiness/energy thresholds.

Lifecycle States:
-   **Baby**: Small size, limited capabilities (until baby_age_threshold).
-   **Child**: Medium size, can socialize (until child_age_threshold).
-   **Adult**: Full size, can breed when conditions met.
-   **Dead**: No AI processing, visual indicator (flipped sprite).

Growth Transitions:
-   Physical scale increases (1.5x Baby→Child, 1.33x Child→Adult).
-   Health capacity increases, immediate partial heal.
-   Physics shape radius scaled to match visual size.

Breeding Requirements:
-   Must be Adult stage.
-   Happiness above breeding_happiness_threshold.
-   Energy above breeding_energy_threshold.
-   Random chance per tick (breeding_chance).
-   Spawns Baby of same type at offset position.
"""

from loguru import logger

from ...engine import rng
from ...engine.ecs import System, World
from ...engine.event_bus import EventBus
from ..yukkuri_components import YukkuriStats, Needs, AIState, Dead, EmotionalState
from ..components import Sprite, Transform, PhysicsBody
from ..events import EntityDiedEvent, EntityGrewEvent
from ...config import LifecycleSettings
from ..prefabs.yukkuri import create_yukkuri


class LifecycleSystem(System):
    """
    Handles lifecycle events: death, growth, and breeding.

    Processes entities each frame to check for stage transitions
    based on age and breeding eligibility based on stats.

    Attributes:
        settings (LifecycleSettings): Lifecycle settings.
    """

    # Growth constants
    BREEDING_SPAWN_OFFSET = 20.0  # Random offset range for baby spawn position

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
        """
        self._handle_death(world)
        self._handle_growth(world)
        self._handle_breeding(world)

    def _handle_death(self, world: World) -> None:
        """
        Handles death logic for entities with 0 health.

        Args:
            world (World): The ECS World.
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

                # Disable AI
                if world.has_component(entity, AIState):
                    world.remove_component(entity, AIState)

                sprite = world.get_component(entity, Sprite)
                if sprite:
                    sprite.flip_y = True  # Flip upside down as death indicator.

                # Emit Event
                if event_bus:
                    transform = world.get_component(entity, Transform)
                    pos = (transform.x, transform.y) if transform else (0, 0)
                    event_bus.publish(EntityDiedEvent(entity, pos))

    def _handle_growth(self, world: World) -> None:
        """
        Handles growth logic based on age.

        Args:
            world (World): The ECS World.
        """
        for entity, (stats, needs, transform) in world.get_components_tuple(
            YukkuriStats, Needs, Transform
        ):
            if world.has_component(entity, Dead):
                continue

            # Growth Stages: Baby -> Child -> Adult

            # Baby -> Child
            if (
                stats.growth_stage == "Baby"
                and stats.age >= self.settings.baby_age_threshold
            ):
                self._grow_entity(world, entity, stats, needs, transform, "Child", 1.5)

            # Child -> Adult
            elif (
                stats.growth_stage == "Child"
                and stats.age >= self.settings.child_age_threshold
            ):
                self._grow_entity(
                    world, entity, stats, needs, transform, "Adult", 4.0 / 3.0
                )

    def _grow_entity(
        self,
        world: World,
        entity: int,
        stats: YukkuriStats,
        needs: Needs,
        transform: Transform,
        new_stage: str,
        scale_multiplier: float,
    ) -> None:
        """
        Performs the growth transition, updating stats, health, and scale.

        Args:
            world (World): The ECS World.
            entity (int): The entity ID.
            stats (YukkuriStats): The entity's stats.
            needs (Needs): The entity's needs.
            transform (Transform): The entity's transform.
            new_stage (str): The new growth stage name.
            scale_multiplier (float): The factor to scale the entity by.
        """
        logger.info(
            f"{stats.name} is growing from {stats.growth_stage} to {new_stage}!"
        )

        stats.growth_stage = new_stage

        # Scale Transform
        transform.scale *= scale_multiplier

        # Adjust Stats
        if new_stage == "Child":
            needs.max_health += self.settings.child_max_health_bonus

        needs.health += self.settings.growth_health_restore  # Heal on growth
        if needs.health > needs.max_health:
            needs.health = needs.max_health

        physics = world.get_component(entity, PhysicsBody)
        if physics:
            if hasattr(physics.shape, "unsafe_set_radius"):
                new_radius = physics.shape.radius * scale_multiplier
                physics.shape.unsafe_set_radius(new_radius)
            elif hasattr(physics.shape, "unsafe_set_vertices"):
                pass

        # Emit Event
        event_bus = world.services.try_get(EventBus)
        if event_bus:
            event_bus.publish(
                EntityGrewEvent(entity, new_stage, (transform.x, transform.y))
            )

    def _handle_breeding(self, world: World) -> None:
        """
        Handles breeding logic. Check eligibility and spawn offspring.

        Args:
            world (World): The ECS World.
        """
        for entity, (stats, needs, transform) in world.get_components_tuple(
            YukkuriStats, Needs, Transform
        ):
            if world.has_component(entity, Dead):
                continue

            if self._should_breed(world, entity, stats, needs):
                self._breed(world, entity, stats, needs, transform)

    def _should_breed(
        self, world: World, entity: int, stats: YukkuriStats, needs: Needs
    ) -> bool:
        """
        Determines if an entity meets the conditions to breed.

        Args:
            world (World): The ECS World.
            entity (int): Entity ID.
            stats (YukkuriStats): The entity's stats.
            needs (Needs): The entity's needs.

        Returns:
            bool: True if eligible and luck roll succeeds.
        """
        # Must be Adult
        if stats.growth_stage != "Adult":
            return False

        emotional = world.get_component(entity, EmotionalState)
        happiness = 0.0
        if emotional:
            happiness = emotional.happiness

        if (
            happiness >= self.settings.breeding_happiness_threshold
            and needs.energy >= self.settings.breeding_energy_threshold
        ):
            # Chance to breed
            return rng.random_float() < self.settings.breeding_chance

        return False

    def _breed(
        self,
        world: World,
        parent_entity: int,
        parent_stats: YukkuriStats,
        parent_needs: Needs,
        parent_transform: Transform,
    ) -> None:
        """
        Executes breeding action (cost deduction and spawning).

        Args:
            world (World): The ECS World.
            parent_entity (int): The parent entity ID.
            parent_stats (YukkuriStats): The parent's stats.
            parent_needs (Needs): The parent's needs.
            parent_transform (Transform): The parent's transform.
        """
        logger.info(f"{parent_stats.name} is breeding!")

        parent_needs.energy -= self.settings.breeding_cost

        # Spawn Baby at offset position.
        offset_x = rng.uniform(-self.BREEDING_SPAWN_OFFSET, self.BREEDING_SPAWN_OFFSET)
        offset_y = rng.uniform(-self.BREEDING_SPAWN_OFFSET, self.BREEDING_SPAWN_OFFSET)

        create_yukkuri(
            world,
            type_id=parent_stats.type_id,
            x=parent_transform.x + offset_x,
            y=parent_transform.y + offset_y,
            age=0.0,
            parents=[parent_entity],
        )
