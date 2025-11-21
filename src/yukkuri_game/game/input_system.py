import pygame
from typing import Optional, TYPE_CHECKING
from ..engine.ecs import System, World
from ..engine.event_bus import EventBus
from .events import PlacementStartedEvent, EntitySelectedEvent, PlacementRequestedEvent, PlacementCancelledEvent
from .components import Transform, Selectable
from .services import InputService

if TYPE_CHECKING:
    from .yukkurrium import Yukkurrium
    import pygame_gui

class InputSystem(System):
    """
    System responsible for handling user input related to the game world.

    Handles entity selection and triggers placement requests via events.

    Attributes:
        yukkurrium (Yukkurrium): The game world view manager.
        event_bus (EventBus): The event bus for publishing and subscribing to events.
        input_service (InputService): The service managing input state.
    """

    def __init__(self, yukkurrium: 'Yukkurrium'):
        """
        Initializes the InputSystem.

        Args:
            yukkurrium: The Yukkurrium instance.
        """
        self.yukkurrium = yukkurrium
        self.event_bus: Optional[EventBus] = None
        self.input_service: Optional[InputService] = None

    def on_placement_started(self, event: PlacementStartedEvent) -> None:
        """
        Handles the PlacementStartedEvent.
        """
        if self.input_service:
            self.input_service.start_placement(event.type_id, event.cost, event.entity_type)

    def update(self, world: World, dt: float) -> None:
        """
        Updates the input system.

        Args:
            world: The ECS World.
            dt: Delta time.
        """
        # Lazy initialization of dependencies
        if self.input_service is None:
            self.input_service = world.services.get(InputService)
        if self.event_bus is None:
            self.event_bus = world.services.get(EventBus)
            self.event_bus.subscribe(PlacementStartedEvent, self.on_placement_started)

    def handle_event(self, event: pygame.event.Event, world: World, screen_w: int, screen_h: int, ui_manager: Optional['pygame_gui.UIManager'] = None) -> None:
        """
        Handles a single Pygame event.

        Args:
            event: The Pygame event.
            world: The ECS World.
            screen_w: The width of the screen.
            screen_h: The height of the screen.
            ui_manager: The UI manager (optional) to check for UI interaction.
        """
        self.yukkurrium.handle_input(event, screen_w, screen_h)

        if event.type == pygame.MOUSEBUTTONDOWN:
            # Check if UI is handling the event
            if ui_manager and ui_manager.get_hovering_any_element():
                return

            if event.button == 1: # Left Click
                mx, my = event.pos
                wx, wy = self.yukkurrium.screen_to_world(mx, my, screen_w, screen_h)

                if self.input_service and self.input_service.is_placing:
                    if self.event_bus:
                        self.event_bus.publish(PlacementRequestedEvent(
                            wx, wy,
                            self.input_service.place_type,
                            self.input_service.place_cost,
                            self.input_service.place_entity_type
                        ))
                    self.input_service.cancel_placement()
                    return

                # Check clicks on entities
                self._handle_selection(world, wx, wy)

            elif event.button == 3: # Right Click cancels placement
                if self.input_service and self.input_service.is_placing:
                    self.input_service.cancel_placement()
                    if self.event_bus:
                        self.event_bus.publish(PlacementCancelledEvent())

    def _handle_selection(self, world: World, wx: float, wy: float) -> None:
        """
        Handles selecting entities at the given world coordinates.
        """
        entities = world.get_entities_with(Transform, Selectable)
        clicked_something = False
        selected_entity = -1

        for ent in entities:
            trans = world.get_component(ent, Transform)
            if not trans:
                continue
            # Assume 32px radius roughly
            dist = ((trans.x - wx)**2 + (trans.y - wy)**2)**0.5

            selectable = world.get_component(ent, Selectable)
            if not selectable:
                continue

            if dist < 32:
                selectable.selected = True
                clicked_something = True
                selected_entity = ent
            else:
                if not pygame.key.get_pressed()[pygame.K_LSHIFT]: # Shift adds to selection
                    selectable.selected = False

        if clicked_something:
            if self.event_bus:
                self.event_bus.publish(EntitySelectedEvent(selected_entity))
        else:
            # Deselect all if clicked ground
            for ent in entities:
                selectable = world.get_component(ent, Selectable)
                if selectable:
                    selectable.selected = False
            if self.event_bus:
                self.event_bus.publish(EntitySelectedEvent(-1))
