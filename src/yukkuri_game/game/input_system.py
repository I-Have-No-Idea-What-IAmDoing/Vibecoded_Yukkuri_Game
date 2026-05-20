"""
Module defining the InputSystem logic.
"""

from typing import TYPE_CHECKING

import pygame

from ..engine.ecs import System, World
from ..engine.event_bus import Event, EventBus
from ..engine.input_manager import InputManager
from .commands import (
    CameraAxisCommand,
    CameraPanCommand,
    CameraZoomAxisCommand,
    CameraZoomCommand,
    CancelCleaningCommand,
    CancelPlacementCommand,
    CleanEntityCommand,
    ContextMenuCommand,
    PlaceItemCommand,
    SelectEntitiesCommand,
    TimeSpeedCommand,
)
from yukkuri_game.engine.components import Selectable, Transform
from .events import (
    CleanToolRequestedEvent,
    PlacementStartedEvent,
)
from .services import InputBufferService, InputService

if TYPE_CHECKING:
    import pygame_gui

    from yukkuri_game.engine.camera import Camera


from yukkuri_game.game.systems.command_processor_system import CommandProcessorSystem


class InputSystem(System):
    run_before = [CommandProcessorSystem]

    """
    System responsible for translating raw hardware input into GameCommands.

    This system no longer executes any game logic itself.  It reads the
    InputManager state each frame, produces the appropriate GameCommand
    objects, and enqueues them in the InputBufferService.  All actual
    world mutations happen inside CommandProcessorSystem.

    Attributes:
        camera (Camera): The world view manager (used for coordinate conversion).
        event_bus (EventBus | None): The event bus service.
        input_service (InputService | None): The input mode service.
        input_manager (InputManager | None): The raw input manager.
        buffer (InputBufferService | None): The command buffer service.
        ui_manager (pygame_gui.UIManager | None): The UI manager.
        drag_start_pos (tuple[float, float] | None): World drag-start position.
        drag_end_pos (tuple[float, float] | None): World drag-end position.
        drag_start_screen_pos (tuple[int, int] | None): Screen drag-start position.
        _prev_move_axis (tuple[float, float]): Previously emitted movement axis.
        _prev_zoom_axis (float): Previously emitted zoom axis.
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
        self.buffer: InputBufferService | None = None
        self.ui_manager: "pygame_gui.UIManager | None" = None

        self.drag_start_pos: tuple[float, float] | None = None
        self.drag_end_pos: tuple[float, float] | None = None
        self.drag_start_screen_pos: tuple[int, int] | None = None

        # Track previously emitted axis values to avoid flooding the buffer
        self._prev_move_axis: tuple[float, float] = (0.0, 0.0)
        self._prev_zoom_axis: float = 0.0

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

    def _emit(self, command: object) -> None:
        """
        Enqueues a command into the InputBufferService.

        Args:
            command: Any object satisfying the GameCommand protocol.
        """
        if self.buffer:
            self.buffer.add_command(command)

    def _emit_camera_axis(self, x: float, y: float) -> None:
        """
        Emits a CameraAxisCommand only when the axis value changes.

        Args:
            x: Horizontal axis value in [-1, 1].
            y: Vertical axis value in [-1, 1].
        """
        if (x, y) != self._prev_move_axis:
            self._emit(CameraAxisCommand(x, y))
            self._prev_move_axis = (x, y)

    def _emit_zoom_axis(self, z: float) -> None:
        """
        Emits a CameraZoomAxisCommand only when the zoom axis changes.

        Args:
            z: Zoom axis value in [-1, 1].
        """
        if z != self._prev_zoom_axis:
            self._emit(CameraZoomAxisCommand(z))
            self._prev_zoom_axis = z

    def update(self, world: World, dt: float) -> None:
        """
        Translates InputManager state into GameCommands each frame.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.
        """
        # Lazy initialization of dependencies
        if self.input_service is None:
            self.input_service = world.services.get(InputService)
        if self.input_manager is None:
            self.input_manager = world.services.try_get(InputManager)
        if self.buffer is None:
            self.buffer = world.services.try_get(InputBufferService)
        if self.event_bus is None:
            self.event_bus = world.services.get(EventBus)
            self.event_bus.subscribe(PlacementStartedEvent, self.on_placement_started)
            self.event_bus.subscribe(
                CleanToolRequestedEvent, self.on_clean_tool_requested
            )

        if not self.input_manager:
            return

        # Poll mouse position
        mx, my = self.input_manager.get_mouse_position()

        surface = pygame.display.get_surface()
        if not surface:
            return
        screen_w, screen_h = surface.get_size()

        # --- Camera movement axis ---
        x_axis = 0.0
        y_axis = 0.0
        if self.input_manager.is_action_pressed("right"):
            x_axis += 1.0
        if self.input_manager.is_action_pressed("left"):
            x_axis -= 1.0
        if self.input_manager.is_action_pressed("down"):
            y_axis += 1.0
        if self.input_manager.is_action_pressed("up"):
            y_axis -= 1.0
        self._emit_camera_axis(x_axis, y_axis)

        # --- Camera zoom axis (keyboard Ctrl + +/-) ---
        zoom_axis = 0.0
        if self.input_manager.is_action_pressed("ctrl"):
            if self.input_manager.is_action_pressed("time_speed_up"):
                zoom_axis = 1.0
            elif self.input_manager.is_action_pressed("time_speed_down"):
                zoom_axis = -1.0
        self._emit_zoom_axis(zoom_axis)

        # --- Mouse wheel discrete zoom ---
        wheel = self.input_manager.get_mouse_wheel()
        if wheel != 0.0:
            self._emit(CameraZoomCommand(wheel * 0.1))

        # --- Middle-mouse pan ---
        if self.input_manager.is_action_pressed("pan"):
            dx, dy = self.input_manager.get_mouse_rel()
            if dx != 0 or dy != 0:
                self._emit(CameraPanCommand(dx, dy))

        # Check UI Hover — suppress gameplay input when UI is hovered
        if self.ui_manager and self.ui_manager.get_hovering_any_element():
            return

        # --- Per-frame action queries ---
        is_select_pressed = self.input_manager.is_action_just_pressed("select")
        is_cancel_pressed = self.input_manager.is_action_just_pressed("cancel_action")
        is_select_released = self.input_manager.is_action_just_released("select")

        wx, wy = self.camera.screen_to_world(mx, my, screen_w, screen_h)

        # --- Placement preview position update ---
        if self.input_service and self.input_service.is_placing:
            is_ctrl_pressed = self.input_manager.is_action_pressed("ctrl")
            if is_ctrl_pressed:
                grid_size = 32
                wx = round(wx / grid_size) * grid_size
                wy = round(wy / grid_size) * grid_size
            self.input_service.current_placement_pos = (wx, wy)

        self._check_hover(world, wx, wy, mx, my)

        # --- Left click: Place / Clean / Start drag ---
        if is_select_pressed:
            if self.input_service and self.input_service.is_placing:
                place_x, place_y = self.input_service.current_placement_pos
                self._emit(
                    PlaceItemCommand(
                        place_x,
                        place_y,
                        self.input_service.place_type,
                        self.input_service.place_cost,
                        self.input_service.place_entity_type,
                    )
                )
                is_shift_pressed = self.input_manager.is_action_pressed("shift")
                if not is_shift_pressed:
                    self.input_service.cancel_placement()
                return

            if self.input_service and self.input_service.is_cleaning:
                self._emit(CleanEntityCommand(wx, wy))
                return

            self.drag_start_pos = (wx, wy)
            self.drag_end_pos = (wx, wy)
            self.drag_start_screen_pos = (mx, my)
            if self.input_service:
                self.input_service.is_dragging = True
                self.input_service.drag_start_pos = (mx, my)
                self.input_service.drag_current_pos = (mx, my)

        # --- Drag update ---
        if self.input_service and self.input_service.is_dragging:
            self.drag_end_pos = (wx, wy)
            self.input_service.drag_current_pos = (mx, my)

        # --- Left release: resolve selection ---
        if is_select_released and self.drag_start_pos:
            self.drag_end_pos = (wx, wy)

            drag_dist = 0.0
            if self.drag_start_screen_pos:
                ddx = mx - self.drag_start_screen_pos[0]
                ddy = my - self.drag_start_screen_pos[1]
                drag_dist = (ddx * ddx + ddy * ddy) ** 0.5

            end = self.drag_end_pos or (wx, wy)
            is_shift = (
                self.input_manager.is_action_pressed("shift")
                if self.input_manager
                else False
            )
            self._emit(
                SelectEntitiesCommand(
                    self.drag_start_pos, end, drag_dist, is_shift
                )
            )

            self.drag_start_pos = None
            self.drag_end_pos = None
            self.drag_start_screen_pos = None
            if self.input_service:
                self.input_service.is_dragging = False

        # --- Right click: Cancel or Context Menu ---
        if is_cancel_pressed:
            if self.input_service and self.input_service.is_placing:
                self._emit(CancelPlacementCommand())
            elif self.input_service and self.input_service.is_cleaning:
                self._emit(CancelCleaningCommand())
            else:
                self._emit(ContextMenuCommand(wx, wy, mx, my))

        # --- Time speed controls ---
        self._handle_time_controls()

    def _check_hover(
        self, world: World, wx: float, wy: float, mx: int, my: int
    ) -> None:
        """
        Checks for entities under the mouse cursor and updates InputService.

        Args:
            world (World): The ECS World.
            wx (float): World x-coordinate.
            wy (float): World y-coordinate.
            mx (int): Screen x-coordinate.
            my (int): Screen y-coordinate.
        """
        hover_radius = 32.0
        components = world.get_components_tuple(Transform, Selectable)

        hovered_id = -1
        for entity_id, (trans, _) in reversed(components):
            dist = ((trans.x - wx) ** 2 + (trans.y - wy) ** 2) ** 0.5
            if dist < hover_radius:
                hovered_id = entity_id
                break

        if self.input_service:
            self.input_service.hovered_entity_id = hovered_id
            self.input_service.hovered_entity_pos = (mx, my)

    def _handle_time_controls(self) -> None:
        """
        Emits TimeSpeedCommands based on time speed key presses.

        Skips if the Ctrl key is held (to avoid conflict with zoom).
        """
        if not self.input_manager:
            return

        # Prevent conflict with Ctrl+zoom
        if self.input_manager.is_action_pressed("ctrl"):
            return

        if self.input_manager.is_action_just_pressed("time_speed_up"):
            # Read current speed from the service directly so we can compute
            # the next value; the command only accepts the final value.
            if self.buffer:
                from yukkuri_game.engine.services.time_service import TimeService as _TS

                ts = self.ecs_world.services.try_get(_TS)
                if ts:
                    new_speed = min(5.0, ts.game_speed * 2.0)
                    self._emit(TimeSpeedCommand(new_speed))

        if self.input_manager.is_action_just_pressed("time_speed_down"):
            if self.buffer:
                from yukkuri_game.engine.services.time_service import TimeService as _TS

                ts = self.ecs_world.services.try_get(_TS)
                if ts:
                    new_speed = max(0.5, ts.game_speed / 2.0)
                    self._emit(TimeSpeedCommand(new_speed))
