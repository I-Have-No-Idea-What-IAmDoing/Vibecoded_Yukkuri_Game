"""
Module defining the HUD layout and UI element creation.
"""

from collections.abc import MutableMapping
from typing import Any, cast

import pygame
import pygame_gui
from pygame_gui.core import ObjectID
from pygame_gui.elements import (
    UIButton,
    UIDropDownMenu,
    UIHorizontalSlider,
    UILabel,
    UIPanel,
    UIScrollingContainer,
    UITextBox,
    UIWindow,
)

from ...engine.data_models import UserSettings
from .custom_elements import NonBlockingTextBox
from .entity_info_panel import EntityInfoPanel


class HudLayout:
    """
    Manages the layout and creation of HUD elements.
    """

    def __init__(
        self,
        ui_manager: pygame_gui.UIManager,
        width: int,
        height: int,
        yukkuri_types: MutableMapping[str, Any] | None = None,
        item_types: MutableMapping[str, Any] | None = None,
    ):
        """
        Initializes the HudLayout.

        Args:
            ui_manager (pygame_gui.UIManager): The pygame_gui UIManager.
            width (int): The width of the screen.
            height (int): The height of the screen.
            yukkuri_types (MutableMapping[str, Any]): Dictionary of available Yukkuri types.
            item_types (MutableMapping[str, Any]): Dictionary of available Item types.
        """
        self.manager: pygame_gui.UIManager = ui_manager
        self.width: int = width
        self.height: int = height
        self.yukkuri_types: MutableMapping[str, Any] = (
            yukkuri_types if yukkuri_types is not None else {}
        )
        self.item_types: MutableMapping[str, Any] = (
            item_types if item_types is not None else {}
        )

        # Elements
        self.top_panel: UIPanel | None = None
        self.money_label: UILabel | None = None
        self.time_label: UILabel | None = None
        self.save_btn: UIButton | None = None
        self.load_btn: UIButton | None = None
        self.pause_btn: UIButton | None = None
        self.speed_btn: UIButton | None = None
        self.settings_btn: UIButton | None = None
        self.bottom_panel: UIPanel | None = None
        self.scrolling_container: UIScrollingContainer | None = None

        # Buy Buttons Map: {button: {"type_id": str, "category": str, "cost": int}}
        self.buy_buttons: dict[UIButton, dict[str, Any]] = {}

        # Entity Info Panel
        self.entity_info_panel: EntityInfoPanel | None = None

        self.clean_btn: UIButton | None = None

        # Log Box
        self.log_box: UITextBox | None = None

        # Debug Window Elements
        self.debug_window: UIWindow | None = None
        self.debug_text_box: UITextBox | None = None

        # Settings Window Elements
        self.settings_window: UIWindow | None = None
        self.settings_controls: dict[str, Any] = {}

        # Hover Tooltip Elements
        self.hover_tooltip_label: NonBlockingTextBox | None = None

        self._create_top_bar()
        self._create_bottom_bar()

    def resize(self, width: int, height: int) -> None:
        """
        Resizes the HUD layout.

        Args:
            width (int): New width.
            height (int): New height.
        """
        self.width = width
        self.height = height
        self.rebuild_ui()

    def rebuild_ui(self) -> None:
        """
        Rebuilds the UI elements.
        """
        self.clear_ui()
        self._create_top_bar()
        self._create_bottom_bar()

        # Close windows to avoid layout issues
        self.close_settings_window()
        self.close_debug_window()
        self.close_selection_window()

    def clear_ui(self) -> None:
        """
        Clears existing UI elements.
        """
        if self.top_panel:
            self.top_panel.kill()
            self.top_panel = None

        if self.bottom_panel:
            self.bottom_panel.kill()
            self.bottom_panel = None

        self.buy_buttons.clear()

        # Reset element references
        self.money_label = None
        self.time_label = None
        self.save_btn = None
        self.load_btn = None
        self.pause_btn = None
        self.speed_btn = None
        self.settings_btn = None
        self.log_box = None
        self.scrolling_container = None
        self.clean_btn = None

        # Ensure info panel is closed on clear
        if self.entity_info_panel:
            self.entity_info_panel.close()
            self.entity_info_panel = None

    def _create_top_bar(self) -> None:
        """
        Creates the top UI panel and its children.
        """
        self.top_panel = UIPanel(
            relative_rect=pygame.Rect(0, 0, self.width, 50), manager=self.manager
        )

        self.money_label = UILabel(
            relative_rect=pygame.Rect(10, 10, 200, 30),
            text="Money: $0",
            manager=self.manager,
            container=self.top_panel,
        )

        self.time_label = UILabel(
            relative_rect=pygame.Rect(220, 10, 150, 30),
            text="Time: 00:00",
            manager=self.manager,
            container=self.top_panel,
        )

        self.pause_btn = UIButton(
            relative_rect=pygame.Rect(380, 10, 80, 30),
            text="Pause",
            manager=self.manager,
            container=self.top_panel,
            tool_tip_text="Pause/Resume the game (Space)",
            object_id=ObjectID(class_id="control_button"),
        )

        self.speed_btn = UIButton(
            relative_rect=pygame.Rect(470, 10, 80, 30),
            text="1x",
            manager=self.manager,
            container=self.top_panel,
            tool_tip_text="Change game speed",
            object_id=ObjectID(class_id="control_button"),
        )

        self.save_btn = UIButton(
            relative_rect=pygame.Rect(self.width - 330, 10, 100, 30),
            text="Save",
            manager=self.manager,
            container=self.top_panel,
            tool_tip_text="Save current game state to 'savegame'",
            object_id=ObjectID(class_id="menu_button"),
        )

        self.load_btn = UIButton(
            relative_rect=pygame.Rect(self.width - 220, 10, 100, 30),
            text="Load",
            manager=self.manager,
            container=self.top_panel,
            tool_tip_text="Load game state from 'savegame'",
            object_id=ObjectID(class_id="menu_button"),
        )

        self.settings_btn = UIButton(
            relative_rect=pygame.Rect(self.width - 110, 10, 100, 30),
            text="Settings",
            manager=self.manager,
            container=self.top_panel,
            tool_tip_text="Open Settings Menu",
            object_id=ObjectID(class_id="menu_button"),
        )

    def _create_bottom_bar(self) -> None:
        """
        Creates the bottom UI panel and its children.
        """
        self.bottom_panel = UIPanel(
            relative_rect=pygame.Rect(0, self.height - 100, self.width, 100),
            manager=self.manager,
        )

        # Log Box Area (Left side)
        self.log_box = UITextBox(
            html_text="Welcome to Yukkuri Game!<br>",
            relative_rect=pygame.Rect(10, 10, 300, 80),
            manager=self.manager,
            container=self.bottom_panel,
        )

        # --- Scrolling Container for Buy Buttons ---
        # Reserve space for log box (320px) and clean button (160px from right)
        scroll_container_x = 320
        scroll_container_width = self.width - scroll_container_x - 160
        scroll_container_height = 80

        self.scrolling_container = UIScrollingContainer(
            relative_rect=pygame.Rect(
                scroll_container_x, 5, scroll_container_width, scroll_container_height
            ),
            manager=self.manager,
            container=self.bottom_panel,
            allow_scroll_x=True,
            allow_scroll_y=False,
        )

        x_offset = 5
        y_offset = 5
        button_width = 200
        button_height = 40
        spacing = 10

        # Create buttons for Yukkuris
        for type_id, data in self.yukkuri_types.items():
            cost = getattr(data, "cost", 100)
            name = getattr(data, "name", type_id.capitalize())

            btn = UIButton(
                relative_rect=pygame.Rect(
                    x_offset, y_offset, button_width, button_height
                ),
                text=f"Buy {name} (${cost})",
                manager=self.manager,
                container=self.scrolling_container,
                tool_tip_text=f"Buy {name} for ${cost}. Click to place.",
                object_id=ObjectID(class_id="buy_button"),
            )
            # Try to get image from data, else default to type_id/name
            image_name = getattr(data, "image", f"{type_id}.png")
            self.buy_buttons[btn] = {
                "type_id": type_id,
                "category": "yukkuri",
                "cost": cost,
                "name": name,
                "image": image_name,
            }
            x_offset += button_width + spacing

        # Create buttons for Items
        for type_id, data in self.item_types.items():
            cost = getattr(data, "cost", 10)
            name = getattr(data, "name", type_id.capitalize())
            description = getattr(data, "description", f"A nice {name}")

            btn = UIButton(
                relative_rect=pygame.Rect(
                    x_offset, y_offset, button_width, button_height
                ),
                text=f"Buy {name} (${cost})",
                manager=self.manager,
                container=self.scrolling_container,
                tool_tip_text=f"Buy {name} for ${cost}. {description}",
                object_id=ObjectID(class_id="buy_button"),
            )
            image_name = getattr(data, "image", f"{type_id}.png")
            self.buy_buttons[btn] = {
                "type_id": type_id,
                "category": "item",
                "cost": cost,
                "name": name,
                "image": image_name,
            }
            x_offset += button_width + spacing

        # Set the scrollable area size based on total button width
        total_content_width = x_offset
        self.scrolling_container.set_scrollable_area_dimensions(
            (total_content_width, button_height + 10)
        )

        # Create Clean Button (outside the scroll container, fixed position)
        self.clean_btn = UIButton(
            relative_rect=pygame.Rect(
                self.width - 150, 30, button_width, button_height
            ),
            text="Clean Tool",
            manager=self.manager,
            container=self.bottom_panel,
            tool_tip_text="Remove waste and dirt from the ground",
            object_id=ObjectID(class_id="clean_button"),
        )

    def create_selection_window(
        self, has_stats: bool, selection_count: int = 1
    ) -> None:
        """
        Creates or recreates the selection window using EntityInfoPanel.

        Args:
            has_stats (bool): True if the selected entity has stats (is a Yukkuri), False otherwise.
            selection_count (int): The number of selected entities. Defaults to 1.
        """
        if self.entity_info_panel is None:
            self.entity_info_panel = EntityInfoPanel(self.manager)

        self.entity_info_panel.show(
            position=(self.width - 350, 60),
            has_stats=has_stats,
            selection_count=selection_count,
        )

    def close_selection_window(self) -> None:
        """
        Closes and cleans up the selection window.
        """
        if self.entity_info_panel:
            self.entity_info_panel.close()
            # We don't nullify entity_info_panel itself to keep the instance,
            # but close() kills the UI elements.
            # Actually, let's keep it null safe.
            self.entity_info_panel = None

    def create_debug_window(self) -> None:
        """
        Creates the debug window.
        """
        if self.debug_window:
            self.debug_window.kill()

        self.debug_window = UIWindow(
            rect=pygame.Rect(10, 60, 300, 200),
            manager=self.manager,
            window_display_title="Debug Info",
            resizable=True,
        )

        self.debug_text_box = UITextBox(
            html_text="Debug info...",
            relative_rect=pygame.Rect(10, 10, 260, 140),
            manager=self.manager,
            container=self.debug_window,
            anchors={
                "top": "top",
                "bottom": "bottom",
                "left": "left",
                "right": "right",
            },
        )

    def close_debug_window(self) -> None:
        """
        Closes the debug window.
        """
        if self.debug_window:
            self.debug_window.kill()
            self.debug_window = None
            self.debug_text_box = None

    def create_settings_window(
        self, current_settings: dict[str, Any] | UserSettings
    ) -> None:
        """
        Creates the settings window.

        Args:
            current_settings (dict[str, Any] | UserSettings): Current settings values.
        """
        # Close existing window if any
        if self.settings_window:
            self.settings_window.kill()

        window_width = 400
        window_height = 350
        x = (self.width - window_width) // 2
        y = (self.height - window_height) // 2

        self.settings_window = UIWindow(
            rect=pygame.Rect(x, y, window_width, window_height),
            manager=self.manager,
            window_display_title="Settings",
            resizable=False,
        )

        if isinstance(current_settings, UserSettings):
            master_vol = current_settings.audio.master_volume * 100
            bgm_vol = current_settings.audio.bgm_volume * 100
            sfx_vol = current_settings.audio.sfx_volume * 100

            width = current_settings.window.width
            height = current_settings.window.height
            fullscreen = current_settings.window.fullscreen
        else:
            audio_settings = current_settings.get("audio", {})
            master_vol = audio_settings.get("master_volume", 1.0) * 100
            bgm_vol = audio_settings.get("bgm_volume", 1.0) * 100
            sfx_vol = audio_settings.get("sfx_volume", 1.0) * 100

            window_settings = current_settings.get("window", {})
            width = window_settings.get("width", 1280)
            height = window_settings.get("height", 720)
            fullscreen = window_settings.get("fullscreen", False)

        # Master Volume
        UILabel(
            relative_rect=pygame.Rect(20, 20, 100, 30),
            text="Master Vol:",
            manager=self.manager,
            container=self.settings_window,
        )
        self.settings_controls["master_slider"] = UIHorizontalSlider(
            relative_rect=pygame.Rect(130, 20, 200, 30),
            start_value=master_vol,
            value_range=(0, 100),
            manager=self.manager,
            container=self.settings_window,
        )
        self.settings_controls["master_slider"].set_tooltip_text(  # type: ignore[attr-defined]
            "Adjust Master Volume"
        )

        # BGM Volume
        UILabel(
            relative_rect=pygame.Rect(20, 60, 100, 30),
            text="BGM Vol:",
            manager=self.manager,
            container=self.settings_window,
        )
        self.settings_controls["bgm_slider"] = UIHorizontalSlider(
            relative_rect=pygame.Rect(130, 60, 200, 30),
            start_value=bgm_vol,
            value_range=(0, 100),
            manager=self.manager,
            container=self.settings_window,
        )
        self.settings_controls["bgm_slider"].set_tooltip_text(  # type: ignore[attr-defined]
            "Adjust Background Music Volume"
        )

        # SFX Volume
        UILabel(
            relative_rect=pygame.Rect(20, 100, 100, 30),
            text="SFX Vol:",
            manager=self.manager,
            container=self.settings_window,
        )
        self.settings_controls["sfx_slider"] = UIHorizontalSlider(
            relative_rect=pygame.Rect(130, 100, 200, 30),
            start_value=sfx_vol,
            value_range=(0, 100),
            manager=self.manager,
            container=self.settings_window,
        )
        self.settings_controls["sfx_slider"].set_tooltip_text(  # type: ignore[attr-defined]
            "Adjust Sound Effects Volume"
        )

        # Window Settings

        current_res = f"{width}x{height}"
        resolution_options = ["1280x720", "1920x1080", "800x600"]
        if current_res not in resolution_options:
            resolution_options.append(current_res)

        UILabel(
            relative_rect=pygame.Rect(20, 140, 100, 30),
            text="Resolution:",
            manager=self.manager,
            container=self.settings_window,
        )
        self.settings_controls["resolution_dropdown"] = UIDropDownMenu(
            options_list=cast(list[str | tuple[str, str]], resolution_options),
            starting_option=current_res,
            relative_rect=pygame.Rect(130, 140, 200, 30),
            manager=self.manager,
            container=self.settings_window,
        )
        self.settings_controls["resolution_dropdown"].set_tooltip_text(  # type: ignore[attr-defined]
            "Change Window Resolution"
        )

        self.settings_controls["fullscreen_btn"] = UIButton(
            relative_rect=pygame.Rect(130, 180, 200, 30),
            text="Fullscreen: ON" if fullscreen else "Fullscreen: OFF",
            manager=self.manager,
            container=self.settings_window,
            tool_tip_text="Toggle Fullscreen Mode",
        )
        self.settings_controls["fullscreen_value"] = fullscreen

        # Buttons
        self.settings_controls["save_btn"] = UIButton(
            relative_rect=pygame.Rect(60, 250, 100, 40),
            text="Save",
            manager=self.manager,
            container=self.settings_window,
            tool_tip_text="Save changes and close",
        )

        self.settings_controls["cancel_btn"] = UIButton(
            relative_rect=pygame.Rect(240, 250, 100, 40),
            text="Cancel",
            manager=self.manager,
            container=self.settings_window,
            tool_tip_text="Discard changes and close",
        )

    def close_settings_window(self) -> None:
        """
        Closes the settings window.
        """
        if self.settings_window:
            self.settings_window.kill()
            self.settings_window = None
            self.settings_controls = {}

    def create_hover_tooltip(self) -> None:
        """
        Creates the hover tooltip label if it doesn't exist.
        """
        if self.hover_tooltip_label is None:
            self.hover_tooltip_label = NonBlockingTextBox(
                html_text="",
                relative_rect=pygame.Rect(0, 0, 200, 60),
                manager=self.manager,
            )
            # Start hidden
            self.hover_tooltip_label.hide()

    def update_hover_tooltip(self, text: str, pos: tuple[int, int]) -> None:
        """
        Updates the hover tooltip with text and position.

        Args:
            text (str): Text to display.
            pos (tuple[int, int]): Screen position (x, y).
        """
        if not self.hover_tooltip_label:
            self.create_hover_tooltip()

        if text:
            if self.hover_tooltip_label:
                if not self.hover_tooltip_label.visible:
                    self.hover_tooltip_label.show()

                # Only update if text changed (optimization)
                if self.hover_tooltip_label.html_text != text:
                    self.hover_tooltip_label.set_text(text)

                # Adjust position to not go off screen
                x, y = pos
                width, height = self.hover_tooltip_label.rect.size

                # Offset slightly
                x += 15
                y += 15

                if x + width > self.width:
                    x = self.width - width
                if y + height > self.height:
                    y = self.height - height

                self.hover_tooltip_label.set_position((x, y))

                # Bring to front
                # Cast to Any to bypass strict type check for move_window_to_front which expects UIWindow/UIPanel
                # but works for UIElements in the stack generally or we assume it's fine for this valid element
                self.manager.ui_window_stack.move_window_to_front(
                    cast(Any, self.hover_tooltip_label)
                )

        else:
            if self.hover_tooltip_label and self.hover_tooltip_label.visible:
                self.hover_tooltip_label.hide()
