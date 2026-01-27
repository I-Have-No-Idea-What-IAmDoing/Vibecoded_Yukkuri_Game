"""
Module for handling UI events from the HUD.
"""

import pygame
import pygame_gui
from typing import Any, TYPE_CHECKING
from collections.abc import Callable
from ...engine.event_bus import EventBus
from ...engine.audio import AudioManager
from ..settings_service import SettingsService
from ..services import EconomyService
from ...engine.ecs import World
from ..events import (
    PlacementStartedEvent,
    TogglePauseRequest,
    CycleSpeedRequest,
    TrainEntityRequest,
    PunishEntityRequest,
    SellEntityRequest,
    CleanToolRequestedEvent,
    ResolutionChangedEvent,
    SaveGameRequest,
    LoadGameRequest,
    LevelUpEvent,
)

from ..components import Transform
from ..prefabs.effects import create_floating_text

if TYPE_CHECKING:
    from .hud_layout import HudLayout


class HudEvents:
    """
    Handles UI events for the HUD, such as button clicks.
    """

    def __init__(
        self,
        layout: "HudLayout",
        world: World,
        event_bus: EventBus,
        on_error: Callable[[str], None] | None = None,
    ):
        """
        Initializes HudEvents.

        Args:
            layout (HudLayout): The layout object containing UI elements.
            world (World): The ECS World instance.
            event_bus (EventBus): The event bus for publishing game events.
            on_error (Optional[Callable[[str], None]]): Callback for error reporting.
        """
        self.layout = layout
        self.world = world
        self.event_bus = event_bus
        self.on_error = on_error
        self.selected_entities: list[int] = []

        self.settings_service: SettingsService | None = None
        if hasattr(self.world.services, "try_get"):
            self.settings_service = self.world.services.try_get(SettingsService)

        self.audio_manager: AudioManager | None = None
        if hasattr(self.world.services, "try_get"):
            self.audio_manager = self.world.services.try_get(AudioManager)

        # Listen for Level Up events
        self.event_bus.subscribe(LevelUpEvent, self.on_level_up)

        # Map layout attribute names to handlers
        self._static_handlers: dict[str, Callable[[], None]] = {
            "save_btn": self._save_game,
            "load_btn": self._load_game,
            "pause_btn": lambda: self.event_bus.publish(TogglePauseRequest()),
            "speed_btn": lambda: self.event_bus.publish(CycleSpeedRequest()),
            "settings_btn": self._open_settings,
            "clean_btn": lambda: self.event_bus.publish(CleanToolRequestedEvent()),
        }

    def _play_click(self) -> None:
        """Plays the UI click sound."""
        if self.audio_manager:
            self.audio_manager.play_sound("click")

    def _save_game(self) -> None:
        """Publishes a SaveGameRequest."""
        # Default filename for UI-based save
        self.event_bus.publish(SaveGameRequest("savegame"))

    def _load_game(self) -> None:
        """Publishes a LoadGameRequest."""
        self.event_bus.publish(LoadGameRequest("savegame"))

    def on_level_up(self, event: LevelUpEvent) -> None:
        """Handles LevelUpEvent to show floating text."""
        trans = self.world.get_component(event.entity_id, Transform)
        if trans:
            text = f"{event.skill_id.capitalize()} Lv.{event.new_level}!"
            create_floating_text(
                self.world,
                trans.x,
                trans.y - 40,
                text,
                (255, 215, 0),  # Gold color
                size=24,
                velocity_y=-30.0,
            )

    def set_selected_entities(self, entity_ids: list[int]) -> None:
        """
        Sets the currently selected entities.

        Args:
            entity_ids (list[int]): List of selected entity IDs.
        """
        self.selected_entities = entity_ids

    def process_event(self, event: pygame.event.Event) -> bool:
        """
        Processes a Pygame event for UI interactions.

        Args:
            event (pygame.event.Event): The event to process.

        Returns:
            bool: True if the event was handled, False otherwise.
        """
        if event.type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
            return self._handle_slider_event(event)

        if event.type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED:
            return True

        if event.type != pygame_gui.UI_BUTTON_PRESSED:
            return False

        ui_element = event.ui_element

        for attr_name, handler in self._static_handlers.items():
            if (
                hasattr(self.layout, attr_name)
                and getattr(self.layout, attr_name) == ui_element
            ):
                self._play_click()
                handler()
                return True

        if self._handle_settings_buttons(ui_element):
            self._play_click()
            return True

        if self._handle_buy_buttons(ui_element):
            self._play_click()
            return True

        if self._handle_selection_buttons(ui_element):
            self._play_click()
            return True

        return False

    def _handle_settings_buttons(self, ui_element: Any) -> bool:
        """Handles clicks on settings window buttons."""
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
        """Handles clicks on buy buttons."""
        if ui_element in self.layout.buy_buttons:
            data = self.layout.buy_buttons[ui_element]
            type_id = data["type_id"]
            cost = data["cost"]
            category = data["category"]
            name = data["name"]
            image_name = data.get("image", "")

            economy = self.world.services.get(EconomyService)
            if economy.get_money() >= cost:
                self.event_bus.publish(
                    PlacementStartedEvent(type_id, cost, category, image_name)
                )
            elif self.on_error:
                self.on_error(f"Not enough money to buy {name}! Needed: ${cost}")
            return True
        return False

    def _handle_selection_buttons(self, ui_element: Any) -> bool:
        """Handles clicks on selection panel buttons (Sell, Train, Punish)."""
        if (
            not self.layout.entity_info_panel
            or not self.layout.entity_info_panel.window
        ):
            return False

        panel = self.layout.entity_info_panel

        if panel.sell_btn and ui_element == panel.sell_btn:
            for entity_id in self.selected_entities:
                self.event_bus.publish(SellEntityRequest(entity_id))
            return True

        if panel.train_btn and ui_element == panel.train_btn:
            for entity_id in self.selected_entities:
                self.event_bus.publish(TrainEntityRequest(entity_id))
            return True

        if panel.punish_btn and ui_element == panel.punish_btn:
            for entity_id in self.selected_entities:
                self.event_bus.publish(PunishEntityRequest(entity_id))
            return True

        return False

    def _open_settings(self) -> None:
        """Opens the settings window."""
        if not self.settings_service:
            self.settings_service = self.world.services.try_get(SettingsService)

        if self.settings_service:
            self.layout.create_settings_window(self.settings_service.settings)
        else:
            if self.on_error:
                self.on_error("Settings Service not available.")

    def _handle_slider_event(self, event: pygame.event.Event) -> bool:
        """Handles slider movement events."""
        if not self.layout.settings_window:
            return False

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
        """Toggles the fullscreen setting state."""
        if not self.layout.settings_window:
            return

        current = self.layout.settings_controls.get("fullscreen_value", False)
        new_value = not current
        self.layout.settings_controls["fullscreen_value"] = new_value

        btn = self.layout.settings_controls.get("fullscreen_btn")
        if btn:
            btn.set_text("Fullscreen: ON" if new_value else "Fullscreen: OFF")

    def _save_settings(self) -> None:
        """Saves current settings from UI to SettingsService."""
        if not self.settings_service or not self.layout.settings_window:
            return

        controls = self.layout.settings_controls

        master = controls["master_slider"].get_current_value() / 100.0
        bgm = controls["bgm_slider"].get_current_value() / 100.0
        sfx = controls["sfx_slider"].get_current_value() / 100.0

        self.settings_service.set("audio", "master_volume", master)
        self.settings_service.set("audio", "bgm_volume", bgm)
        self.settings_service.set("audio", "sfx_volume", sfx)

        resolution_str = controls["resolution_dropdown"].selected_option
        if isinstance(resolution_str, tuple):
            resolution_str = resolution_str[0]

        try:
            width, height = map(int, resolution_str.split("x"))
        except ValueError:
            width, height = 1280, 720

        fullscreen = controls["fullscreen_value"]

        self.settings_service.set("window", "width", width)
        self.settings_service.set("window", "height", height)
        self.settings_service.set("window", "fullscreen", fullscreen)

        self.settings_service.save_settings()

        self._apply_window_settings(width, height, fullscreen)

    def _apply_window_settings(self, width: int, height: int, fullscreen: bool) -> None:
        """Applies window settings (resolution/fullscreen)."""
        # We just publish the event. The actual window resizing and context handling
        # should be done by the Application or the Scene that owns the display/engine.
        self.event_bus.publish(ResolutionChangedEvent(width, height, fullscreen))

    def _revert_audio_settings(self) -> None:
        """Reverts audio settings to last saved values (on cancel)."""
        if not self.settings_service or not self.audio_manager:
            return

        master = self.settings_service.get("audio", "master_volume")
        bgm = self.settings_service.get("audio", "bgm_volume")
        sfx = self.settings_service.get("audio", "sfx_volume")

        self.audio_manager.set_master_volume(master if master is not None else 1.0)
        self.audio_manager.set_bgm_volume(bgm if bgm is not None else 1.0)
        self.audio_manager.set_sfx_volume(sfx if sfx is not None else 1.0)
