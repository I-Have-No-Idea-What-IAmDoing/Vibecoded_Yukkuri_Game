import pygame
import pygame_gui
from typing import Optional
from pygame_gui.elements import UIPanel, UILabel, UIButton, UIWindow, UITextBox, UIHorizontalSlider, UIDropDownMenu

class HudLayout:
    """
    Manages the layout and creation of HUD elements.

    Attributes:
        manager (pygame_gui.UIManager): The UI manager instance.
        width (int): The width of the screen.
        height (int): The height of the screen.
        top_panel (Optional[UIPanel]): The top panel container.
        money_label (Optional[UILabel]): Label displaying player money.
        time_label (Optional[UILabel]): Label displaying game time.
        save_btn (Optional[UIButton]): Button to save the game.
        load_btn (Optional[UIButton]): Button to load the game.
        pause_btn (Optional[UIButton]): Button to pause/resume the game.
        speed_btn (Optional[UIButton]): Button to cycle game speed.
        settings_btn (Optional[UIButton]): Button to open settings.
        bottom_panel (Optional[UIPanel]): The bottom panel container.
        add_reimu_btn (Optional[UIButton]): Button to buy a Reimu.
        add_cookie_btn (Optional[UIButton]): Button to buy a Cookie.
        selection_window (Optional[UIWindow]): The window displaying selected entity info.
        info_label (Optional[UITextBox]): Text box within the selection window showing stats.
        sell_btn (Optional[UIButton]): Button to sell the selected entity.
        train_btn (Optional[UIButton]): Button to train the selected entity.
        debug_window (Optional[UIWindow]): The debug info window.
        debug_text_box (Optional[UITextBox]): Text box within the debug window.
        settings_window (Optional[UIWindow]): The settings window.
    """
    def __init__(self, ui_manager: pygame_gui.UIManager, width: int, height: int, yukkuri_types: dict = None, item_types: dict = None):
        """
        Initializes the HudLayout.

        Args:
            ui_manager (pygame_gui.UIManager): The pygame_gui UIManager.
            width (int): The width of the screen.
            height (int): The height of the screen.
            yukkuri_types (dict): Dictionary of available Yukkuri types.
            item_types (dict): Dictionary of available Item types.
        """
        self.manager = ui_manager
        self.width = width
        self.height = height
        self.yukkuri_types = yukkuri_types if yukkuri_types is not None else {}
        self.item_types = item_types if item_types is not None else {}

        # Elements
        self.top_panel: Optional[UIPanel] = None
        self.money_label: Optional[UILabel] = None
        self.time_label: Optional[UILabel] = None
        self.save_btn: Optional[UIButton] = None
        self.load_btn: Optional[UIButton] = None
        self.pause_btn: Optional[UIButton] = None
        self.speed_btn: Optional[UIButton] = None
        self.settings_btn: Optional[UIButton] = None
        self.bottom_panel: Optional[UIPanel] = None

        # Buy Buttons Map: {button: {"type_id": str, "category": str, "cost": int}}
        self.buy_buttons: dict = {}

        # Selection Window Elements
        self.selection_window: Optional[UIWindow] = None
        self.info_label: Optional[UITextBox] = None
        self.sell_btn: Optional[UIButton] = None
        self.train_btn: Optional[UIButton] = None
        self.punish_btn: Optional[UIButton] = None

        self.clean_btn: Optional[UIButton] = None

        # Log Box
        self.log_box: Optional[UITextBox] = None

        # Debug Window Elements
        self.debug_window: Optional[UIWindow] = None
        self.debug_text_box: Optional[UITextBox] = None

        # Settings Window Elements
        self.settings_window: Optional[UIWindow] = None
        self.settings_controls: dict = {}

        # Hover Tooltip Elements
        self.hover_tooltip_panel: Optional[UIPanel] = None
        self.hover_tooltip_label: Optional[UITextBox] = None

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
        self.clean_btn = None

    def _create_top_bar(self) -> None:
        """
        Creates the top UI panel and its children.

        Returns:
            None
        """
        self.top_panel = UIPanel(
            relative_rect=pygame.Rect(0, 0, self.width, 50),
            manager=self.manager
        )

        self.money_label = UILabel(
            relative_rect=pygame.Rect(10, 10, 200, 30),
            text="Money: $0",
            manager=self.manager,
            container=self.top_panel
        )

        self.time_label = UILabel(
            relative_rect=pygame.Rect(220, 10, 150, 30),
            text="Time: 00:00",
            manager=self.manager,
            container=self.top_panel
        )

        self.pause_btn = UIButton(
            relative_rect=pygame.Rect(380, 10, 80, 30),
            text="Pause",
            manager=self.manager,
            container=self.top_panel,
            tool_tip_text="Pause/Resume the game"
        )

        self.speed_btn = UIButton(
            relative_rect=pygame.Rect(470, 10, 80, 30),
            text="1x",
            manager=self.manager,
            container=self.top_panel,
            tool_tip_text="Change game speed"
        )

        self.save_btn = UIButton(
            relative_rect=pygame.Rect(self.width - 330, 10, 100, 30),
            text="Save",
            manager=self.manager,
            container=self.top_panel,
            tool_tip_text="Save current game state"
        )

        self.load_btn = UIButton(
            relative_rect=pygame.Rect(self.width - 220, 10, 100, 30),
            text="Load",
            manager=self.manager,
            container=self.top_panel,
            tool_tip_text="Load saved game"
        )

        self.settings_btn = UIButton(
            relative_rect=pygame.Rect(self.width - 110, 10, 100, 30),
            text="Settings",
            manager=self.manager,
            container=self.top_panel,
            tool_tip_text="Open Settings Menu"
        )

    def _create_bottom_bar(self) -> None:
        """
        Creates the bottom UI panel and its children.

        Returns:
            None
        """
        self.bottom_panel = UIPanel(
            relative_rect=pygame.Rect(0, self.height - 100, self.width, 100),
            manager=self.manager
        )

        # Log Box Area (Left side)
        self.log_box = UITextBox(
            html_text="Welcome to Yukkuri Game!<br>",
            relative_rect=pygame.Rect(10, 10, 300, 80),
            manager=self.manager,
            container=self.bottom_panel
        )

        x_offset = 320
        y_offset = 10
        btn_width = 120
        btn_height = 40
        spacing = 10

        # Create buttons for Yukkuris
        for type_id, data in self.yukkuri_types.items():
            cost = getattr(data, 'cost', 100)
            name = getattr(data, 'name', type_id.capitalize())

            btn = UIButton(
                relative_rect=pygame.Rect(x_offset, y_offset, btn_width, btn_height),
                text=f"Buy {name} (${cost})",
                manager=self.manager,
                container=self.bottom_panel,
                tool_tip_text=f"Buy {name} for ${cost}. Click to place."
            )
            self.buy_buttons[btn] = {"type_id": type_id, "category": "yukkuri", "cost": cost, "name": name}
            x_offset += btn_width + spacing

        # Create buttons for Items
        for type_id, data in self.item_types.items():
            cost = getattr(data, 'cost', 10)
            name = getattr(data, 'name', type_id.capitalize())
            description = getattr(data, 'description', f"A nice {name}")

            btn = UIButton(
                relative_rect=pygame.Rect(x_offset, y_offset, btn_width, btn_height),
                text=f"Buy {name} (${cost})",
                manager=self.manager,
                container=self.bottom_panel,
                tool_tip_text=f"Buy {name} for ${cost}. {description}"
            )
            self.buy_buttons[btn] = {"type_id": type_id, "category": "item", "cost": cost, "name": name}
            x_offset += btn_width + spacing

        # Create Clean Button
        self.clean_btn = UIButton(
            relative_rect=pygame.Rect(self.width - 150, y_offset, btn_width, btn_height),
            text="Clean Tool",
            manager=self.manager,
            container=self.bottom_panel,
            tool_tip_text="Click to clean poop"
        )

    def create_selection_window(self, has_stats: bool, selection_count: int = 1) -> None:
        """
        Creates or recreates the selection window.

        Args:
            has_stats (bool): True if the selected entity has stats (is a Yukkuri), False otherwise.
            selection_count (int): The number of selected entities. Defaults to 1.

        Returns:
            None
        """
        self.close_selection_window()

        self.selection_window = UIWindow(
            rect=pygame.Rect(self.width - 350, 60, 330, 400),
            manager=self.manager,
            window_display_title="Entity Info",
            resizable=True
        )

        self.info_label = UITextBox(
            html_text="",
            relative_rect=pygame.Rect(10, 10, 290, 200),
            manager=self.manager,
            container=self.selection_window,
            anchors={'top': 'top', 'bottom': 'top', 'left': 'left', 'right': 'right'}
        )

        if has_stats:
            sell_text = "Sell All" if selection_count > 1 else "Sell"
            train_text = "Train All (+Badge)" if selection_count > 1 else "Train (+Badge)"
            punish_text = "Punish All" if selection_count > 1 else "Punish"

            self.sell_btn = UIButton(
                relative_rect=pygame.Rect(10, 220, 290, 40),
                text=sell_text,
                manager=self.manager,
                container=self.selection_window,
                tool_tip_text="Sell selected entities"
            )
            self.train_btn = UIButton(
                relative_rect=pygame.Rect(10, 270, 290, 40),
                text=train_text,
                manager=self.manager,
                container=self.selection_window,
                tool_tip_text="Train selected entities to increase badges"
            )
            self.punish_btn = UIButton(
                relative_rect=pygame.Rect(10, 320, 290, 40),
                text=punish_text,
                manager=self.manager,
                container=self.selection_window,
                tool_tip_text="Punish selected entities to increase discipline but lower health/happiness"
            )

    def close_selection_window(self) -> None:
        """
        Closes and cleans up the selection window.

        Returns:
            None
        """
        if self.selection_window:
            self.selection_window.kill()
            self.selection_window = None
            self.info_label = None
            self.sell_btn = None
            self.train_btn = None
            self.punish_btn = None

    def create_debug_window(self) -> None:
        """
        Creates the debug window.

        Returns:
            None
        """
        if self.debug_window:
            self.debug_window.kill()

        self.debug_window = UIWindow(
            rect=pygame.Rect(10, 60, 300, 200),
            manager=self.manager,
            window_display_title="Debug Info",
            resizable=True
        )

        self.debug_text_box = UITextBox(
            html_text="Debug info...",
            relative_rect=pygame.Rect(10, 10, 260, 140),
            manager=self.manager,
            container=self.debug_window,
            anchors={'top': 'top', 'bottom': 'bottom', 'left': 'left', 'right': 'right'}
        )

    def close_debug_window(self) -> None:
        """
        Closes the debug window.

        Returns:
            None
        """
        if self.debug_window:
            self.debug_window.kill()
            self.debug_window = None
            self.debug_text_box = None

    def create_settings_window(self, current_settings: dict) -> None:
        """
        Creates the settings window.

        Args:
            current_settings (dict): Current settings values.
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
            resizable=False
        )

        audio_settings = current_settings.get("audio", {})
        master_vol = audio_settings.get("master_volume", 1.0) * 100
        bgm_vol = audio_settings.get("bgm_volume", 1.0) * 100
        sfx_vol = audio_settings.get("sfx_volume", 1.0) * 100

        # Master Volume
        UILabel(relative_rect=pygame.Rect(20, 20, 100, 30), text="Master Vol:", manager=self.manager, container=self.settings_window)
        self.settings_controls["master_slider"] = UIHorizontalSlider(
            relative_rect=pygame.Rect(130, 20, 200, 30),
            start_value=master_vol, value_range=(0, 100),
            manager=self.manager, container=self.settings_window
        )

        # BGM Volume
        UILabel(relative_rect=pygame.Rect(20, 60, 100, 30), text="BGM Vol:", manager=self.manager, container=self.settings_window)
        self.settings_controls["bgm_slider"] = UIHorizontalSlider(
            relative_rect=pygame.Rect(130, 60, 200, 30),
            start_value=bgm_vol, value_range=(0, 100),
            manager=self.manager, container=self.settings_window
        )

        # SFX Volume
        UILabel(relative_rect=pygame.Rect(20, 100, 100, 30), text="SFX Vol:", manager=self.manager, container=self.settings_window)
        self.settings_controls["sfx_slider"] = UIHorizontalSlider(
            relative_rect=pygame.Rect(130, 100, 200, 30),
            start_value=sfx_vol, value_range=(0, 100),
            manager=self.manager, container=self.settings_window
        )

        # Window Settings
        window_settings = current_settings.get("window", {})
        width = window_settings.get("width", 1280)
        height = window_settings.get("height", 720)
        fullscreen = window_settings.get("fullscreen", False)

        current_res = f"{width}x{height}"
        resolution_options = ["1280x720", "1920x1080", "800x600"]
        if current_res not in resolution_options:
            resolution_options.append(current_res)

        UILabel(relative_rect=pygame.Rect(20, 140, 100, 30), text="Resolution:", manager=self.manager, container=self.settings_window)
        self.settings_controls["resolution_dropdown"] = UIDropDownMenu(
            options_list=resolution_options,
            starting_option=current_res,
            relative_rect=pygame.Rect(130, 140, 200, 30),
            manager=self.manager,
            container=self.settings_window
        )

        self.settings_controls["fullscreen_btn"] = UIButton(
            relative_rect=pygame.Rect(130, 180, 200, 30),
            text="Fullscreen: ON" if fullscreen else "Fullscreen: OFF",
            manager=self.manager,
            container=self.settings_window
        )
        self.settings_controls["fullscreen_value"] = fullscreen

        # Buttons
        self.settings_controls["save_btn"] = UIButton(
            relative_rect=pygame.Rect(60, 250, 100, 40),
            text="Save",
            manager=self.manager, container=self.settings_window
        )

        self.settings_controls["cancel_btn"] = UIButton(
            relative_rect=pygame.Rect(240, 250, 100, 40),
            text="Cancel",
            manager=self.manager, container=self.settings_window
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
        Creates the hover tooltip panel and label if they don't exist.

        Returns:
            None
        """
        if self.hover_tooltip_panel is None:
            self.hover_tooltip_panel = UIPanel(
                relative_rect=pygame.Rect(0, 0, 200, 60),
                manager=self.manager
            )
            # Start hidden
            self.hover_tooltip_panel.hide()

            self.hover_tooltip_label = UITextBox(
                html_text="",
                relative_rect=pygame.Rect(5, 5, 190, 50),
                manager=self.manager,
                container=self.hover_tooltip_panel
            )

    def update_hover_tooltip(self, text: str, pos: tuple[int, int]) -> None:
        """
        Updates the hover tooltip with text and position.

        Args:
            text (str): Text to display.
            pos (tuple[int, int]): Screen position (x, y).

        Returns:
            None
        """
        if not self.hover_tooltip_panel:
            self.create_hover_tooltip()

        if text:
            if not self.hover_tooltip_panel.visible:
                self.hover_tooltip_panel.show()

            # Only update if text changed (optimization)
            if self.hover_tooltip_label.html_text != text:
                self.hover_tooltip_label.set_text(text)

            # Adjust position to not go off screen
            x, y = pos
            width, height = self.hover_tooltip_panel.rect.size

            # Offset slightly
            x += 15
            y += 15

            if x + width > self.width:
                x = self.width - width
            if y + height > self.height:
                y = self.height - height

            self.hover_tooltip_panel.set_position((x, y))

            # Bring to front
            self.manager.ui_window_stack.move_window_to_front(self.hover_tooltip_panel)

        else:
            if self.hover_tooltip_panel.visible:
                self.hover_tooltip_panel.hide()
