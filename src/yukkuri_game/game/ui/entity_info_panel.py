"""
Module for Entity Info Panel logic.
"""

import pygame
import pygame_gui
from pygame_gui.elements import (
    UIWindow,
    UITextBox,
    UIButton,
    UIScrollingContainer,
    UIPanel,
)
from pygame_gui.core import ObjectID
from .tabbed_panel import TabbedPanel


class SafeUIScrollingContainer(UIScrollingContainer):
    """
    A subclass of UIScrollingContainer that initializes scroll bars to None
    before calling super().__init__(). This prevents an AttributeError when
    the container is initialized inside a hidden container (e.g., a non-active tab),
    which causes hide() to be called during initialization before attributes are set.
    """

    def __init__(self, *args, **kwargs):
        """
        Initializes the SafeUIScrollingContainer.

        Args:
            *args: Variable length argument list for UIScrollingContainer.
            **kwargs: Arbitrary keyword arguments for UIScrollingContainer.
        """
        self.vert_scroll_bar = None
        self.horiz_scroll_bar = None
        self._root_container = None
        self._view_container = None
        super().__init__(*args, **kwargs)


class EntityInfoPanel:
    """
    Manages the Entity Info Window, including Tabs for Stats and Skills.

    Attributes:
        manager (pygame_gui.UIManager): The UI manager.
        window (Optional[UIWindow]): The main window element.
        tabbed_panel (Optional[TabbedPanel]): The tabbed panel element.
        stats_text_box (Optional[UITextBox]): Text box for stats.
        stats_scroll (Optional[UIScrollingContainer]): Scroll container for stats.
        skills_text_box (Optional[UITextBox]): Text box for skills.
        skills_scroll (Optional[UIScrollingContainer]): Scroll container for skills.
        sell_btn (Optional[UIButton]): Button to sell entity.
        train_btn (Optional[UIButton]): Button to train entity.
        punish_btn (Optional[UIButton]): Button to punish entity.
        width (int): Window width.
        height (int): Window height.
    """

    def __init__(
        self, manager: pygame_gui.UIManager, root_container: UIPanel | None = None
    ):
        """
        Initializes the EntityInfoPanel.

        Args:
            manager (pygame_gui.UIManager): The UI Manager.
            root_container (Optional[UIPanel]): Parent container, if any.
        """
        self.manager = manager
        self.window: UIWindow | None = None
        self.tabbed_panel: TabbedPanel | None = None

        # Stats Tab Elements
        self.stats_text_box: UITextBox | None = None
        self.stats_scroll: UIScrollingContainer | None = None

        # Skills Tab Elements
        self.skills_text_box: UITextBox | None = None
        self.skills_scroll: UIScrollingContainer | None = None

        # Buttons (shared or bottom area)
        self.sell_btn: UIButton | None = None
        self.train_btn: UIButton | None = None
        self.punish_btn: UIButton | None = None

        # Layout config
        self.width = 330
        self.height = 450

    def show(
        self,
        position: tuple[int, int],
        has_stats: bool,
        selection_count: int,
        title: str = "Entity Info",
    ) -> None:
        """
        Creates and shows the window.

        Args:
            position (tuple[int, int]): Position to display the window.
            has_stats (bool): Whether the selected entity has stats.
            selection_count (int): Number of selected entities.
            title (str): Title of the window.

        Returns:
            None
        """
        self.close()

        rect = pygame.Rect(position[0], position[1], self.width, self.height)

        # Ensure position is within safe bounds or at least handled if container is used
        # In this specific issue, pygame_gui calculates dimensions using container size.
        # If we are root, it uses manager.root_container.
        # We assume self.manager is valid.

        self.window = UIWindow(
            rect=rect, manager=self.manager, window_display_title=title, resizable=True
        )

        # Content Area
        # We reserve bottom 130px for buttons
        content_height = self.height - 180

        self.tabbed_panel = TabbedPanel(
            relative_rect=pygame.Rect(10, 10, self.width - 20, content_height),
            manager=self.manager,
            container=self.window,
            orientation="horizontal",
            tab_button_size=(100, 30),
        )

        # Tab 1: Stats
        self._create_stats_tab()

        # Tab 2: Skills (Only if Yukkuri/has_stats)
        if has_stats:
            self._create_skills_tab()

        # Action Buttons
        self._create_buttons(has_stats, selection_count)

    def close(self) -> None:
        """
        Closes the window and cleans up elements.

        Returns:
            None
        """
        if self.window:
            self.window.kill()
            self.window = None
            self.tabbed_panel = None
            self.stats_text_box = None
            self.skills_text_box = None
            self.sell_btn = None
            self.train_btn = None
            self.punish_btn = None

    def _create_stats_tab(self) -> None:
        """Creates the Stats tab."""
        if not self.tabbed_panel:
            return

        tab_id = self.tabbed_panel.add_tab("Stats")
        container = self.tabbed_panel.tabs[tab_id]["container"]

        self.stats_scroll = SafeUIScrollingContainer(
            relative_rect=pygame.Rect(
                0, 0, container.rect.width, container.rect.height
            ),
            manager=self.manager,
            container=container,
            anchors={
                "top": "top",
                "bottom": "bottom",
                "left": "left",
                "right": "right",
            },
        )

        self.stats_text_box = UITextBox(
            html_text="Loading...",
            relative_rect=pygame.Rect(0, 0, container.rect.width - 20, -1),
            manager=self.manager,
            container=self.stats_scroll,
            wrap_to_height=True,
            anchors={"top": "top", "bottom": "top", "left": "left", "right": "left"},
        )

    def _create_skills_tab(self) -> None:
        """Creates the Skills tab."""
        if not self.tabbed_panel:
            return

        tab_id = self.tabbed_panel.add_tab("Skills")
        container = self.tabbed_panel.tabs[tab_id]["container"]

        self.skills_scroll = SafeUIScrollingContainer(
            relative_rect=pygame.Rect(
                0, 0, container.rect.width, container.rect.height
            ),
            manager=self.manager,
            container=container,
            anchors={
                "top": "top",
                "bottom": "bottom",
                "left": "left",
                "right": "right",
            },
        )

        self.skills_text_box = UITextBox(
            html_text="Loading Skills...",
            relative_rect=pygame.Rect(0, 0, container.rect.width - 20, -1),
            manager=self.manager,
            container=self.skills_scroll,
            wrap_to_height=True,
            anchors={"top": "top", "bottom": "top", "left": "left", "right": "left"},
        )

    def _create_buttons(self, has_stats: bool, selection_count: int) -> None:
        """Creates action buttons based on entity type."""
        if not self.window:
            return

        y_pos = self.height - 160

        if has_stats:
            sell_text = (
                f"Sell All ({selection_count})" if selection_count > 1 else "Sell"
            )
            train_text = (
                f"Train All ({selection_count}) (+Badge)"
                if selection_count > 1
                else "Train (+Badge)"
            )
            punish_text = (
                f"Punish All ({selection_count})" if selection_count > 1 else "Punish"
            )

            self.sell_btn = UIButton(
                relative_rect=pygame.Rect(10, y_pos, 290, 40),
                text=sell_text,
                manager=self.manager,
                container=self.window,
                tool_tip_text="Sell selected entities",
                object_id=ObjectID(class_id="sell_button"),
            )
            self.train_btn = UIButton(
                relative_rect=pygame.Rect(10, y_pos + 50, 290, 40),
                text=train_text,
                manager=self.manager,
                container=self.window,
                tool_tip_text="Train selected entities",
                object_id=ObjectID(class_id="train_button"),
            )
            self.punish_btn = UIButton(
                relative_rect=pygame.Rect(10, y_pos + 100, 290, 40),
                text=punish_text,
                manager=self.manager,
                container=self.window,
                tool_tip_text="Punish selected entities",
                object_id=ObjectID(class_id="punish_button"),
            )
        else:
            # Just Sell for items
            self.sell_btn = UIButton(
                relative_rect=pygame.Rect(10, y_pos, 290, 40),
                text=f"Sell All ({selection_count})",
                manager=self.manager,
                container=self.window,
                tool_tip_text="Sell selected items",
                object_id=ObjectID(class_id="sell_button"),
            )

    def update_stats(self, text: str) -> None:
        """
        Updates the stats text box content.

        Args:
            text (str): The HTML text to display.

        Returns:
            None
        """
        if self.stats_text_box and self.stats_text_box.html_text != text:
            old_height = self.stats_text_box.rect.height
            self.stats_text_box.set_text(text)
            new_height = self.stats_text_box.rect.height

            if old_height != new_height and self.stats_scroll:
                self.stats_scroll.set_scrollable_area_dimensions(
                    (self.stats_scroll.rect.width - 20, new_height)
                )

    def update_skills(self, text: str) -> None:
        """
        Updates the skills text box content.

        Args:
            text (str): The HTML text to display.

        Returns:
            None
        """
        if self.skills_text_box and self.skills_text_box.html_text != text:
            old_height = self.skills_text_box.rect.height
            self.skills_text_box.set_text(text)
            new_height = self.skills_text_box.rect.height

            if old_height != new_height and self.skills_scroll:
                self.skills_scroll.set_scrollable_area_dimensions(
                    (self.skills_scroll.rect.width - 20, new_height)
                )
