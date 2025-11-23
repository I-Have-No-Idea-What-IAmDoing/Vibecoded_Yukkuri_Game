from ...engine.ecs import System, World
from ...engine.event_bus import EventBus
from ..components import Transform, FloatingText
from ..yukkuri_components import YukkuriStats
from ..events import (
    EntitySoldEvent,
    EntityGrewEvent,
    EntityTrainedEvent,
    EntityPunishedEvent,
    EntityDiedEvent,
    LogMessageEvent
)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..entity_factory import EntityFactory

class FeedbackSystem(System):
    """
    System responsible for visual and textual feedback.
    Handles floating text and log messages.

    Attributes:
        factory (EntityFactory): The entity factory to create floating text.
        event_bus (EventBus): The event bus to listen for game events and publish log events.
    """

    def __init__(self, world: World):
        """
        Initializes the FeedbackSystem.

        Args:
            world (World): The ECS World.
        """
        from ..entity_factory import EntityFactory
        self.factory = world.services.get(EntityFactory)
        self.event_bus = world.services.get(EventBus)
        self.world = world

        # Subscribe to events
        self.event_bus.subscribe(EntitySoldEvent, self.on_entity_sold)
        self.event_bus.subscribe(EntityGrewEvent, self.on_growth)
        self.event_bus.subscribe(EntityDiedEvent, self.on_death)
        self.event_bus.subscribe(EntityTrainedEvent, self.on_trained)
        self.event_bus.subscribe(EntityPunishedEvent, self.on_punished)

    def update(self, world: World, dt: float) -> None:
        """
        Updates floating text entities.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.

        Returns:
            None
        """
        to_destroy = []
        for entity, (transform, text_comp) in world.get_components_tuple(Transform, FloatingText):
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
        # Spawn Floating Text: "+$100" (Gold)
        self.factory.create_floating_text(
            event.position[0],
            event.position[1] - 30,
            f"+${event.value}",
            (255, 215, 0), # Gold
            size=24
        )

        # Emit Log Message
        # We don't have the name here, but we can't get it easily as entity is destroyed.
        # Maybe just say "Sold Yukkuri". Or if EntitySoldEvent contained name...
        # But we can't change event now easily without changing GameManager.
        # For now: "Sold entity for $..."
        self.event_bus.publish(LogMessageEvent(
            message=f"Sold entity for ${event.value}.",
            color=(255, 215, 0)
        ))

    def on_growth(self, event: EntityGrewEvent) -> None:
        """
        Handles EntityGrewEvent.

        Args:
            event (EntityGrewEvent): The event data.

        Returns:
            None
        """
        # Look up name if possible
        name = "Entity"
        stats = self.world.get_component(event.entity_id, YukkuriStats)
        if stats:
            name = stats.name

        self.factory.create_floating_text(
            event.position[0],
            event.position[1] - 40,
            "Level Up!",
            (255, 255, 0), # Yellow
            size=24
        )

        self.event_bus.publish(LogMessageEvent(
            message=f"{name} grew into a {event.new_stage}!",
            color=(0, 255, 0)
        ))

    def on_death(self, event: EntityDiedEvent) -> None:
        """
        Handles EntityDiedEvent.

        Args:
            event (EntityDiedEvent): The event data.

        Returns:
            None
        """
        name = "Entity"
        # Entity might be dead but still in world (as dead body)
        stats = self.world.get_component(event.entity_id, YukkuriStats)
        if stats:
            name = stats.name

        self.factory.create_floating_text(
            event.position[0],
            event.position[1] - 30,
            "Dead...",
            (128, 128, 128), # Gray
            size=20
        )

        self.event_bus.publish(LogMessageEvent(
            message=f"{name} has died.",
            color=(255, 0, 0)
        ))

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

        self.factory.create_floating_text(
            event.position[0],
            event.position[1] - 30,
            "Trained!",
            (0, 255, 255), # Cyan
            size=20
        )

        self.event_bus.publish(LogMessageEvent(
            message=f"{name} trained successfully.",
            color=(0, 255, 255)
        ))

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

        self.factory.create_floating_text(
            event.position[0],
            event.position[1] - 30,
            "Punished!",
            (255, 0, 0), # Red
            size=20
        )

        self.event_bus.publish(LogMessageEvent(
            message=f"{name} was punished.",
            color=(255, 0, 0)
        ))
