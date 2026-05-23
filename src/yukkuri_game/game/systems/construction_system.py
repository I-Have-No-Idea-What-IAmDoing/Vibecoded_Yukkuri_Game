"""
Module defining the ConstructionSystem logic.
"""

from typing import TYPE_CHECKING
from ...engine.ecs import System, World
from ...engine.event_bus import EventBus, Event
from ..events import PlacementRequestedEvent
from ..services import EconomyService

if TYPE_CHECKING:
    from ..entity_factory import EntityFactory


class ConstructionSystem(System):
    """
    System responsible for handling construction (placement) of entities.
    Listens for PlacementRequestedEvent.

    Attributes:
        world (Optional[World]): The ECS World instance.
        event_bus (Optional[EventBus]): The event bus.
        economy_service (Optional[EconomyService]): The economy service.
        factory (Optional[EntityFactory]): The entity factory.
    """

    def __init__(self) -> None:
        """Initializes the ConstructionSystem."""
        self.world: World | None = None
        self.event_bus: EventBus | None = None
        self.economy_service: EconomyService | None = None
        self.factory: EntityFactory | None = None

    def update(self, world: World, dt: float) -> None:
        """
        Updates the system.

        Lazily initializes dependencies and subscribes to events.

        Args:
            world (World): The ECS World instance.
            dt (float): The time elapsed since the last update.

        Returns:
            None
        """
        if self.world is None:
            self.world = world
            self.event_bus = world.services.get(EventBus)
            self.economy_service = world.services.get(EconomyService)

            from ..entity_factory import EntityFactory

            self.factory = world.services.get(EntityFactory)

            self.event_bus.subscribe(
                PlacementRequestedEvent, self.on_placement_requested
            )

    def on_placement_requested(self, event: Event) -> None:
        """
        Handles the PlacementRequestedEvent.
        Checks funds and creates the entity.

        Args:
            event (PlacementRequestedEvent): The event data.

        Returns:
            None
        """
        if not isinstance(event, PlacementRequestedEvent):
            return

        if self.economy_service and self.factory:
            if self.economy_service.money >= event.cost:
                try:
                    if event.entity_type == "yukkuri":
                        self.factory.create_yukkuri(event.type_id, event.x, event.y)
                    elif event.entity_type == "item":
                        self.factory.create_item(event.type_id, event.x, event.y)

                    self.economy_service.remove_money(event.cost)
                    if self.event_bus:
                        from ..events import LogMessageEvent

                        self.event_bus.publish(
                            LogMessageEvent(
                                message=(
                                    f"Bought {event.type_id.capitalize()} "
                                    f"for ${event.cost}."
                                ),
                                color=(255, 100, 100),
                                channel="Economy",
                            )
                        )
                except Exception:
                    # Propagate to EventBus (which should log it)
                    # Money is NOT removed since remove_money is after creation
                    raise
