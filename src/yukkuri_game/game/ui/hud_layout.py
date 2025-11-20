import pygame
from pygame_gui import UIManager
from pygame_gui.elements import UIPanel, UILabel, UIButton
from pygame_gui.windows import UIMessageWindow

class HudLayout:
    """
    Manages the static layout of the HUD (Heads-Up Display).

    This includes the top status bar and the bottom action bar.
    """

    def __init__(self, manager: UIManager, width: int, height: int):
        """
        Initialize the HUD layout.

        Args:
            manager: The pygame_gui UIManager.
            width: The screen width.
            height: The screen height.
        """
        self.manager = manager
        self.width = width
        self.height = height

        self.top_panel = None
        self.money_label = None
        self.save_btn = None
        self.load_btn = None
        self.time_label = None
        self.pause_btn = None
        self.speed_btn = None

        self.bottom_panel = None
        self.add_reimu_btn = None
        self.add_cookie_btn = None

        self._create_top_bar()
        self._create_bottom_bar()

    def _create_top_bar(self):
        """Creates the top status bar with money, time, and control buttons."""
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

        # Time Controls
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

    def _create_bottom_bar(self):
        """Creates the bottom action bar (Shop)."""
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

    def show_error(self, message: str):
        """
        Displays an error message in a popup window.

        Args:
            message: The error message to display.
        """
        UIMessageWindow(
            rect=pygame.Rect((self.width - 400) // 2, (self.height - 250) // 2, 400, 250),
            html_message=message,
            manager=self.manager,
            window_title="Error"
        )
