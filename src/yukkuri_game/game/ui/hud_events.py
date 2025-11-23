import pygame
import pygame_gui
from typing import Optional, Callable, Dict, Any, TYPE_CHECKING
from ...engine.event_bus import EventBus
from ...engine.audio import AudioManager
from ..settings_service import SettingsService
from ..events import (
    PlacementStartedEvent,
    TogglePauseRequest,
    CycleSpeedRequest,
    TrainEntityRequest,
    PunishEntityRequest,
    SellEntityRequest,
    CleanToolRequestedEvent,
    ResolutionChangedEvent
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

        self.settings_service: Optional[SettingsService] = None
        if hasattr(self.gm.world.services, 'try_get'):
             self.settings_service = self.gm.world.services.try_get(SettingsService)

        self.audio_manager: Optional[AudioManager] = None
        if hasattr(self.gm.world.services, 'try_get'):
            self.audio_manager = self.gm.world.services.try_get(AudioManager)

    def set_selected_entities(self, entity_ids: list[int]) -> None:
        """
        Sets the IDs of the currently selected entities.

        Args:
            entity_ids (list[int]): The entity IDs.

        Returns:
            None
        """
        self.selected_entities = entity_ids

    def process_event(self, event: pygame.event.Event) -> bool:
        """
        Processes UI events.

        Handles button presses for main HUD controls, selection window actions, and settings.

        Args:
            event (pygame.event.Event): The Pygame event.

        Returns:
            bool: True if an event was handled, False otherwise.
        """
        if event.type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
            return self._handle_slider_event(event)

        if event.type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED:
            # We don't need to do anything immediately on dropdown change,
            # we read the value on save.
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

        if ui_element == self.layout.pause_btn:
            self.event_bus.publish(TogglePauseRequest())
            return True

        if ui_element == self.layout.speed_btn:
            self.event_bus.publish(CycleSpeedRequest())
            return True

        if ui_element == self.layout.settings_btn:
            self._open_settings()
            return True

        if ui_element == self.layout.clean_btn:
            self.event_bus.publish(CleanToolRequestedEvent())
            return True

        # Settings Window Buttons
        if self.layout.settings_window:
            if ui_element == self.layout.settings_controls.get("save_btn"):
                self._save_settings()
                self.layout.close_settings_window()
                return True
            if ui_element == self.layout.settings_controls.get("cancel_btn"):
                # Revert changes if needed, but for now just close as sliders apply realtime?
                # Actually sliders apply realtime for feedback, but we should revert if canceled.
                # To revert, we need to restore original values.
                # Simplest is to just reload from service which hasn't been saved yet.
                self._revert_audio_settings()
                self.layout.close_settings_window()
                return True
            if ui_element == self.layout.settings_controls.get("fullscreen_btn"):
                self._toggle_fullscreen_btn()
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

    def _open_settings(self) -> None:
        """Opens the settings window."""
        if not self.settings_service:
            # Try getting it again if it wasn't available at init
             self.settings_service = self.gm.world.services.try_get(SettingsService)

        if self.settings_service:
            self.layout.create_settings_window(self.settings_service.settings)
        else:
            self.on_error("Settings Service not available.")

    def _handle_slider_event(self, event: pygame.event.Event) -> bool:
        """Handles slider movements for volume control."""
        if not self.layout.settings_window:
            return False

        # Get UI element and normalized value
        ui_element = event.ui_element
        value = event.value / 100.0

        if ui_element == self.layout.settings_controls.get("master_slider"):
            if self.audio_manager:
                self.audio_manager.set_master_volume(value)
            return True

        if ui_element == self.layout.settings_controls.get("bgm_slider"):
            if self.audio_manager:
                self.audio_manager.set_bgm_volume(value)
            return True

        if ui_element == self.layout.settings_controls.get("sfx_slider"):
            if self.audio_manager:
                self.audio_manager.set_sfx_volume(value)
            return True

        return False

    def _toggle_fullscreen_btn(self) -> None:
        """Toggles the fullscreen button state in the settings window."""
        if not self.layout.settings_window:
            return

        current = self.layout.settings_controls.get("fullscreen_value", False)
        new_value = not current
        self.layout.settings_controls["fullscreen_value"] = new_value

        btn = self.layout.settings_controls.get("fullscreen_btn")
        if btn:
            btn.set_text("Fullscreen: ON" if new_value else "Fullscreen: OFF")

    def _save_settings(self) -> None:
        """Saves current settings from UI to disk."""
        if not self.settings_service or not self.layout.settings_window:
            return

        controls = self.layout.settings_controls

        # Audio
        master = controls["master_slider"].get_current_value() / 100.0
        bgm = controls["bgm_slider"].get_current_value() / 100.0
        sfx = controls["sfx_slider"].get_current_value() / 100.0

        self.settings_service.set("audio", "master_volume", master)
        self.settings_service.set("audio", "bgm_volume", bgm)
        self.settings_service.set("audio", "sfx_volume", sfx)

        # Window
        resolution_str = controls["resolution_dropdown"].selected_option
        try:
            width, height = map(int, resolution_str.split('x'))
        except ValueError:
             width, height = 1280, 720

        fullscreen = controls["fullscreen_value"]

        self.settings_service.set("window", "width", width)
        self.settings_service.set("window", "height", height)
        self.settings_service.set("window", "fullscreen", fullscreen)

        self.settings_service.save_settings()

        # Apply Window Settings immediately
        self._apply_window_settings(width, height, fullscreen)

    def _apply_window_settings(self, width: int, height: int, fullscreen: bool) -> None:
        """Applies window settings using pygame.display."""
        flags = pygame.RESIZABLE
        if fullscreen:
            flags |= pygame.FULLSCREEN

        try:
            pygame.display.set_mode((width, height), flags)
            # Notify system of resolution change
            self.event_bus.publish(ResolutionChangedEvent(width, height, fullscreen))
        except pygame.error as e:
            if self.on_error:
                self.on_error(f"Failed to change display mode: {e}")
            else:
                print(f"Failed to change display mode: {e}")

    def _revert_audio_settings(self) -> None:
        """Reverts audio settings to what is stored in SettingsService."""
        if not self.settings_service or not self.audio_manager:
            return

        master = self.settings_service.get("audio", "master_volume")
        bgm = self.settings_service.get("audio", "bgm_volume")
        sfx = self.settings_service.get("audio", "sfx_volume")

        self.audio_manager.set_master_volume(master if master is not None else 1.0)
        self.audio_manager.set_bgm_volume(bgm if bgm is not None else 1.0)
        self.audio_manager.set_sfx_volume(sfx if sfx is not None else 1.0)
