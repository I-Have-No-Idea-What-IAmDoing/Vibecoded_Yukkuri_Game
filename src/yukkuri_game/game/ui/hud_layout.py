import pygame
import pygame_gui
from typing import Optional
from pygame_gui.elements import UIPanel, UILabel, UIButton, UIWindow, UITextBox

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
        bottom_panel (Optional[UIPanel]): The bottom panel container.
        add_reimu_btn (Optional[UIButton]): Button to buy a Reimu.
        add_cookie_btn (Optional[UIButton]): Button to buy a Cookie.
        selection_window (Optional[UIWindow]): The window displaying selected entity info.
        info_label (Optional[UITextBox]): Text box within the selection window showing stats.
        sell_btn (Optional[UIButton]): Button to sell the selected entity.
        train_btn (Optional[UIButton]): Button to train the selected entity.
        debug_window (Optional[UIWindow]): The debug info window.
        debug_text_box (Optional[UITextBox]): Text box within the debug window.
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
        self.bottom_panel: Optional[UIPanel] = None

        # Buy Buttons Map: {button: {"type_id": str, "category": str, "cost": int}}
        self.buy_buttons: dict = {}

        # Selection Window Elements
        self.selection_window: Optional[UIWindow] = None
        self.info_label: Optional[UITextBox] = None
        self.sell_btn: Optional[UIButton] = None
        self.train_btn: Optional[UIButton] = None

        # Debug Window Elements
        self.debug_window: Optional[UIWindow] = None
        self.debug_text_box: Optional[UITextBox] = None

        self._create_top_bar()
        self._create_bottom_bar()

    def _create_top_bar(self) -> None:
        """
        Creates the top UI panel and its children.
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
            container=self.top_panel
        )

        self.speed_btn = UIButton(
            relative_rect=pygame.Rect(470, 10, 80, 30),
            text="1x",
            manager=self.manager,
            container=self.top_panel
        )

        self.save_btn = UIButton(
            relative_rect=pygame.Rect(self.width - 220, 10, 100, 30),
            text="Save",
            manager=self.manager,
            container=self.top_panel
        )

        self.load_btn = UIButton(
            relative_rect=pygame.Rect(self.width - 110, 10, 100, 30),
            text="Load",
            manager=self.manager,
            container=self.top_panel
        )

    def _create_bottom_bar(self) -> None:
        """
        Creates the bottom UI panel and its children.
        """
        self.bottom_panel = UIPanel(
            relative_rect=pygame.Rect(0, self.height - 100, self.width, 100),
            manager=self.manager
        )

        x_offset = 10
        y_offset = 10
        btn_width = 140
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
                container=self.bottom_panel
            )
            self.buy_buttons[btn] = {"type_id": type_id, "category": "yukkuri", "cost": cost, "name": name}
            x_offset += btn_width + spacing

        # Create buttons for Items
        for type_id, data in self.item_types.items():
            cost = getattr(data, 'cost', 10)
            name = getattr(data, 'name', type_id.capitalize())

            btn = UIButton(
                relative_rect=pygame.Rect(x_offset, y_offset, btn_width, btn_height),
                text=f"Buy {name} (${cost})",
                manager=self.manager,
                container=self.bottom_panel
            )
            self.buy_buttons[btn] = {"type_id": type_id, "category": "item", "cost": cost, "name": name}
            x_offset += btn_width + spacing

    def create_selection_window(self, has_stats: bool, selection_count: int = 1) -> None:
        """
        Creates or recreates the selection window.

        Args:
            has_stats (bool): True if the selected entity has stats (is a Yukkuri), False otherwise.
            selection_count (int): The number of selected entities. Defaults to 1.
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

            self.sell_btn = UIButton(
                relative_rect=pygame.Rect(10, 220, 290, 40),
                text=sell_text,
                manager=self.manager,
                container=self.selection_window
            )
            self.train_btn = UIButton(
                relative_rect=pygame.Rect(10, 270, 290, 40),
                text=train_text,
                manager=self.manager,
                container=self.selection_window
            )

    def close_selection_window(self) -> None:
        """
        Closes and cleans up the selection window.
        """
        if self.selection_window:
            self.selection_window.kill()
            self.selection_window = None
            self.info_label = None
            self.sell_btn = None
            self.train_btn = None

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
        """
        if self.debug_window:
            self.debug_window.kill()
            self.debug_window = None
            self.debug_text_box = None
