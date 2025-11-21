import pygame
import pygame_gui
from typing import Optional, Callable, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .hud_layout import HudLayout
    from ..game_manager import GameManager

class HudEvents:
    """
    Handles UI events for the HUD, such as button clicks.

    Attributes:
        layout (HudLayout): The layout component containing UI elements.
        gm (GameManager): The GameManager instance for game logic.
        callbacks (Dict[str, Callable]): A dictionary of callback functions for various actions.
        selected_entity (int): The ID of the currently selected entity.
    """
    def __init__(self, layout: 'HudLayout', game_manager: 'GameManager', callbacks: Dict[str, Callable[..., Any]]):
        """
        Initializes the HudEvents handler.

        Args:
            layout: The HudLayout component.
            game_manager: The GameManager instance.
            callbacks: Dictionary of callback functions.
        """
        self.layout = layout
        self.gm = game_manager
        self.callbacks = callbacks
        self.selected_entity = -1

    def set_selected_entity(self, entity_id: int) -> None:
        """
        Sets the ID of the currently selected entity.

        Args:
            entity_id: The entity ID.
        """
        self.selected_entity = entity_id

    def process_event(self, event: pygame.event.Event) -> bool:
        """
        Processes UI events.

        Handles button presses for main HUD controls and selection window actions.

        Args:
            event: The Pygame event.

        Returns:
            bool: True if an event was handled, False otherwise.
        """
        if event.type != pygame_gui.UI_BUTTON_PRESSED:
            return False

        ui_element = event.ui_element

        if ui_element == self.layout.save_btn:
            self.gm.save_game()
            return True

        if ui_element == self.layout.load_btn:
            self.gm.load_game()
            return True

        if ui_element == self.layout.pause_btn:
            if self.callbacks.get('toggle_pause'):
                self.callbacks['toggle_pause']()
            return True

        if ui_element == self.layout.speed_btn:
            if self.callbacks.get('cycle_speed'):
                self.callbacks['cycle_speed']()
            return True

        if ui_element == self.layout.add_reimu_btn:
            if self.gm.money >= 100:
                if self.callbacks.get('start_placement'):
                    self.callbacks['start_placement']("reimu", 100, "yukkuri")
            return True

        if ui_element == self.layout.add_cookie_btn:
            if self.gm.money >= 10:
                if self.callbacks.get('start_placement'):
                    self.callbacks['start_placement']("cookie", 10, "item")
            return True

        if self.layout.selection_window:
            if hasattr(self.layout, 'sell_btn') and ui_element == self.layout.sell_btn:
                self.gm.sell_yukkuri(self.selected_entity)
                # Signal that selection should be cleared or handled by caller,
                # but for now, we can't easily clear it here without callbacks or returning a signal.
                # The original code cleared it locally.
                # We can return a specific signal or handle it via callback.
                # For now let's assume the main HUD loop handles the state update after this.
                return True # Special handling might be needed for clearing selection

            if hasattr(self.layout, 'train_btn') and ui_element == self.layout.train_btn:
                # This logic requires access to World to modify components.
                # Ideally this should be in GameManager or a dedicated system.
                # But since we have the logic here in original code, we need to support it.
                # We can delegate to a callback 'train_entity'.
                if self.callbacks.get('train_entity'):
                    self.callbacks['train_entity'](self.selected_entity)
                return True

        return False
