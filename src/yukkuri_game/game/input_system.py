"""
Module defining the InputSystem logic.
"""

import pygame
from typing import Optional, TYPE_CHECKING, Tuple
from ..engine.ecs import System, World
from ..engine.event_bus import EventBus, Event
from ..engine.audio import AudioManager
from ..engine.input_manager import InputManager
from .events import (
    PlacementStartedEvent,
    EntitySelectedEvent,
    PlacementRequestedEvent,
    PlacementCancelledEvent,
    CleanToolRequestedEvent,
)
from .components import Transform, Selectable
from .yukkuri_components import Poop
from .services import InputService

if TYPE_CHECKING:
    from .camera import Camera
    import pygame_gui


class InputSystem(System):
    """
    System responsible for handling user input related to the game world.

    Handles entity selection and triggers placement requests via events.

    Attributes:
        camera (Camera): The world view manager.
        event_bus (Optional[EventBus]): The event bus service.
        input_service (Optional[InputService]): The input service.
        input_manager (Optional[InputManager]): The input manager service.
        audio (Optional[AudioManager]): The audio manager.
        ui_manager (Optional[pygame_gui.UIManager]): The UI manager.
        drag_start_pos (Optional[Tuple[float, float]]): World coordinates where drag started.
        drag_end_pos (Optional[Tuple[float, float]]): World coordinates where drag ended.
        drag_start_screen_pos (Optional[Tuple[int, int]]): Screen coordinates where drag started.
    """

    def __init__(self, camera: "Camera"):
        """
        Initializes the InputSystem.

        Args:
            camera (Camera): The game world view manager.
        """
        self.camera = camera
        self.event_bus: Optional[EventBus] = None
        self.input_service: Optional[InputService] = None
        self.input_manager: Optional[InputManager] = None
        self.audio: Optional[AudioManager] = None
        self.ui_manager: Optional["pygame_gui.UIManager"] = None

        self.drag_start_pos: Optional[Tuple[float, float]] = None
        self.drag_end_pos: Optional[Tuple[float, float]] = None
        self.drag_start_screen_pos: Optional[Tuple[int, int]] = None

    def set_ui_manager(self, ui_manager: "pygame_gui.UIManager") -> None:
        """
        Sets the UI Manager to check for UI interaction.

        Args:
            ui_manager (pygame_gui.UIManager): The UI manager.
        """
        self.ui_manager = ui_manager

    def on_placement_started(self, event: Event) -> None:
        """
        Handles the PlacementStartedEvent.

        Args:
            event (Event): The event instance.
        """
        if not isinstance(event, PlacementStartedEvent):
            return

        if self.input_service:
            self.input_service.start_placement(
                event.type_id, event.cost, event.entity_type
            )

    def on_clean_tool_requested(self, event: Event) -> None:
        """
        Handles the CleanToolRequestedEvent.

        Args:
            event (Event): The event instance.
        """
        if not isinstance(event, CleanToolRequestedEvent):
            return

        if self.input_service:
            self.input_service.start_cleaning()

    def update(self, world: World, dt: float) -> None:
        """
        Updates the input system by polling InputManager.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.
        """
        # Lazy initialization of dependencies
        if self.input_service is None:
            self.input_service = world.services.get(InputService)
        if self.input_manager is None:
            self.input_manager = world.services.try_get(InputManager)
        if self.event_bus is None:
            self.event_bus = world.services.get(EventBus)
            self.event_bus.subscribe(PlacementStartedEvent, self.on_placement_started)
            self.event_bus.subscribe(
                CleanToolRequestedEvent, self.on_clean_tool_requested
            )
        if self.audio is None:
            self.audio = world.services.try_get(AudioManager)

        if not self.input_manager:
            return

        # Poll InputManager
        mx, my = self.input_manager.get_mouse_position()

        surface = pygame.display.get_surface()
        if not surface:
            return
        screen_w, screen_h = surface.get_size()

        # Check UI Hover
        if self.ui_manager and self.ui_manager.get_hovering_any_element():
            return

        # Check Actions
        is_select_pressed = self.input_manager.is_action_just_pressed("select")
        is_cancel_pressed = self.input_manager.is_action_just_pressed("cancel_action")
        is_select_released = self.input_manager.is_action_just_released("select")

        wx, wy = self.camera.screen_to_world(mx, my, screen_w, screen_h)

        self._check_hover(world, wx, wy, mx, my)

        # Handle Left Click (Select / Place / Clean / Start Drag)
        if is_select_pressed:
            if self.input_service and self.input_service.is_placing:
                if self.event_bus:
                    self.event_bus.publish(
                        PlacementRequestedEvent(
                            wx,
                            wy,
                            self.input_service.place_type,
                            self.input_service.place_cost,
                            self.input_service.place_entity_type,
                        )
                    )
                if self.audio:
                    self.audio.play_sound("place")
                self.input_service.cancel_placement()
                return

            if self.input_service and self.input_service.is_cleaning:
                self._handle_cleaning(world, wx, wy)
                return

            if self.audio:
                self.audio.play_sound("click")

            self.drag_start_pos = (wx, wy)
            self.drag_end_pos = (wx, wy)
            self.drag_start_screen_pos = (mx, my)
            if self.input_service:
                self.input_service.is_dragging = True
                self.input_service.drag_start_pos = (mx, my)
                self.input_service.drag_current_pos = (mx, my)

        # Handle Dragging Update
        if self.input_service and self.input_service.is_dragging:
            self.drag_end_pos = (wx, wy)
            self.input_service.drag_current_pos = (mx, my)

        # Handle Left Release (End Drag / Selection)
        if is_select_released and self.drag_start_pos:
            self.drag_end_pos = (wx, wy)

            drag_dist = 0.0
            if self.drag_start_screen_pos:
                dx = mx - self.drag_start_screen_pos[0]
                dy = my - self.drag_start_screen_pos[1]
                drag_dist = (dx * dx + dy * dy) ** 0.5

            self._handle_selection(
                world, self.drag_start_pos, self.drag_end_pos, drag_dist
            )

            self.drag_start_pos = None
            self.drag_end_pos = None
            self.drag_start_screen_pos = None
            if self.input_service:
                self.input_service.is_dragging = False

        # Handle Right Click (Cancel)
        if is_cancel_pressed:
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

    def _handle_selection(
        self,
        world: World,
        start_pos: tuple[float, float],
        end_pos: tuple[float, float],
        drag_dist: float,
    ) -> None:
        """
        Handles selecting entities within the given world coordinate box.

        Args:
            world (World): The ECS World.
            start_pos (tuple[float, float]): The drag start position (world coords).
            end_pos (tuple[float, float]): The drag end position (world coords).
            drag_dist (float): The distance dragged in screen pixels.
        """
        x1, y1 = start_pos
        x2, y2 = end_pos
        min_x, max_x = min(x1, x2), max(x1, x2)
        min_y, max_y = min(y1, y2), max(y1, y2)

        is_click = drag_dist < 5.0
        click_radius = 32.0

        entities = world.get_entities_with(Transform, Selectable)
        clicked_something = False

        is_shift_pressed = pygame.key.get_pressed()[pygame.K_LSHIFT]

        current_selection = []
        for ent in entities:
            selectable = world.get_component(ent, Selectable)
            if selectable and selectable.selected:
                current_selection.append(ent)

        new_selection = []

        for ent in entities:
            trans = world.get_component(ent, Transform)
            if trans is None:
                continue

            selectable = world.get_component(ent, Selectable)
            if not selectable:
                continue

            in_selection = False
            if is_click:
                dist = ((trans.x - x1) ** 2 + (trans.y - y1) ** 2) ** 0.5
                if dist < click_radius:
                    in_selection = True
                    clicked_something = True
            else:
                if min_x <= trans.x <= max_x and min_y <= trans.y <= max_y:
                    in_selection = True
                    clicked_something = True

            if in_selection:
                new_selection.append(ent)

        final_selection = []
        if is_shift_pressed:
            final_selection = list(set(current_selection) | set(new_selection))
            if is_click and len(new_selection) == 1:
                ent = new_selection[0]
                if ent in current_selection:
                    final_selection.remove(ent)
        else:
            if clicked_something:
                final_selection = new_selection
            else:
                final_selection = []

        for ent in entities:
            selectable = world.get_component(ent, Selectable)
            if selectable:
                selectable.selected = ent in final_selection

        if self.event_bus:
            self.event_bus.publish(EntitySelectedEvent(final_selection))

    def _handle_cleaning(self, world: World, wx: float, wy: float) -> None:
        """
        Handles logic when clicking in cleaning mode.

        Args:
            world (World): The ECS World.
            wx (float): World x-coordinate.
            wy (float): World y-coordinate.
        """
        click_radius = 32.0
        poop_entities = world.get_entities_with(Poop, Transform)

        found = False
        for entity in poop_entities:
            transform = world.get_component(entity, Transform)
            if transform is None:
                continue
            dist = ((transform.x - wx) ** 2 + (transform.y - wy) ** 2) ** 0.5
            if dist < click_radius:
                world.destroy_entity(entity)
                found = True

        if found:
            if self.audio:
                self.audio.play_sound("click")

    def _check_hover(
        self, world: World, wx: float, wy: float, mx: int, my: int
    ) -> None:
        """
        Checks for entities under the mouse cursor and updates the input service.

        Args:
            world (World): The ECS World.
            wx (float): World x-coordinate.
            wy (float): World y-coordinate.
            mx (int): Screen x-coordinate.
            my (int): Screen y-coordinate.
        """
        hover_radius = 32.0
        entities = world.get_entities_with(Transform, Selectable)
        entity_list = list(entities)

        hovered_id = -1
        for ent in reversed(entity_list):
            if isinstance(ent, tuple):
                entity_id = ent[0]
            else:
                entity_id = ent

            trans = world.get_component(entity_id, Transform)
            if trans is None:
                continue

            dist = ((trans.x - wx) ** 2 + (trans.y - wy) ** 2) ** 0.5
            if dist < hover_radius:
                hovered_id = entity_id
                break

        if self.input_service:
            self.input_service.hovered_entity_id = hovered_id
            self.input_service.hovered_entity_pos = (mx, my)
