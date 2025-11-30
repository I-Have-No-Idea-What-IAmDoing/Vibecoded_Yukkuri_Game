"""
Module for handling UI events from the HUD.
"""
import pygame
import pygame_gui
from typing import Optional, Callable, Dict, Any, TYPE_CHECKING
from loguru import logger
from ...engine.event_bus import EventBus
from ...engine.audio import AudioManager
from ..settings_service import SettingsService
from ..services import EconomyService, PersistenceService
from ...engine.ecs import World
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

class HudEvents:
    """
    Handles UI events for the HUD, such as button clicks.

    Attributes:
        layout (HudLayout): The layout component containing UI elements.
        world (World): The ECS World instance.
        event_bus (EventBus): The event bus.
        selected_entities (list[int]): The IDs of the currently selected entities.
        settings_service (Optional[SettingsService]): The settings service.
        audio_manager (Optional[AudioManager]): The audio manager.
        on_error (Optional[Callable[[str], None]]): Callback for error reporting.
        _static_handlers (Dict[str, Callable[[], None]]): Map of layout attribute names to handler functions.
    """
    def __init__(self, layout: 'HudLayout', world: World, event_bus: EventBus, on_error: Optional[Callable[[str], None]] = None):
        """
        Initializes the HudEvents handler.

        Args:
            layout (HudLayout): The HudLayout component.
            world (World): The ECS World instance.
            event_bus (EventBus): The event bus.
            on_error (Callable[[str], None], optional): Callback for error reporting.
        """
        self.layout = layout
        self.world = world
        self.event_bus = event_bus
        self.on_error = on_error
        self.selected_entities: list[int] = []

        self.settings_service: Optional[SettingsService] = None
        if hasattr(self.world.services, 'try_get'):
             self.settings_service = self.world.services.try_get(SettingsService)

        self.audio_manager: Optional[AudioManager] = None
        if hasattr(self.world.services, 'try_get'):
            self.audio_manager = self.world.services.try_get(AudioManager)

        # Map layout attribute names to handlers
        self._static_handlers = {
            'save_btn': self._save_game,
            'load_btn': self._load_game,
            'pause_btn': lambda: self.event_bus.publish(TogglePauseRequest()),
            'speed_btn': lambda: self.event_bus.publish(CycleSpeedRequest()),
            'settings_btn': self._open_settings,
            'clean_btn': lambda: self.event_bus.publish(CleanToolRequestedEvent()),
        }

    def _save_game(self) -> None:
        persistence = self.world.services.try_get(PersistenceService)
        if persistence:
            persistence.save_game("savegame.json")

    def _load_game(self) -> None:
        persistence = self.world.services.try_get(PersistenceService)
        if persistence:
            persistence.load_game("savegame.json")

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

        # 1. Check static handlers (by looking up current button on layout)
        for attr_name, handler in self._static_handlers.items():
            # Check if layout has this button and if it matches the event element
            if hasattr(self.layout, attr_name) and getattr(self.layout, attr_name) == ui_element:
                handler()
                return True

        # 2. Check settings window buttons
        if self._handle_settings_buttons(ui_element):
            return True

        # 3. Check dynamic buy buttons
        if self._handle_buy_buttons(ui_element):
            return True

        # 4. Check selection window buttons
        if self._handle_selection_buttons(ui_element):
            return True

        return False

    def _handle_settings_buttons(self, ui_element: Any) -> bool:
        """Handles buttons within the settings window."""
        if not self.layout.settings_window:
            return False

        if ui_element == self.layout.settings_controls.get("save_btn"):
            self._save_settings()
            self.layout.close_settings_window()
            return True

        if ui_element == self.layout.settings_controls.get("cancel_btn"):
            self._revert_audio_settings()
            self.layout.close_settings_window()
            return True

        if ui_element == self.layout.settings_controls.get("fullscreen_btn"):
            self._toggle_fullscreen_btn()
            return True

        return False

    def _handle_buy_buttons(self, ui_element: Any) -> bool:
        """Handles dynamic buy buttons."""
        if ui_element in self.layout.buy_buttons:
            data = self.layout.buy_buttons[ui_element]
            type_id = data["type_id"]
            cost = data["cost"]
            category = data["category"]
            name = data["name"]

            economy = self.world.services.get(EconomyService)
            if economy.get_money() >= cost:
                self.event_bus.publish(PlacementStartedEvent(type_id, cost, category))
            elif self.on_error:
                self.on_error(f"Not enough money to buy {name}! Needed: ${cost}")
            return True
        return False

    def _handle_selection_buttons(self, ui_element: Any) -> bool:
        """Handles buttons in the selection window."""
        if not self.layout.selection_window:
            return False

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
             self.settings_service = self.world.services.try_get(SettingsService)

        if self.settings_service:
            self.layout.create_settings_window(self.settings_service.settings)
        else:
            if self.on_error:
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
        if isinstance(resolution_str, tuple):
            resolution_str = resolution_str[0]

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
                logger.error(f"Failed to change display mode: {e}")

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
