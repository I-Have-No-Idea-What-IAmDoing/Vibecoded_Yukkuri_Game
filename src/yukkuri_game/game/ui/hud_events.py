import pygame
import pygame_gui
from typing import Optional, Callable, Dict, Any, TYPE_CHECKING
from ...engine.event_bus import EventBus
from ..events import (
    PlacementStartedEvent,
    TogglePauseRequest,
    CycleSpeedRequest,
    TrainEntityRequest,
    SellEntityRequest
)

if TYPE_CHECKING:
    from .hud_layout import HudLayout
    from ..game_manager import GameManager

class HudEvents:
    """
    Handles UI events for the HUD, such as button clicks.

    Attributes:
        layout (HudLayout): The layout component containing UI elements.
        gm (GameManager): The GameManager instance for game logic.
        event_bus (EventBus): The event bus.
        selected_entity (int): The ID of the currently selected entity.
    """
    def __init__(self, layout: 'HudLayout', game_manager: 'GameManager', event_bus: EventBus):
        """
        Initializes the HudEvents handler.

        Args:
            layout (HudLayout): The HudLayout component.
            game_manager (GameManager): The GameManager instance.
            event_bus (EventBus): The event bus.
        """
        self.layout = layout
        self.gm = game_manager
        self.event_bus = event_bus
        self.selected_entities: list[int] = []

    def set_selected_entities(self, entity_ids: list[int]) -> None:
        """
        Sets the IDs of the currently selected entities.

        Args:
            entity_ids (list[int]): The entity IDs.
        """
        self.selected_entities = entity_ids

    def process_event(self, event: pygame.event.Event) -> bool:
        """
        Processes UI events.

        Handles button presses for main HUD controls and selection window actions.

        Args:
            event (pygame.event.Event): The Pygame event.

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
            self.event_bus.publish(TogglePauseRequest())
            return True

        if ui_element == self.layout.speed_btn:
            self.event_bus.publish(CycleSpeedRequest())
            return True

        if ui_element == self.layout.add_reimu_btn:
            if self.gm.money >= 100:
                self.event_bus.publish(PlacementStartedEvent("reimu", 100, "yukkuri"))
            return True

        if ui_element == self.layout.add_cookie_btn:
            if self.gm.money >= 10:
                self.event_bus.publish(PlacementStartedEvent("cookie", 10, "item"))
            return True

        if self.layout.selection_window:
            if hasattr(self.layout, 'sell_btn') and ui_element == self.layout.sell_btn:
                for entity_id in self.selected_entities:
                     self.event_bus.publish(SellEntityRequest(entity_id))
                return True

            if hasattr(self.layout, 'train_btn') and ui_element == self.layout.train_btn:
                for entity_id in self.selected_entities:
                    self.event_bus.publish(TrainEntityRequest(entity_id))
                return True

        return False
