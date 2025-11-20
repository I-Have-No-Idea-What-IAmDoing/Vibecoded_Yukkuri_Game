import pygame
import pygame_gui
from pygame_gui.elements import UIPanel, UILabel, UIButton, UIWindow, UITextBox

class HudLayout:
    """
    Manages the layout and creation of HUD elements.
    """
    def __init__(self, ui_manager: pygame_gui.UIManager, width: int, height: int):
        self.manager = ui_manager
        self.width = width
        self.height = height

        # Elements
        self.top_panel = None
        self.money_label = None
        self.time_label = None
        self.save_btn = None
        self.load_btn = None
        self.pause_btn = None
        self.speed_btn = None
        self.bottom_panel = None
        self.add_reimu_btn = None
        self.add_cookie_btn = None

        # Selection Window Elements
        self.selection_window = None
        self.info_label = None
        self.sell_btn = None
        self.train_btn = None

        # Debug Window Elements
        self.debug_window = None
        self.debug_text_box = None

        self._create_top_bar()
        self._create_bottom_bar()

    def _create_top_bar(self):
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

    def _create_bottom_bar(self):
        self.bottom_panel = UIPanel(
            relative_rect=pygame.Rect(0, self.height - 100, self.width, 100),
            manager=self.manager
        )

        self.add_reimu_btn = UIButton(
            relative_rect=pygame.Rect(10, 10, 120, 40),
            text="Buy Reimu ($100)",
            manager=self.manager,
            container=self.bottom_panel
        )

        self.add_cookie_btn = UIButton(
            relative_rect=pygame.Rect(140, 10, 120, 40),
            text="Buy Cookie ($10)",
            manager=self.manager,
            container=self.bottom_panel
        )

    def create_selection_window(self, has_stats: bool):
        """
        Creates or recreates the selection window.
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
            self.sell_btn = UIButton(
                relative_rect=pygame.Rect(10, 220, 290, 40),
                text="Sell",
                manager=self.manager,
                container=self.selection_window
            )
            self.train_btn = UIButton(
                relative_rect=pygame.Rect(10, 270, 290, 40),
                text="Train (+Badge)",
                manager=self.manager,
                container=self.selection_window
            )

    def close_selection_window(self):
        if self.selection_window:
            self.selection_window.kill()
            self.selection_window = None
            self.info_label = None
            self.sell_btn = None
            self.train_btn = None

    def create_debug_window(self):
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

    def close_debug_window(self):
        if self.debug_window:
            self.debug_window.kill()
            self.debug_window = None
            self.debug_text_box = None
