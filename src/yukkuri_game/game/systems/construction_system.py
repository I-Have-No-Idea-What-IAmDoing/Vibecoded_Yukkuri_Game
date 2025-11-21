from typing import Optional, TYPE_CHECKING
from ...engine.ecs import System, World
from ...engine.event_bus import EventBus
from ..events import PlacementRequestedEvent
from ..services import EconomyService

if TYPE_CHECKING:
    from ..entity_factory import EntityFactory

class ConstructionSystem(System):
    """
    System responsible for handling construction (placement) of entities.
    Listens for PlacementRequestedEvent.
    """
    def __init__(self):
        self.world: Optional[World] = None
        self.event_bus: Optional[EventBus] = None
        self.economy_service: Optional[EconomyService] = None
        self.factory: Optional['EntityFactory'] = None

    def update(self, world: World, dt: float) -> None:
        if self.world is None:
            self.world = world
            self.event_bus = world.services.get(EventBus)
            self.economy_service = world.services.get(EconomyService)

            from ..entity_factory import EntityFactory
            self.factory = world.services.get(EntityFactory)

            self.event_bus.subscribe(PlacementRequestedEvent, self.on_placement_requested)

    def on_placement_requested(self, event: PlacementRequestedEvent) -> None:
        """
        Handles the PlacementRequestedEvent.
        Checks funds and creates the entity.
        """
        if self.economy_service and self.factory:
            if self.economy_service.get_money() >= event.cost:
                self.economy_service.remove_money(event.cost)
                if event.entity_type == "yukkuri":
                    self.factory.create_yukkuri(event.type_id, event.x, event.y)
                elif event.entity_type == "item":
                    self.factory.create_item(event.type_id, event.x, event.y)
