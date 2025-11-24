"""
Module defining the InputSystem logic.
"""
import pygame
from typing import Optional, TYPE_CHECKING, List, Tuple
from ..engine.ecs import System, World
from ..engine.event_bus import EventBus
from ..engine.audio import AudioManager
from .events import PlacementStartedEvent, EntitySelectedEvent, PlacementRequestedEvent, PlacementCancelledEvent, CleanToolRequestedEvent
from .components import Transform, Selectable
from .yukkuri_components import Poop
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
        event_bus (Optional[EventBus]): The event bus for publishing and subscribing to events.
        input_service (Optional[InputService]): The service managing input state.
        audio (Optional[AudioManager]): The audio manager.
        drag_start_pos (Optional[tuple[float, float]]): World coordinates where dragging started.
        drag_end_pos (Optional[tuple[float, float]]): World coordinates where dragging currently is.
        drag_start_screen_pos (Optional[tuple[int, int]]): Screen coordinates where dragging started.
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
        self.audio: Optional[AudioManager] = None
        self.drag_start_pos: Optional[Tuple[float, float]] = None
        self.drag_end_pos: Optional[Tuple[float, float]] = None
        self.drag_start_screen_pos: Optional[Tuple[int, int]] = None

    def on_placement_started(self, event: PlacementStartedEvent) -> None:
        """
        Handles the PlacementStartedEvent.

        Args:
            event (PlacementStartedEvent): The placement started event.

        Returns:
            None
        """
        if self.input_service:
            self.input_service.start_placement(event.type_id, event.cost, event.entity_type)

    def on_clean_tool_requested(self, event: CleanToolRequestedEvent) -> None:
        """
        Handles the CleanToolRequestedEvent.

        Args:
            event (CleanToolRequestedEvent): The clean tool requested event.

        Returns:
            None
        """
        if self.input_service:
            self.input_service.start_cleaning()

    def update(self, world: World, dt: float) -> None:
        """
        Updates the input system.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.

        Returns:
            None
        """
        # Lazy initialization of dependencies
        if self.input_service is None:
            self.input_service = world.services.get(InputService)
        if self.event_bus is None:
            self.event_bus = world.services.get(EventBus)
            self.event_bus.subscribe(PlacementStartedEvent, self.on_placement_started)
            self.event_bus.subscribe(CleanToolRequestedEvent, self.on_clean_tool_requested)
        if self.audio is None:
            self.audio = world.services.try_get(AudioManager)

        # Handle hover detection once per frame if possible
        # We need current mouse pos for this.
        if pygame.display.get_init() and pygame.display.get_surface():
             mx, my = pygame.mouse.get_pos()
             screen_w, screen_h = pygame.display.get_surface().get_size()
             wx, wy = self.yukkurrium.screen_to_world(mx, my, screen_w, screen_h)
             self._check_hover(world, wx, wy, mx, my)

    def handle_event(self, event: pygame.event.Event, world: World, screen_w: int, screen_h: int, ui_manager: Optional['pygame_gui.UIManager'] = None) -> None:
        """
        Handles a single Pygame event.

        Args:
            event (pygame.event.Event): The Pygame event.
            world (World): The ECS World.
            screen_w (int): The width of the screen.
            screen_h (int): The height of the screen.
            ui_manager (Optional[pygame_gui.UIManager]): The UI manager (optional) to check for UI interaction.

        Returns:
            None
        """
        self.yukkurrium.handle_input(event, screen_w, screen_h)

        # Retrieve mouse position from event if possible, or fall back to get_pos but be safe for headless/tests
        if hasattr(event, "pos"):
            mx, my = event.pos
        else:
             if pygame.display.get_init():
                 mx, my = pygame.mouse.get_pos()
             else:
                 mx, my = (0, 0)

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
                    if self.audio:
                        self.audio.play_sound("place")
                    self.input_service.cancel_placement()
                    return

                if self.input_service and self.input_service.is_cleaning:
                    self._handle_cleaning(world, wx, wy)
                    return

                if self.audio:
                    self.audio.play_sound("click")

                # Start dragging
                self.drag_start_pos = (wx, wy)
                self.drag_end_pos = (wx, wy)
                self.drag_start_screen_pos = (mx, my)
                if self.input_service:
                    self.input_service.is_dragging = True
                    self.input_service.drag_start_pos = (mx, my)
                    self.input_service.drag_current_pos = (mx, my)

            elif event.button == 3: # Right Click cancels placement/cleaning
                if self.input_service and self.input_service.is_placing:
                    if self.audio:
                        self.audio.play_sound("cancel")
                    self.input_service.cancel_placement()
                    if self.event_bus:
                        self.event_bus.publish(PlacementCancelledEvent())

                if self.input_service and self.input_service.is_cleaning:
                    if self.audio:
                        self.audio.play_sound("cancel")
                    self.input_service.stop_cleaning()

        elif event.type == pygame.MOUSEMOTION:
            if self.drag_start_pos:
                self.drag_end_pos = (wx, wy)
                if self.input_service and self.input_service.is_dragging:
                    self.input_service.drag_current_pos = (mx, my)

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
                    self.input_service.is_dragging = False

    def _handle_selection(self, world: World, start_pos: tuple[float, float], end_pos: tuple[float, float], drag_dist: float) -> None:
        """
        Handles selecting entities within the given world coordinate box.

        Args:
            world: The ECS World.
            start_pos: World coordinates of drag start.
            end_pos: World coordinates of drag end.
            drag_dist: Drag distance in screen pixels.

        Returns:
            None
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

    def _handle_cleaning(self, world: World, wx: float, wy: float) -> None:
        """
        Handles logic when clicking in cleaning mode.

        Args:
            world: The ECS World.
            wx (float): World x-coordinate.
            wy (float): World y-coordinate.

        Returns:
            None
        """
        click_radius = 32.0
        # Find Poop entities near click
        # Optimization: Spatial query if available, else iterate Poop entities
        poop_entities = world.get_entities_with(Poop, Transform)

        found = False
        for entity in poop_entities:
            transform = world.get_component(entity, Transform)
            dist = ((transform.x - wx)**2 + (transform.y - wy)**2)**0.5
            if dist < click_radius:
                # Clean it
                world.destroy_entity(entity)
                found = True
                # We can clean multiple if stacked, or just one. Let's clean all in radius.

        if found:
            if self.audio:
                self.audio.play_sound("click") # Or a cleaning sound if available
        else:
             # If nothing found, maybe stop cleaning? Or just allow clicking around.
             # Let's keep cleaning mode active until right click or button press.
             pass

    def _check_hover(self, world: World, wx: float, wy: float, mx: int, my: int) -> None:
        """
        Checks for entities under the mouse cursor and updates the input service.

        Args:
            world: The ECS World.
            wx (float): World x-coordinate.
            wy (float): World y-coordinate.
            mx (int): Mouse x-coordinate.
            my (int): Mouse y-coordinate.

        Returns:
            None
        """
        hover_radius = 32.0
        # esper.get_components returns a list of (entity_id, component1, component2, ...)
        # Note: get_entities_with is not a standard esper method, usually it's get_components
        # Assuming get_entities_with returns just IDs is risky if it's actually a wrapper or esper's get_components.
        # If this method exists on World (ECS), check its signature.
        # Standard esper: world.get_components(Transform, Selectable) -> [(ent, trans, sel), ...]

        # If get_entities_with returns just IDs:
        # entities = world.get_entities_with(Transform, Selectable)

        # Let's assume standard usage pattern or check usage elsewhere.
        # Usage elsewhere: entities = world.get_entities_with(Transform, Selectable)
        # for ent in entities: ...
        # It seems get_entities_with might return a list of entity IDs if implemented customly,
        # or tuples if it's get_components.

        # To be safe and robust, let's use get_components if available or handle the tuple.
        # Since other methods use get_entities_with, I'll assume it's available.
        # If it returns tuples (ent, trans, sel), iterating 'ent' would be the tuple.

        # Let's check how other methods use it.
        # _handle_selection uses:
        # entities = world.get_entities_with(Transform, Selectable)
        # for ent in entities:
        #    selectable = world.get_component(ent, Selectable)

        # This implies 'ent' is an entity ID.
        # If get_entities_with returns tuples, world.get_component((id, ...), ...) would fail.

        # However, if get_entities_with returns a list of IDs, reversed(entities) is fine.
        # If it returns a generator, reversed() fails.

        entities = world.get_entities_with(Transform, Selectable)
        # Convert to list to ensure we can reverse it (in case it's a generator)
        entity_list = list(entities)

        hovered_id = -1
        # Reverse iterate to find the top-most entity (if rendered back-to-front)
        for ent in reversed(entity_list):
            # If ent is a tuple (common in esper for multiple components), extract ID
            if isinstance(ent, tuple):
                entity_id = ent[0]
                # Optimization: we already have components in the tuple if it's standard esper
                # trans = ent[1]
            else:
                entity_id = ent

            trans = world.get_component(entity_id, Transform)

            dist = ((trans.x - wx)**2 + (trans.y - wy)**2)**0.5
            if dist < hover_radius:
                hovered_id = entity_id
                break

        self.input_service.hovered_entity_id = hovered_id
        self.input_service.hovered_entity_pos = (mx, my)
