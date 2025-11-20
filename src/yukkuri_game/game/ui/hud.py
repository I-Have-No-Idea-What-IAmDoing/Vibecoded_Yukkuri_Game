import pygame
from typing import Optional, Callable
import pygame_gui
from ...engine.ecs import World
from ..components import Selectable, Transform
from ..yukkuri_components import YukkuriStats

# Import new components
from .hud_layout import HudLayout
from .hud_events import HudEvents
from .hud_renderer import HudRenderer

class HUD:
    """
    The Heads-Up Display (HUD) system for the game.

    Refactored to use specialized components for Layout, Events, and Rendering.
    """

    def __init__(self, ui_manager, game_manager, world: World, factory):
        self.manager = ui_manager
        self.gm = game_manager
        self.world = world
        self.factory = factory

        self.width = 1280
        self.height = 720

        # Callbacks
        self.toggle_pause_callback: Optional[Callable[[], None]] = None
        self.cycle_speed_callback: Optional[Callable[[], None]] = None
        self.start_placement_callback: Optional[Callable[[str, int, str], None]] = None

        # Initialize Components
        self.layout = HudLayout(self.manager, self.width, self.height)

        # Events component needs callbacks, which are set later.
        # We can pass a lambda or method that resolves them dynamically,
        # or update the events component when callbacks are set.
        # For now, we pass a dict that we can update.
        self._callbacks_store = {}
        self.events = HudEvents(self.layout, self.gm, self._callbacks_store)

        self.renderer = HudRenderer(self.layout, self.gm, self.world)

        # State
        self.selected_entity = -1
        self.show_debug = False
        self.fps = 0.0

    # Delegate property access for backward compatibility/convenience
    @property
    def money_label(self): return self.layout.money_label
    @property
    def time_label(self): return self.layout.time_label
    @property
    def save_btn(self): return self.layout.save_btn
    @property
    def load_btn(self): return self.layout.load_btn
    @property
    def pause_btn(self): return self.layout.pause_btn
    @property
    def speed_btn(self): return self.layout.speed_btn
    @property
    def add_reimu_btn(self): return self.layout.add_reimu_btn
    @property
    def add_cookie_btn(self): return self.layout.add_cookie_btn
    @property
    def selection_window(self): return self.layout.selection_window
    @property
    def debug_window(self): return self.layout.debug_window

    def update(self, dt: float) -> None:
        self.renderer.fps = self.fps # Sync FPS

        # Check selection logic
        current_selected = self._get_current_selected_entity()

        if current_selected != self.selected_entity:
            self.selected_entity = current_selected
            self.events.set_selected_entity(self.selected_entity)
            self._update_selection_window_layout()

        # Update Layout if needed (e.g. if selection changed, we already did it)

        # Render Updates
        self.renderer.update(dt, self.selected_entity, self.show_debug)

    def _get_current_selected_entity(self) -> int:
        selected = self.world.get_entities_with(Selectable)
        for ent in selected:
            sel = self.world.get_component(ent, Selectable)
            if sel and sel.selected:
                return ent
        return -1

    def _update_selection_window_layout(self):
        if self.selected_entity == -1:
            self.layout.close_selection_window()
        else:
            has_stats = self.world.has_component(self.selected_entity, YukkuriStats)
            self.layout.create_selection_window(has_stats)

    def toggle_debug(self) -> None:
        self.show_debug = not self.show_debug
        if self.show_debug:
            self.layout.create_debug_window()
        else:
            self.layout.close_debug_window()

    def show_error(self, message: str) -> None:
        self.renderer.show_error(message)

    def process_event(self, event: pygame.event.Event) -> None:
        # Update callbacks dict before processing (in case they were set after init)
        self._callbacks_store['toggle_pause'] = self.toggle_pause_callback
        self._callbacks_store['cycle_speed'] = self.cycle_speed_callback
        self._callbacks_store['start_placement'] = self.start_placement_callback

        # Add a special callback for training which was inline before
        self._callbacks_store['train_entity'] = self._train_entity

        handled = self.events.process_event(event)

        # Check if event processing resulted in state changes we need to react to immediately
        # For example, if sold, we need to clear selection
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if hasattr(self.layout, 'sell_btn') and event.ui_element == self.layout.sell_btn:
                # The event handler called sell, we need to clear selection locally
                self.selected_entity = -1
                self.layout.close_selection_window()
                self.events.set_selected_entity(-1)

    def _train_entity(self, entity_id: int):
        stats = self.world.get_component(entity_id, YukkuriStats)
        if stats:
            stats.badges += 1
            stats.happiness += 10
