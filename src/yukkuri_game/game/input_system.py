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
            yukkurrium (Yukkurrium): The Yukkurrium instance.
        """
        self.yukkurrium = yukkurrium
        self.event_bus: Optional[EventBus] = None
        self.input_service: Optional[InputService] = None
        self.drag_start_pos: Optional[tuple[float, float]] = None
        self.drag_end_pos: Optional[tuple[float, float]] = None
        self.drag_start_screen_pos: Optional[tuple[int, int]] = None

    def on_placement_started(self, event: PlacementStartedEvent) -> None:
        """
        Handles the PlacementStartedEvent.

        Args:
            event (PlacementStartedEvent): The placement started event.
        """
        if self.input_service:
            self.input_service.start_placement(event.type_id, event.cost, event.entity_type)

    def update(self, world: World, dt: float) -> None:
        """
        Updates the input system.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.
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
            event (pygame.event.Event): The Pygame event.
            world (World): The ECS World.
            screen_w (int): The width of the screen.
            screen_h (int): The height of the screen.
            ui_manager (Optional[pygame_gui.UIManager]): The UI manager (optional) to check for UI interaction.
        """
        self.yukkurrium.handle_input(event, screen_w, screen_h)

        mx, my = pygame.mouse.get_pos()
        wx, wy = self.yukkurrium.screen_to_world(mx, my, screen_w, screen_h)

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # Left Click
                # Check if UI is handling the event
                if ui_manager and ui_manager.get_hovering_any_element():
                    return

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

                # Start dragging
                self.drag_start_pos = (wx, wy)
                self.drag_end_pos = (wx, wy)
                self.drag_start_screen_pos = (mx, my)
                if self.input_service:
                    self.input_service.selection_rect = pygame.Rect(mx, my, 0, 0) # Use screen coords for rect

            elif event.button == 3: # Right Click cancels placement
                if self.input_service and self.input_service.is_placing:
                    self.input_service.cancel_placement()
                    if self.event_bus:
                        self.event_bus.publish(PlacementCancelledEvent())

        elif event.type == pygame.MOUSEMOTION:
            if self.drag_start_pos:
                self.drag_end_pos = (wx, wy)
                if self.input_service:
                    # Calculate screen rect for rendering
                    sx_start, sy_start = self.yukkurrium.world_to_screen(self.drag_start_pos[0], self.drag_start_pos[1], screen_w, screen_h)
                    self.input_service.selection_rect = pygame.Rect(
                        min(sx_start, mx), min(sy_start, my),
                        abs(sx_start - mx), abs(sy_start - my)
                    )

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1 and self.drag_start_pos:
                self.drag_end_pos = (wx, wy)

                # Calculate drag distance in screen pixels
                drag_dist = 0.0
                if self.drag_start_screen_pos:
                    dx = mx - self.drag_start_screen_pos[0]
                    dy = my - self.drag_start_screen_pos[1]
                    drag_dist = (dx*dx + dy*dy)**0.5

                self._handle_selection(world, self.drag_start_pos, self.drag_end_pos, drag_dist)
                self.drag_start_pos = None
                self.drag_end_pos = None
                self.drag_start_screen_pos = None
                if self.input_service:
                    self.input_service.selection_rect = None

    def _handle_selection(self, world: World, start_pos: tuple[float, float], end_pos: tuple[float, float], drag_dist: float) -> None:
        """
        Handles selecting entities within the given world coordinate box.

        Args:
            world: The ECS World.
            start_pos: World coordinates of drag start.
            end_pos: World coordinates of drag end.
            drag_dist: Drag distance in screen pixels.
        """
        x1, y1 = start_pos
        x2, y2 = end_pos
        min_x, max_x = min(x1, x2), max(x1, x2)
        min_y, max_y = min(y1, y2), max(y1, y2)

        # Use screen pixel distance to distinguish click vs drag
        is_click = drag_dist < 5.0
        click_radius = 32.0

        entities = world.get_entities_with(Transform, Selectable)
        selected_ids = []
        clicked_something = False

        # Handle Shift key for multi-select
        is_shift_pressed = pygame.key.get_pressed()[pygame.K_LSHIFT]

        # If not appending, clear previous selection first (unless we click nothing, handled later)
        if not is_shift_pressed:
            # We will clear non-selected entities in the loop or after
            pass

        current_selection = []
        for ent in entities:
            selectable = world.get_component(ent, Selectable)
            if selectable and selectable.selected:
                current_selection.append(ent)

        new_selection = []

        for ent in entities:
            trans = world.get_component(ent, Transform)
            if not trans:
                continue

            selectable = world.get_component(ent, Selectable)
            if not selectable:
                continue

            in_selection = False
            if is_click:
                 dist = ((trans.x - x1)**2 + (trans.y - y1)**2)**0.5
                 if dist < click_radius:
                     in_selection = True
                     clicked_something = True
            else:
                if min_x <= trans.x <= max_x and min_y <= trans.y <= max_y:
                    in_selection = True
                    clicked_something = True

            if in_selection:
                new_selection.append(ent)

        # Update selection state
        final_selection = []
        if is_shift_pressed:
            # Toggle logic or additive? Standard is usually additive or toggle.
            # Let's go with additive for drag, toggle for click?
            # Requirements say "Update the event to support a list of IDs"
            # Let's simplify: Shift adds/keeps existing.
            # If click/drag covers new entities, add them.

            # Actually, standard RTS behavior:
            # Click on unselected: Select only that one.
            # Shift+Click on unselected: Add to selection.
            # Shift+Click on selected: Remove from selection (toggle).
            # Drag: Select all in box.
            # Shift+Drag: Add all in box to selection.

            final_selection = list(set(current_selection) | set(new_selection))

            # If single click toggle logic desired:
            if is_click and len(new_selection) == 1:
                ent = new_selection[0]
                if ent in current_selection:
                    final_selection.remove(ent)

        else:
            if clicked_something:
                final_selection = new_selection
            else:
                # Clicked/Dragged empty space -> deselect all
                final_selection = []

        # Apply to components
        for ent in entities:
            selectable = world.get_component(ent, Selectable)
            if selectable:
                selectable.selected = (ent in final_selection)

        if self.event_bus:
            self.event_bus.publish(EntitySelectedEvent(final_selection))
