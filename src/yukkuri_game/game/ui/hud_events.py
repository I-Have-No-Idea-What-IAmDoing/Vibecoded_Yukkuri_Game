import pygame
import pygame_gui
from typing import Optional, Callable, Dict, Any, TYPE_CHECKING
from ...engine.event_bus import EventBus
from ..events import (
    PlacementStartedEvent,
    TogglePauseRequest,
    CycleSpeedRequest,
    TrainEntityRequest,
    PunishEntityRequest,
    SellEntityRequest,
    CleanToolRequestedEvent,
    VideoSettingsChangedEvent
)

from ..services import SettingsService
from ...engine.audio import AudioManager

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
    def __init__(self, layout: 'HudLayout', game_manager: 'GameManager', event_bus: EventBus, on_error: Optional[Callable[[str], None]] = None):
        """
        Initializes the HudEvents handler.

        Args:
            layout (HudLayout): The HudLayout component.
            game_manager (GameManager): The GameManager instance.
            event_bus (EventBus): The event bus.
            on_error (Callable[[str], None], optional): Callback for error reporting.
        """
        self.layout = layout
        self.gm = game_manager
        self.event_bus = event_bus
        self.on_error = on_error
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
        # Handle slider events
        if event.type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
             if self.layout.settings_window:
                settings_service = self.gm.world.services.try_get(SettingsService)
                audio_manager = self.gm.world.services.try_get(AudioManager)

                if settings_service and audio_manager:
                    if event.ui_element == self.layout.master_volume_slider:
                         vol = event.value
                         settings_service.set_master_volume(vol)
                         audio_manager.set_master_volume(vol)
                         return True

                    if event.ui_element == self.layout.bgm_volume_slider:
                         vol = event.value
                         settings_service.set_bgm_volume(vol)
                         audio_manager.set_bgm_volume(vol)
                         return True

                    if event.ui_element == self.layout.sfx_volume_slider:
                         vol = event.value
                         settings_service.set_sfx_volume(vol)
                         audio_manager.set_sfx_volume(vol)
                         return True

        # Handle Dropdown events
        if event.type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED:
             if self.layout.settings_window:
                  if event.ui_element == self.layout.resolution_dropdown:
                       # We just store it in temp state in SettingsService until save, or parse immediately?
                       # For now let's update SettingsService immediately but not apply until Save?
                       # Actually, applying resolution usually happens on Save.
                       settings_service = self.gm.world.services.try_get(SettingsService)
                       if settings_service:
                            res_str = event.text
                            try:
                                w, h = map(int, res_str.split('x'))
                                settings_service.set_resolution(w, h)
                            except ValueError:
                                pass
                       return True

        if event.type != pygame_gui.UI_BUTTON_PRESSED:
            return False

        ui_element = event.ui_element

        if ui_element == self.layout.save_btn:
            self.gm.save_game()
            return True

        if ui_element == self.layout.load_btn:
            self.gm.load_game()
            return True

        if ui_element == self.layout.settings_btn:
            settings_service = self.gm.world.services.try_get(SettingsService)
            current_settings = {}
            if settings_service:
                current_settings = {
                    "master_volume": settings_service.master_volume,
                    "bgm_volume": settings_service.bgm_volume,
                    "sfx_volume": settings_service.sfx_volume,
                    "window_width": settings_service.window_width,
                    "window_height": settings_service.window_height,
                    "fullscreen": settings_service.fullscreen
                }
            self.layout.create_settings_window(current_settings)
            return True

        if self.layout.settings_window:
            if ui_element == self.layout.fullscreen_btn:
                settings_service = self.gm.world.services.try_get(SettingsService)
                if settings_service:
                    new_val = not settings_service.fullscreen
                    settings_service.set_fullscreen(new_val)
                    self.layout.fullscreen_btn.set_text("ON" if new_val else "OFF")
                return True

            if ui_element == self.layout.settings_save_btn:
                settings_service = self.gm.world.services.try_get(SettingsService)
                if settings_service:
                    settings_service.save_settings()

                    # Publish event for window changes
                    self.event_bus.publish(VideoSettingsChangedEvent(
                        width=settings_service.window_width,
                        height=settings_service.window_height,
                        fullscreen=settings_service.fullscreen
                    ))

                self.layout.close_settings_window()
                return True

            if ui_element == self.layout.settings_cancel_btn:
                # We might want to revert changes if we were modifying them in real-time but then cancelled
                # But for now, simple close is fine, or we reload from file.
                # To support proper Cancel (revert), we should have stored initial values.
                # Let's reload from file to revert.
                settings_service = self.gm.world.services.try_get(SettingsService)
                audio_manager = self.gm.world.services.try_get(AudioManager)
                if settings_service:
                    settings_service.load_settings()
                    if audio_manager:
                        audio_manager.set_master_volume(settings_service.master_volume)
                        audio_manager.set_bgm_volume(settings_service.bgm_volume)
                        audio_manager.set_sfx_volume(settings_service.sfx_volume)

                self.layout.close_settings_window()
                return True

        if ui_element == self.layout.pause_btn:
            self.event_bus.publish(TogglePauseRequest())
            return True

        if ui_element == self.layout.speed_btn:
            self.event_bus.publish(CycleSpeedRequest())
            return True

        if ui_element == self.layout.clean_btn:
            self.event_bus.publish(CleanToolRequestedEvent())
            return True

        # Dynamic Buy Buttons
        if ui_element in self.layout.buy_buttons:
            data = self.layout.buy_buttons[ui_element]
            type_id = data["type_id"]
            cost = data["cost"]
            category = data["category"]
            name = data["name"]

            if self.gm.money >= cost:
                self.event_bus.publish(PlacementStartedEvent(type_id, cost, category))
            elif self.on_error:
                self.on_error(f"Not enough money to buy {name}! Needed: ${cost}")
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

            if hasattr(self.layout, 'punish_btn') and ui_element == self.layout.punish_btn:
                for entity_id in self.selected_entities:
                    self.event_bus.publish(PunishEntityRequest(entity_id))
                return True

        return False
