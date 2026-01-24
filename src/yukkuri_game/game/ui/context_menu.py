"""
Module for the Context Menu UI.
"""

from collections.abc import Callable
from typing import Any

import pygame
import pygame_gui
from pygame_gui.elements import UIPanel, UISelectionList


class ContextMenu:
    """
    A contextual menu that appears at a specific position.

    Attributes:
        manager (pygame_gui.UIManager): The UI Manager.
        window_rect (pygame.Rect): The rectangle of the menu.
        selection_list (UISelectionList): The list of options.
        on_action (Callable[[str, Any], None]): Callback when an action is selected.
        target_data (Any): Data associated with the current context (e.g., Entity ID).
    """

    def __init__(self, manager: pygame_gui.UIManager):
        """
        Initializes the ContextMenu.

        Args:
            manager (pygame_gui.UIManager): The UI Manager.
        """
        self.manager = manager
        self.panel: UIPanel | None = None
        self.selection_list: UISelectionList | None = None
        self.on_action: Callable[[str, Any], None] | None = None
        self.target_data: Any = None
        self.active = False
        self.options: list[tuple[str, str]] = []  # (Label, ActionID)

    def show(
        self,
        position: tuple[int, int],
        options: list[tuple[str, str]],
        on_action: Callable[[str, Any], None],
        target_data: Any,
    ) -> None:
        """
        Shows the context menu at the given position.

        Args:
            position (tuple[int, int]): Screen coordinates (x, y).
            options (list[tuple[str, str]]): List of (Label, ActionID) tuples.
            on_action (Callable[[str, Any], None]): Callback function (action_id, target_data).
            target_data (Any): Arbitrary data to pass back to the callback.
        """
        self.hide()

        if not options:
            return

        self.options = options
        self.on_action = on_action
        self.target_data = target_data

        item_height = 25
        width = 150
        height = len(options) * item_height + 10  # padding

        # Ensure menu doesn't go off-screen
        screen_w, screen_h = self.manager.window_resolution
        x, y = position

        if x + width > screen_w:
            x = screen_w - width
        if y + height > screen_h:
            y = screen_h - height

        rect = pygame.Rect(x, y, width, height)

        self.panel = UIPanel(
            relative_rect=rect,
            starting_height=100,  # Ensure it's on top
            manager=self.manager,
            object_id="context_menu_panel",
        )

        # Extract just the labels for the selection list
        item_list: list[str | tuple[str, str]] = [opt[0] for opt in options]

        self.selection_list = UISelectionList(
            relative_rect=pygame.Rect(0, 0, width, height),
            item_list=item_list,
            manager=self.manager,
            container=self.panel,
            object_id="context_menu_list",
        )

        self.active = True

    def hide(self) -> None:
        """Hides/Destroys the context menu."""
        if self.panel:
            self.panel.kill()
            self.panel = None
        self.selection_list = None
        self.active = False
        self.on_action = None
        self.target_data = None
        self.options = []

    def process_event(self, event: pygame.event.Event) -> bool:
        """
        Processes UI events to handle selection.

        Args:
            event (pygame.event.Event): The event to process.

        Returns:
            bool: True if the event was consumed/handled by the menu.
        """
        if not self.active:
            return False

        if event.type == pygame_gui.UI_SELECTION_LIST_NEW_SELECTION:
            if event.ui_element == self.selection_list:
                selected_label = event.text
                # Find corresponding action ID
                action_id = next(
                    (opt[1] for opt in self.options if opt[0] == selected_label), None
                )

                if action_id and self.on_action:
                    self.on_action(action_id, self.target_data)

                self.hide()
                return True

        # Close if clicked outside
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.panel:
                mx, my = event.pos
                if not self.panel.rect.collidepoint(mx, my):
                    self.hide()
                    # We don't return True here because the click might be meant for something else
                    # but typically context menus consume the click that closes them or pass it through?
                    # Usually consuming it is safer to prevent accidental clicks.
                    return True

        return False
