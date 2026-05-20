"""
Game Commands Module.

Defines the GameCommand protocol and all concrete command types that
the InputSystem can enqueue into the InputBufferService.

Commands encapsulate a single user intent (e.g. place an item, zoom the
camera) and expose an ``execute`` method that carries out that intent
against the ECS World when called by CommandProcessorSystem.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from ..engine.ecs import World



@runtime_checkable
class GameCommand(Protocol):
    """Protocol for all buffered game commands."""

    def execute(self, world: "World") -> None:
        """
        Execute this command against the ECS world.

        Args:
            world: The active ECS World instance.
        """
        ...


# ---------------------------------------------------------------------------
# Camera commands
# ---------------------------------------------------------------------------


class CameraAxisCommand:
    """
    Updates the camera's movement axis state.

    Emitted when directional keys are pressed or released.  The Camera
    stores this state and uses it in its own update loop so that
    interpolation-friendly, dt-scaled movement continues without
    flooding the buffer every frame.

    Attributes:
        x_axis: Horizontal axis value in [-1, 1].
        y_axis: Vertical axis value in [-1, 1].
    """

    def __init__(self, x_axis: float, y_axis: float) -> None:
        """
        Initialises the command.

        Args:
            x_axis: Horizontal axis value in [-1, 1].
            y_axis: Vertical axis value in [-1, 1].
        """
        self.x_axis = x_axis
        self.y_axis = y_axis

    def execute(self, world: "World") -> None:
        """
        Applies the axis state to the Camera service.

        Args:
            world: The active ECS World instance.
        """
        from yukkuri_game.engine.camera import Camera

        camera = world.services.try_get(Camera)
        if camera:
            camera.set_axis(self.x_axis, self.y_axis)


class CameraZoomAxisCommand:
    """
    Updates the camera's keyboard-zoom axis state.

    Attributes:
        zoom_axis: Zoom axis value in [-1, 1].
    """

    def __init__(self, zoom_axis: float) -> None:
        """
        Initialises the command.

        Args:
            zoom_axis: Zoom axis value in [-1, 1].
        """
        self.zoom_axis = zoom_axis

    def execute(self, world: "World") -> None:
        """
        Applies the zoom axis state to the Camera service.

        Args:
            world: The active ECS World instance.
        """
        from yukkuri_game.engine.camera import Camera

        camera = world.services.try_get(Camera)
        if camera:
            camera.set_zoom_axis(self.zoom_axis)


class CameraZoomCommand:
    """
    Adds a discrete delta to the camera's target zoom level.

    Used for mouse-wheel scroll events where each tick produces an
    instantaneous zoom delta rather than a continuous axis.

    Attributes:
        zoom_delta: The amount to add to the camera's target zoom.
    """

    def __init__(self, zoom_delta: float) -> None:
        """
        Initialises the command.

        Args:
            zoom_delta: Amount to add to camera target zoom.
        """
        self.zoom_delta = zoom_delta

    def execute(self, world: "World") -> None:
        """
        Applies the zoom delta to the Camera service.

        Args:
            world: The active ECS World instance.
        """
        from yukkuri_game.engine.camera import Camera

        camera = world.services.try_get(Camera)
        if camera:
            camera.add_zoom(self.zoom_delta)


class CameraPanCommand:
    """
    Pans the camera by a screen-pixel delta.

    Emitted each frame that the middle mouse button is held, using the
    accumulated mouse-movement delta from InputManager.

    Attributes:
        dx: Horizontal pixel delta.
        dy: Vertical pixel delta.
    """

    def __init__(self, dx: int, dy: int) -> None:
        """
        Initialises the command.

        Args:
            dx: Horizontal pixel delta.
            dy: Vertical pixel delta.
        """
        self.dx = dx
        self.dy = dy

    def execute(self, world: "World") -> None:
        """
        Applies the pixel pan to the Camera service.

        Args:
            world: The active ECS World instance.
        """
        from yukkuri_game.engine.camera import Camera

        camera = world.services.try_get(Camera)
        if camera:
            camera.pan(self.dx, self.dy)


# ---------------------------------------------------------------------------
# Placement commands
# ---------------------------------------------------------------------------


class PlaceItemCommand:
    """
    Requests the placement of an entity at a world position.

    Attributes:
        x: World x-coordinate.
        y: World y-coordinate.
        place_type: Type-ID string of the entity to place.
        cost: Gold cost of the placement.
        entity_type: Category string (``"yukkuri"`` or ``"item"``).
    """

    def __init__(
        self,
        x: float,
        y: float,
        place_type: str,
        cost: int,
        entity_type: str,
    ) -> None:
        """
        Initialises the command.

        Args:
            x: World x-coordinate.
            y: World y-coordinate.
            place_type: Type-ID string of the entity to place.
            cost: Gold cost of the placement.
            entity_type: Category string (``"yukkuri"`` or ``"item"``).
        """
        self.x = x
        self.y = y
        self.place_type = place_type
        self.cost = cost
        self.entity_type = entity_type

    def execute(self, world: "World") -> None:
        """
        Publishes a PlacementRequestedEvent on the EventBus.

        Args:
            world: The active ECS World instance.
        """
        from ..engine.event_bus import EventBus
        from yukkuri_game.engine.protocols import IAudioProvider
        from .events import PlacementRequestedEvent

        event_bus = world.services.try_get(EventBus)
        if event_bus:
            event_bus.publish(
                PlacementRequestedEvent(
                    self.x,
                    self.y,
                    self.place_type,
                    self.cost,
                    self.entity_type,
                )
            )
        audio = world.services.try_get(IAudioProvider)
        if audio:
            audio.play_sound("place")


class CancelPlacementCommand:
    """Cancels the active placement mode."""

    def execute(self, world: "World") -> None:
        """
        Cancels placement mode and publishes a PlacementCancelledEvent.

        Args:
            world: The active ECS World instance.
        """
        from ..engine.event_bus import EventBus
        from yukkuri_game.engine.protocols import IAudioProvider
        from .events import PlacementCancelledEvent
        from .services import InputService

        input_service = world.services.try_get(InputService)
        if input_service:
            input_service.cancel_placement()

        event_bus = world.services.try_get(EventBus)
        if event_bus:
            event_bus.publish(PlacementCancelledEvent())

        audio = world.services.try_get(IAudioProvider)
        if audio:
            audio.play_sound("cancel")


class CancelCleaningCommand:
    """Cancels the active cleaning mode."""

    def execute(self, world: "World") -> None:
        """
        Cancels cleaning mode.

        Args:
            world: The active ECS World instance.
        """
        from yukkuri_game.engine.protocols import IAudioProvider
        from .services import InputService

        input_service = world.services.try_get(InputService)
        if input_service:
            input_service.stop_cleaning()

        audio = world.services.try_get(IAudioProvider)
        if audio:
            audio.play_sound("cancel")


# ---------------------------------------------------------------------------
# Selection commands
# ---------------------------------------------------------------------------


class SelectEntitiesCommand:
    """
    Resolves entity selection from a drag/click operation.

    Attributes:
        start_pos: World coordinate where the drag began.
        end_pos: World coordinate where the drag ended.
        drag_dist: Screen-pixel distance of the drag gesture.
        is_shift_pressed: Whether the shift modifier was held.
    """

    def __init__(
        self,
        start_pos: tuple[float, float],
        end_pos: tuple[float, float],
        drag_dist: float,
        is_shift_pressed: bool,
    ) -> None:
        """
        Initialises the command.

        Args:
            start_pos: World coordinate where the drag began.
            end_pos: World coordinate where the drag ended.
            drag_dist: Screen-pixel distance of the drag gesture.
            is_shift_pressed: Whether the shift modifier was held.
        """
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.drag_dist = drag_dist
        self.is_shift_pressed = is_shift_pressed

    def execute(self, world: "World") -> None:
        """
        Evaluates selection and publishes an EntitySelectedEvent.

        Args:
            world: The active ECS World instance.
        """
        from ..engine.event_bus import EventBus
        from yukkuri_game.engine.protocols import IAudioProvider
        from yukkuri_game.engine.components import Transform
        from yukkuri_game.engine.components import Selectable
        from .events import EntitySelectedEvent

        x1, y1 = self.start_pos
        x2, y2 = self.end_pos
        min_x, max_x = min(x1, x2), max(x1, x2)
        min_y, max_y = min(y1, y2), max(y1, y2)

        is_click = self.drag_dist < 5.0
        click_radius = 32.0

        components = world.get_components_tuple(Transform, Selectable)
        clicked_something = False

        current_selection: list[int] = []
        new_selection: list[int] = []

        for ent, (trans, selectable) in components:
            if selectable.selected:
                current_selection.append(ent)

            in_selection = False
            if is_click:
                dist = math.hypot(trans.x - x1, trans.y - y1)
                if dist < click_radius:
                    in_selection = True
                    clicked_something = True
            else:
                if min_x <= trans.x <= max_x and min_y <= trans.y <= max_y:
                    in_selection = True
                    clicked_something = True

            if in_selection:
                new_selection.append(ent)

        final_selection: list[int] = []
        if self.is_shift_pressed:
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

        for ent, (_, selectable) in components:
            selectable.selected = ent in final_selection

        audio = world.services.try_get(IAudioProvider)
        if is_click and audio:
            audio.play_sound("click")

        event_bus = world.services.try_get(EventBus)
        if event_bus:
            event_bus.publish(EntitySelectedEvent(tuple(final_selection)))


# ---------------------------------------------------------------------------
# Cleaning commands
# ---------------------------------------------------------------------------


class CleanEntityCommand:
    """
    Destroys poop entities near the given world position.

    Attributes:
        wx: World x-coordinate of the click.
        wy: World y-coordinate of the click.
    """

    def __init__(self, wx: float, wy: float) -> None:
        """
        Initialises the command.

        Args:
            wx: World x-coordinate.
            wy: World y-coordinate.
        """
        self.wx = wx
        self.wy = wy

    def execute(self, world: "World") -> None:
        """
        Destroys poop entities within click radius.

        Args:
            world: The active ECS World instance.
        """
        from yukkuri_game.engine.protocols import IAudioProvider
        from .components import Poop
        from yukkuri_game.engine.components import Transform

        click_radius = 32.0
        components = world.get_components_tuple(Poop, Transform)

        found = False
        for entity, (_, transform) in components:
            dist = math.hypot(transform.x - self.wx, transform.y - self.wy)
            if dist < click_radius:
                world.destroy_entity(entity)
                found = True

        if found:
            audio = world.services.try_get(IAudioProvider)
            if audio:
                audio.play_sound("click")


# ---------------------------------------------------------------------------
# Context menu command
# ---------------------------------------------------------------------------


class ContextMenuCommand:
    """
    Requests a context menu for the entity at the given position.

    Attributes:
        wx: World x-coordinate of the click.
        wy: World y-coordinate of the click.
        mx: Screen x-coordinate of the click.
        my: Screen y-coordinate of the click.
    """

    def __init__(
        self, wx: float, wy: float, mx: int, my: int
    ) -> None:
        """
        Initialises the command.

        Args:
            wx: World x-coordinate.
            wy: World y-coordinate.
            mx: Screen x-coordinate.
            my: Screen y-coordinate.
        """
        self.wx = wx
        self.wy = wy
        self.mx = mx
        self.my = my

    def execute(self, world: "World") -> None:
        """
        Finds the top-most entity at the position and publishes a
        ContextMenuRequestedEvent.

        Args:
            world: The active ECS World instance.
        """
        from ..engine.event_bus import EventBus
        from yukkuri_game.engine.components import Transform, Selectable
        from .events import ContextMenuRequestedEvent

        hover_radius = 32.0
        components = world.get_components_tuple(Transform, Selectable)

        target_id = -1
        for entity_id, (trans, _) in reversed(list(components)):
            dist = math.hypot(trans.x - self.wx, trans.y - self.wy)
            if dist < hover_radius:
                target_id = entity_id
                break

        if target_id != -1:
            event_bus = world.services.try_get(EventBus)
            if event_bus:
                event_bus.publish(
                    ContextMenuRequestedEvent(target_id, (self.mx, self.my))
                )


# ---------------------------------------------------------------------------
# Time commands
# ---------------------------------------------------------------------------


class TimeSpeedCommand:
    """
    Sets the game speed to a specific multiplier.

    Attributes:
        speed_multiplier: The new game speed value.
    """

    def __init__(self, speed_multiplier: float) -> None:
        """
        Initialises the command.

        Args:
            speed_multiplier: The new game speed multiplier.
        """
        self.speed_multiplier = speed_multiplier

    def execute(self, world: "World") -> None:
        """
        Updates game speed via TimeService.

        Args:
            world: The active ECS World instance.
        """
        from yukkuri_game.engine.services.time_service import TimeService

        time_service = world.services.try_get(TimeService)
        if time_service:
            time_service.game_speed = self.speed_multiplier
