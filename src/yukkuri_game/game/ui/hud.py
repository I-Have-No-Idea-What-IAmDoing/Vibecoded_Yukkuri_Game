import pygame
from typing import Optional, Callable
from ...engine.ecs import World
from ..components import Selectable, YukkuriStats
from .hud_layout import HudLayout
from .hud_events import HudEventHandler
from .windows import SelectionWindow, DebugWindow

class HUD:
    """
    The Heads-Up Display (HUD) system for the game.

    Manages the UI elements such as the top status bar, bottom action bar,
    and selection windows. Uses specialized components for layout and event handling.
    """

    def __init__(self, ui_manager, game_manager, world: World, factory):
        """
        Initializes the HUD.

        Args:
            ui_manager: The pygame_gui UIManager.
            game_manager: The GameManager instance.
            world: The ECS World.
            factory: The EntityFactory instance.
        """
        self.manager = ui_manager
        self.gm = game_manager
        self.world = world
        self.factory = factory
        self.width = 1280 # Could be dynamic, but sticking to original for now
        self.height = 720

        self.fps: float = 0.0

        # Components
        self.layout = HudLayout(self.manager, self.width, self.height)
        self.selection_window = SelectionWindow(self.manager, self.width)
        self.debug_window = DebugWindow(self.manager)

        self.event_handler = HudEventHandler(self.gm, self.layout, self.selection_window)

        # Set up callbacks for event handler
        # These will be set by the main game loop via properties on HUD instance usually
        # But HUD instance properties need to be forwarded to event_handler

        # Since we want to maintain API compatibility, we should expose properties that
        # forward to event_handler or sync them.

        self._toggle_pause_callback: Optional[Callable[[], None]] = None
        self._cycle_speed_callback: Optional[Callable[[], None]] = None
        self._start_placement_callback: Optional[Callable[[str, int, str], None]] = None

        # Set default internal callbacks for logic that was previously inline
        self.event_handler.train_callback = self._on_train
        self.event_handler.sell_callback = self._on_sell

    # Properties to forward callbacks to event handler
    @property
    def toggle_pause_callback(self):
        return self._toggle_pause_callback

    @toggle_pause_callback.setter
    def toggle_pause_callback(self, value):
        self._toggle_pause_callback = value
        self.event_handler.toggle_pause_callback = value

    @property
    def cycle_speed_callback(self):
        return self._cycle_speed_callback

    @cycle_speed_callback.setter
    def cycle_speed_callback(self, value):
        self._cycle_speed_callback = value
        self.event_handler.cycle_speed_callback = value

    @property
    def start_placement_callback(self):
        return self._start_placement_callback

    @start_placement_callback.setter
    def start_placement_callback(self, value):
        self._start_placement_callback = value
        self.event_handler.start_placement_callback = value

    # Compatibility properties
    @property
    def selected_entity(self):
        return self.selection_window.current_entity

    @selected_entity.setter
    def selected_entity(self, value):
        # This is tricky because setting ID doesn't automatically show window in new design
        # But usually this is read-only or set internally.
        # The original code updated selected_entity in update() loop.
        pass

    @property
    def show_debug(self):
        return self.debug_window.visible

    @show_debug.setter
    def show_debug(self, value):
        if value != self.debug_window.visible:
            self.debug_window.toggle()

    def update(self, dt: float) -> None:
        """
        Updates the HUD elements.

        Refreshes labels, checks for selection changes, and updates debug info.

        Args:
            dt: Delta time.
        """
        # Update Top Bar Labels
        self.layout.money_label.set_text(f"Money: ${self.gm.money}")

        minutes = int(self.gm.time_elapsed / 60)
        seconds = int(self.gm.time_elapsed % 60)
        self.layout.time_label.set_text(f"Time: {minutes:02d}:{seconds:02d}")

        # Update Debug Window
        self.debug_window.update(self.gm, len(self.world._entities), self.fps)

        # Check selection
        selected = self.world.get_entities_with(Selectable)
        current_selected = -1
        for ent in selected:
            sel = self.world.get_component(ent, Selectable)
            if sel and sel.selected:
                current_selected = ent
                break

        if current_selected != -1:
            if current_selected != self.selection_window.current_entity:
                 self.selection_window.show(current_selected, self.world)
            else:
                 self.selection_window.update(self.world)
        else:
            if self.selection_window.is_active():
                self.selection_window.hide()

    def toggle_debug(self) -> None:
        """
        Toggles the visibility of the debug window.
        """
        self.debug_window.toggle()

    def show_error(self, message: str) -> None:
        """
        Displays an error message in a popup window.

        Args:
            message: The error message to display.
        """
        self.layout.show_error(message)

    def process_event(self, event: pygame.event.Event) -> None:
        """
        Processes UI events (button clicks).

        Args:
            event: The Pygame event.
        """
        self.event_handler.process_event(event)

    def _on_train(self, entity_id: int):
        """Callback for train button."""
        stats = self.world.get_component(entity_id, YukkuriStats)
        if stats:
            stats.badges += 1
            stats.happiness += 10

    def _on_sell(self, entity_id: int):
        """Callback for sell button."""
        self.gm.sell_yukkuri(entity_id)
