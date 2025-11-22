import pygame
from typing import Optional, Callable, Any, Dict, TYPE_CHECKING
import pygame_gui
from ...engine.ecs import World
from ...engine.event_bus import EventBus
from ..events import EntitySelectedEvent, GamePausedEvent, PlacementStartedEvent, NotificationEvent
from ..components import Selectable, Transform
from ..yukkuri_components import YukkuriStats

# Import new components
from .hud_layout import HudLayout
from .hud_events import HudEvents
from .hud_renderer import HudRenderer

if TYPE_CHECKING:
    from ..game_manager import GameManager
    from ..entity_factory import EntityFactory

class HUD:
    """
    The Heads-Up Display (HUD) system for the game.

    Manages the UI layout, event handling, and rendering of game status and entity information.
    This class acts as a facade, delegating responsibilities to specialized sub-components:
    HudLayout, HudEvents, and HudRenderer.

    Attributes:
        manager (pygame_gui.UIManager): The UI manager instance.
        gm (GameManager): The game manager instance.
        world (World): The ECS World instance.
        factory (EntityFactory): The entity factory.
        width (int): The width of the screen.
        height (int): The height of the screen.
        layout (HudLayout): Manages the arrangement of UI elements.
        events (HudEvents): Manages UI event handling.
        renderer (HudRenderer): Manages the updating of UI element content.
        selected_entity (int): The ID of the currently selected entity.
        show_debug (bool): Whether to show the debug window.
        fps (float): The current frames per second.
        event_bus (EventBus): The event bus.
    """

    def __init__(self, ui_manager: pygame_gui.UIManager, world: World):
        """
        Initializes the HUD.

        Args:
            ui_manager (pygame_gui.UIManager): The pygame_gui UIManager.
            world (World): The ECS World instance.
        """
        self.manager = ui_manager
        self.world = world
        from ..game_manager import GameManager
        from ..entity_factory import EntityFactory
        self.gm = world.services.get(GameManager)
        self.factory = world.services.get(EntityFactory)
        self.event_bus = world.services.get(EventBus)

        self.width = 1280
        self.height = 720

        # Initialize Components
        rm = self.factory.rm
        self.layout = HudLayout(self.manager, self.width, self.height, rm.yukkuri_types, rm.item_types)

        self.events = HudEvents(self.layout, self.gm, self.event_bus, self.show_error)

        self.renderer = HudRenderer(self.layout, self.gm, self.world)

        # State
        self.selected_entities = []
        self.show_debug = False
        self.fps = 0.0

        # Subscribe to events
        self.event_bus.subscribe(EntitySelectedEvent, self.on_entity_selected)
        self.event_bus.subscribe(GamePausedEvent, self.on_game_paused)
        self.event_bus.subscribe(NotificationEvent, self.on_notification)

    def on_notification(self, event: NotificationEvent) -> None:
        """
        Handles notification events.
        """
        if self.layout.notification_log:
            self.layout.notification_log.add_message(event.message, event.color)

    def on_entity_selected(self, event: EntitySelectedEvent) -> None:
        """
        Handles the EntitySelectedEvent.

        Args:
            event (EntitySelectedEvent): The entity selected event.
        """
        self.selected_entities = event.entity_ids
        self.events.set_selected_entities(self.selected_entities)
        self._update_selection_window_layout()

    def on_game_paused(self, event: GamePausedEvent) -> None:
        """
        Handles the GamePausedEvent.

        Args:
            event (GamePausedEvent): The game paused event.
        """
        if self.layout.pause_btn:
             self.layout.pause_btn.set_text("Resume" if event.paused else "Pause")

    def update(self, dt: float) -> None:
        """
        Updates the HUD state.

        Checks for selection changes and delegates rendering updates to HudRenderer.

        Args:
            dt (float): Delta time since last frame.
        """
        self.renderer.fps = self.fps # Sync FPS

        # Selection is now handled via events, so we don't need to poll

        # Render Updates
        self.renderer.update(dt, self.selected_entities, self.show_debug)

    def _update_selection_window_layout(self) -> None:
        """
        Updates the layout of the selection window based on the selected entity type.
        """
        if not self.selected_entities:
            self.layout.close_selection_window()
        elif len(self.selected_entities) == 1:
            entity_id = self.selected_entities[0]
            has_stats = self.world.has_component(entity_id, YukkuriStats)
            self.layout.create_selection_window(has_stats, 1)
        else:
            # Multiple selection
            # Check if all have stats or mixed?
            # For now, just enable bulk actions if possible, or generic window
            # Assuming mixed selection might not have specific actions yet,
            # but if all are yukkuris we can show bulk actions.

            all_yukkuris = all(self.world.has_component(eid, YukkuriStats) for eid in self.selected_entities)
            self.layout.create_selection_window(all_yukkuris, len(self.selected_entities)) # Pass True if we want to show buttons for bulk actions

    def toggle_debug(self) -> None:
        """
        Toggles the visibility of the debug window.
        """
        self.show_debug = not self.show_debug
        if self.show_debug:
            self.layout.create_debug_window()
        else:
            self.layout.close_debug_window()

    def show_error(self, message: str) -> None:
        """
        Displays an error message (currently logged via renderer).

        Args:
            message (str): The error message to display.
        """
        self.renderer.show_error(message)

    def process_event(self, event: pygame.event.Event) -> None:
        """
        Processes UI events.

        Delegates to HudEvents.

        Args:
            event (pygame.event.Event): The Pygame event to process.
        """
        handled = self.events.process_event(event)

        # Check if event processing resulted in state changes we need to react to immediately
        # For example, if sold, we need to clear selection
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if hasattr(self.layout, 'sell_btn') and event.ui_element == self.layout.sell_btn:
                # The event handler called sell, we need to clear selection locally
                self.selected_entities = []
                self.layout.close_selection_window()
                self.events.set_selected_entities([])
