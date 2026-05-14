"""
Game Session Manager.

Manages session-level state such as pause toggles, time scaling,
and coordinating save/load requests. It binds handlers to the EventBus
and properly cleans them up to prevent memory leaks.
"""

from typing import TYPE_CHECKING, Callable, Any

from ...engine.event_bus import EventBus
from ...game.events import (
    CycleSpeedRequest,
    GamePausedEvent,
    LoadGameRequest,
    SaveGameRequest,
    TogglePauseRequest,
)

if TYPE_CHECKING:
    from ...scenes.gameplay import GameplayScene


class GameSessionManager:
    """
    Manages the current game session state.

    Attributes:
        scene (GameplayScene): Reference to the owning scene.
        event_bus (EventBus): The active event bus.
        paused (bool): Whether the simulation is currently paused.
        time_scale (float): Multiplier for game time.
        _subscriptions (list[tuple[type, Callable]]): Tracked subscriptions for cleanup.
    """

    def __init__(self, scene: "GameplayScene", event_bus: EventBus) -> None:
        """
        Initializes the session manager.

        Args:
            scene (GameplayScene): The owner scene.
            event_bus (EventBus): The global event bus.
        """
        self.scene = scene
        self.event_bus = event_bus
        self.paused = False
        self.time_scale = 1.0
        self._subscriptions: list[tuple[type[Any], Callable[[Any], None]]] = []

        self._setup_event_handlers()

    def _setup_event_handlers(self) -> None:
        """Sets up bound event handlers."""
        self._subscribe(TogglePauseRequest, self._on_toggle_pause)
        self._subscribe(CycleSpeedRequest, self._on_cycle_speed)
        self._subscribe(SaveGameRequest, self._on_save_request)
        self._subscribe(LoadGameRequest, self._on_load_request)

    def _subscribe(self, event_type: type[Any], handler: Callable[[Any], None]) -> None:
        """Subscribes a handler and tracks it for cleanup."""
        self.event_bus.subscribe(event_type, handler)
        self._subscriptions.append((event_type, handler))

    def cleanup(self) -> None:
        """Unsubscribes all bound handlers to prevent memory leaks."""
        for event_type, handler in self._subscriptions:
            self.event_bus.unsubscribe(event_type, handler)
        self._subscriptions.clear()

    # --- Event Handlers ---

    def _on_toggle_pause(self, event: TogglePauseRequest) -> None:
        """Handles TogglePauseRequest."""
        self.toggle_pause()

    def _on_cycle_speed(self, event: CycleSpeedRequest) -> None:
        """Handles CycleSpeedRequest."""
        self.cycle_speed()

    def _on_save_request(self, event: SaveGameRequest) -> None:
        """Handles SaveGameRequest."""
        if hasattr(self.scene, "save_manager"):
            self.scene.save_manager.save_game(event.filename)

    def _on_load_request(self, event: LoadGameRequest) -> None:
        """Handles LoadGameRequest."""
        if hasattr(self.scene, "save_manager"):
            self.scene.save_manager.load_game(event.filename, camera=self.scene.camera)

    # --- Public API ---

    def toggle_pause(self) -> None:
        """Toggles the pause state and broadcasts the change."""
        self.paused = not self.paused
        self.event_bus.publish(GamePausedEvent(self.paused))

    def cycle_speed(self) -> None:
        """Cycles through game speed multipliers."""
        speeds = [1.0, 2.0, 5.0, 0.5]
        try:
            current_idx = speeds.index(self.time_scale)
            next_idx = (current_idx + 1) % len(speeds)
        except ValueError:
            next_idx = 0

        self.time_scale = speeds[next_idx]
        
        # Update HUD if available
        if (
            self.scene.hud
            and hasattr(self.scene.hud, "layout")
            and self.scene.hud.layout
            and self.scene.hud.layout.speed_btn
        ):
            self.scene.hud.layout.speed_btn.set_text(f"{self.time_scale}x")
