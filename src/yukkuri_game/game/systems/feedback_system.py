"""
Module defining the FeedbackSystem logic.
"""

import random
from ...engine.ecs import System, World
from ...engine.event_bus import EventBus
from ...engine.audio import AudioManager
from ..components import Transform, FloatingText
from ..yukkuri_components import YukkuriStats, Dead, EmotionalState
from ..events import (
    EntitySoldEvent,
    EntityGrewEvent,
    EntityTrainedEvent,
    EntityPunishedEvent,
    EntityDiedEvent,
    LogMessageEvent,
)
from ..prefabs.effects import create_floating_text


class FeedbackSystem(System):
    """
    System responsible for visual and textual feedback.
    Handles floating text and log messages.

    Attributes:
        event_bus (Optional[EventBus]): The event bus to listen for game events and publish log events.
        world (World): The ECS World.
    """

    def __init__(self, world: World):
        """
        Initializes the FeedbackSystem.

        Args:
            world (World): The ECS World.
        """
        self.event_bus: EventBus | None = world.services.get(EventBus)
        self.world = world

        # Subscribe to events
        if self.event_bus:
            self.event_bus.subscribe(EntitySoldEvent, self.on_entity_sold)
            self.event_bus.subscribe(EntityGrewEvent, self.on_growth)
            self.event_bus.subscribe(EntityDiedEvent, self.on_death)
            self.event_bus.subscribe(EntityTrainedEvent, self.on_trained)
            self.event_bus.subscribe(EntityPunishedEvent, self.on_punished)

    def update(self, world: World, dt: float) -> None:
        """
        Updates floating text entities and handles ambient feedback (crying).

        Args:
            world (World): The ECS World.
            dt (float): Delta time.

        Returns:
            None
        """
        # Ambient Crying Logic
        audio = world.services.try_get(AudioManager)
        if audio:
            for entity, (stats,) in world.get_components_tuple(YukkuriStats):
                if world.has_component(entity, Dead):
                    continue

                # Check for EmotionalState
                emotional = world.get_component(entity, EmotionalState)

                # Default probability logic
                prob = 0.01 * dt  # 1% chance per second

                if emotional:
                    if emotional.happiness < -30.0:
                        prob = 0.1 * dt  # 10% chance per second
                    else:
                        prob = 0.01 * dt
                else:
                    prob = 0.01 * dt

                if random.random() < prob:
                    audio.play_sound("cry")

        to_destroy = []
        for entity, (transform, text_comp) in world.get_components_tuple(
            Transform, FloatingText
        ):
            # Move up
            transform.y += text_comp.velocity_y * dt

            # Decrease lifetime
            text_comp.lifetime -= dt
            if text_comp.lifetime <= 0:
                to_destroy.append(entity)

        for entity in to_destroy:
            world.destroy_entity(entity)

    def on_entity_sold(self, event: EntitySoldEvent) -> None:
        """
        Handles EntitySoldEvent.

        Args:
            event (EntitySoldEvent): The event data.

        Returns:
            None
        """
        create_floating_text(
            self.world,
            event.position[0],
            event.position[1] - 30,
            f"+${event.value}",
            (255, 215, 0),  # Gold
            size=24,
        )

        if self.event_bus:
            self.event_bus.publish(
                LogMessageEvent(
                    message=f"Sold entity for ${event.value}.", color=(255, 215, 0)
                )
            )

    def on_growth(self, event: EntityGrewEvent) -> None:
        """
        Handles EntityGrewEvent.

        Args:
            event (EntityGrewEvent): The event data.

        Returns:
            None
        """
        name = "Entity"
        stats = self.world.get_component(event.entity_id, YukkuriStats)
        if stats:
            name = stats.name

        create_floating_text(
            self.world,
            event.position[0],
            event.position[1] - 40,
            "Level Up!",
            (255, 255, 0),  # Yellow
            size=24,
        )

        if self.event_bus:
            self.event_bus.publish(
                LogMessageEvent(
                    message=f"{name} grew into a {event.new_stage}!", color=(0, 255, 0)
                )
            )

    def on_death(self, event: EntityDiedEvent) -> None:
        """
        Handles EntityDiedEvent.

        Args:
            event (EntityDiedEvent): The event data.

        Returns:
            None
        """
        name = "Entity"
        stats = self.world.get_component(event.entity_id, YukkuriStats)
        if stats:
            name = stats.name

        create_floating_text(
            self.world,
            event.position[0],
            event.position[1] - 30,
            "Dead...",
            (128, 128, 128),  # Gray
            size=20,
        )

        if self.event_bus:
            self.event_bus.publish(
                LogMessageEvent(message=f"{name} has died.", color=(255, 0, 0))
            )

    def on_trained(self, event: EntityTrainedEvent) -> None:
        """
        Handles EntityTrainedEvent.

        Args:
            event (EntityTrainedEvent): The event data.

        Returns:
            None
        """
        name = "Entity"
        stats = self.world.get_component(event.entity_id, YukkuriStats)
        if stats:
            name = stats.name

        create_floating_text(
            self.world,
            event.position[0],
            event.position[1] - 30,
            "Trained!",
            (0, 255, 255),  # Cyan
            size=20,
        )

        if self.event_bus:
            self.event_bus.publish(
                LogMessageEvent(
                    message=f"{name} trained successfully.", color=(0, 255, 255)
                )
            )

    def on_punished(self, event: EntityPunishedEvent) -> None:
        """
        Handles EntityPunishedEvent.

        Args:
            event (EntityPunishedEvent): The event data.

        Returns:
            None
        """
        name = "Entity"
        stats = self.world.get_component(event.entity_id, YukkuriStats)
        if stats:
            name = stats.name

        create_floating_text(
            self.world,
            event.position[0],
            event.position[1] - 30,
            "Punished!",
            (255, 0, 0),  # Red
            size=20,
        )

        if self.event_bus:
            self.event_bus.publish(
                LogMessageEvent(message=f"{name} was punished.", color=(255, 0, 0))
            )
