"""
Module defining the InputSystem logic.
"""

from typing import TYPE_CHECKING

import pygame

from ..engine.audio import AudioManager
from ..engine.ecs import System, World
from ..engine.event_bus import Event, EventBus
from ..engine.input_manager import InputManager
from .components import Selectable, Transform
from .events import (
    CleanToolRequestedEvent,
    ContextMenuRequestedEvent,
    EntitySelectedEvent,
    PlacementCancelledEvent,
    PlacementRequestedEvent,
    PlacementStartedEvent,
)
from .services import InputService, TimeService
from .yukkuri_components import Poop

if TYPE_CHECKING:
    import pygame_gui

    from .camera import Camera


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
        self.event_bus: EventBus | None = None
        self.input_service: InputService | None = None
        self.input_manager: InputManager | None = None
        self.audio: AudioManager | None = None
        self.ui_manager: pygame_gui.UIManager | None = None

        self.drag_start_pos: tuple[float, float] | None = None
        self.drag_end_pos: tuple[float, float] | None = None
        self.drag_start_screen_pos: tuple[int, int] | None = None

    def set_ui_manager(self, ui_manager: "pygame_gui.UIManager") -> None:
        """
        Sets the UI Manager to check for UI interaction.

        Args:
            ui_manager (pygame_gui.UIManager): The UI manager.
        """
        self.ui_manager = ui_manager

    def _play_sound(self, sound_name: str) -> None:
        """
        Plays a sound effect if the audio manager is available.

        Args:
            sound_name (str): The sound effect name to play.
        """
        if self.audio:
            self.audio.play_sound(sound_name)

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
                event.type_id, event.cost, event.entity_type, event.image_name
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

        # Process camera input (movement, zoom)
        self.camera.process_input(self.input_manager, dt)

        # Check UI Hover
        if self.ui_manager and self.ui_manager.get_hovering_any_element():
            return

        # Check Actions
        is_select_pressed = self.input_manager.is_action_just_pressed("select")
        is_cancel_pressed = self.input_manager.is_action_just_pressed("cancel_action")
        is_select_released = self.input_manager.is_action_just_released("select")

        wx, wy = self.camera.screen_to_world(mx, my, screen_w, screen_h)

        # Update Placement Preview Logic
        if self.input_service and self.input_service.is_placing:
            # Check for Grid Snapping (Control Key) using InputManager
            is_ctrl_pressed = self.input_manager.is_action_pressed("ctrl")

            if is_ctrl_pressed:
                # Snap to grid (32x32)
                grid_size = 32
                wx = round(wx / grid_size) * grid_size
                wy = round(wy / grid_size) * grid_size

            self.input_service.current_placement_pos = (wx, wy)

        self._check_hover(world, wx, wy, mx, my)

        # Handle Left Click (Select / Place / Clean / Start Drag)
        if is_select_pressed:
            if self.input_service and self.input_service.is_placing:
                # Use the potentially snapped position
                place_x, place_y = self.input_service.current_placement_pos
                if self.event_bus:
                    self.event_bus.publish(
                        PlacementRequestedEvent(
                            place_x,
                            place_y,
                            self.input_service.place_type,
                            self.input_service.place_cost,
                            self.input_service.place_entity_type,
                        )
                    )
                self._play_sound("place")

                # Check for Shift Key (Multiple Placement) using InputManager
                is_shift_pressed = self.input_manager.is_action_pressed("shift")

                if not is_shift_pressed:
                    self.input_service.cancel_placement()
                return

            if self.input_service and self.input_service.is_cleaning:
                self._handle_cleaning(world, wx, wy)
                return

            self._play_sound("click")

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

            if self.drag_end_pos:  # Add check to satisfy type checker
                self._handle_selection(
                    world, self.drag_start_pos, self.drag_end_pos, drag_dist
                )

            self.drag_start_pos = None
            self.drag_end_pos = None
            self.drag_start_screen_pos = None
            if self.input_service:
                self.input_service.is_dragging = False

        # Handle Right Click (Cancel or Context Menu)
        if is_cancel_pressed:
            handled = False

            # Cancel Placement
            if self.input_service and self.input_service.is_placing:
                self._play_sound("cancel")
                self.input_service.cancel_placement()
                if self.event_bus:
                    self.event_bus.publish(PlacementCancelledEvent())
                handled = True

            # Cancel Cleaning
            if not handled and self.input_service and self.input_service.is_cleaning:
                self._play_sound("cancel")
                self.input_service.stop_cleaning()
                handled = True

            # Context Menu (if not cancelling something)
            if not handled:
                # Use the hovered entity logic but for context menu
                self._handle_context_menu_request(world, wx, wy, mx, my)

        # Handle Time Speed Controls
        self._handle_time_controls(world)

    def _handle_context_menu_request(
        self, world: World, wx: float, wy: float, mx: int, my: int
    ) -> None:
        """
        Checks for an entity at the right-click position and requests a context menu.
        """
        # Re-use hover logic to find top-most entity
        hover_radius = 32.0
        # Optimization: Use get_components_tuple to iterate efficiently
        components = world.get_components_tuple(Transform, Selectable)

        target_id = -1
        # Reversed to match Z-order (assuming order in list follows creation/render order)
        for entity_id, (trans, selectable) in reversed(list(components)):
            dist = ((trans.x - wx) ** 2 + (trans.y - wy) ** 2) ** 0.5
            if dist < hover_radius:
                target_id = entity_id
                break

        if target_id != -1 and self.event_bus:
            self.event_bus.publish(ContextMenuRequestedEvent(target_id, (mx, my)))

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

        # Optimization: Use get_components_tuple to avoid O(N) get_component calls
        # components is a list of (entity_id, (Transform, Selectable))
        components = world.get_components_tuple(Transform, Selectable)
        clicked_something = False

        is_shift_pressed = (
            self.input_manager.is_action_pressed("shift")
            if self.input_manager
            else False
        )

        current_selection = []
        new_selection = []

        for ent, (trans, selectable) in components:
            if selectable.selected:
                current_selection.append(ent)

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

        # Update selection state
        # We need to iterate all components to update 'selected' status
        for ent, (_, selectable) in components:
            selectable.selected = ent in final_selection

        if self.event_bus:
            self.event_bus.publish(EntitySelectedEvent(tuple(final_selection)))

    def _handle_cleaning(self, world: World, wx: float, wy: float) -> None:
        """
        Handles logic when clicking in cleaning mode.

        Args:
            world (World): The ECS World.
            wx (float): World x-coordinate.
            wy (float): World y-coordinate.
        """
        click_radius = 32.0
        # Optimization: Use get_components_tuple
        components = world.get_components_tuple(Poop, Transform)

        found = False
        for entity, (_, transform) in components:
            dist = ((transform.x - wx) ** 2 + (transform.y - wy) ** 2) ** 0.5
            if dist < click_radius:
                world.destroy_entity(entity)
                found = True

        if found:
            self._play_sound("click")

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
        # Optimization: Use get_components_tuple to iterate efficiently
        components = world.get_components_tuple(Transform, Selectable)

        hovered_id = -1
        # Reversed to match Z-order (assuming order in list follows creation/render order)
        # Note: esper.get_components returns a list, order depends on insertion but usually consistent.
        for entity_id, (trans, selectable) in reversed(components):
            dist = ((trans.x - wx) ** 2 + (trans.y - wy) ** 2) ** 0.5
            if dist < hover_radius:
                hovered_id = entity_id
                break

        if self.input_service:
            self.input_service.hovered_entity_id = hovered_id
            self.input_service.hovered_entity_pos = (mx, my)

    def _handle_time_controls(self, world: World) -> None:
        """
        Handles time speed control inputs.

        Checks for speed up/down actions and modifies the TimeService.game_speed accordingly.

        Args:
            world (World): The ECS World.
        """
        if not self.input_manager:
            return

        # Lazy get TimeService
        time_service = world.services.try_get(TimeService)
        if time_service is None:
            return

        # Prevent conflict with Zoom (Ctrl + +/-)
        if self.input_manager.is_action_pressed("ctrl"):
            return

        # Speed Up (+)
        if self.input_manager.is_action_just_pressed("time_speed_up"):
            new_speed = min(5.0, time_service.game_speed * 2.0)
            time_service.game_speed = new_speed

        # Speed Down (-)
        if self.input_manager.is_action_just_pressed("time_speed_down"):
            new_speed = max(0.5, time_service.game_speed / 2.0)
            time_service.game_speed = new_speed
