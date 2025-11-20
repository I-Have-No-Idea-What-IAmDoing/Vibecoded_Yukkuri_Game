import pygame
import pygame_gui
from typing import Optional, Callable

class HudEventHandler:
    """
    Handles UI events (mostly button clicks) for the HUD.
    """

    def __init__(self, game_manager, hud_layout, selection_window):
        """
        Args:
            game_manager: The GameManager instance.
            hud_layout: The HudLayout instance (to access buttons).
            selection_window: The SelectionWindow instance (to access its buttons).
        """
        self.gm = game_manager
        self.layout = hud_layout
        self.selection_window = selection_window

        self.toggle_pause_callback: Optional[Callable[[], None]] = None
        self.cycle_speed_callback: Optional[Callable[[], None]] = None
        self.start_placement_callback: Optional[Callable[[str, int, str], None]] = None
        self.sell_callback: Optional[Callable[[int], None]] = None
        self.train_callback: Optional[Callable[[int], None]] = None

    def process_event(self, event: pygame.event.Event) -> bool:
        """
        Processes a pygame event. Returns True if the event was handled.
        """
        if event.type != pygame_gui.UI_BUTTON_PRESSED:
            return False

        ui_element = event.ui_element

        # Top Bar
        if ui_element == self.layout.save_btn:
            self.gm.save_game()
            return True
        elif ui_element == self.layout.load_btn:
            self.gm.load_game()
            return True
        elif ui_element == self.layout.pause_btn:
            if self.toggle_pause_callback:
                self.toggle_pause_callback()
            return True
        elif ui_element == self.layout.speed_btn:
            if self.cycle_speed_callback:
                self.cycle_speed_callback()
            return True

        # Bottom Bar
        elif ui_element == self.layout.add_reimu_btn:
            if self.gm.money >= 100:
                if self.start_placement_callback:
                    self.start_placement_callback("reimu", 100, "yukkuri")
            return True
        elif ui_element == self.layout.add_cookie_btn:
            if self.gm.money >= 10:
                if self.start_placement_callback:
                    self.start_placement_callback("cookie", 10, "item")
            return True

        # Selection Window
        elif self.selection_window.is_active():
            if ui_element == self.selection_window.sell_btn:
                entity_id = self.selection_window.current_entity
                if self.sell_callback:
                    self.sell_callback(entity_id)
                else:
                    # Fallback to direct GM call if no callback provided, but HUD usually did this directly
                    self.gm.sell_yukkuri(entity_id)

                self.selection_window.hide()
                return True
            elif ui_element == self.selection_window.train_btn:
                entity_id = self.selection_window.current_entity
                if self.train_callback:
                    self.train_callback(entity_id)
                return True

        return False
