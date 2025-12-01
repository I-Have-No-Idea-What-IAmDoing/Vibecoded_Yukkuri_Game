import pygame
from typing import Union, Tuple, Optional, Dict

from pygame_gui.core import ObjectID, UIElement
from pygame_gui.core.interfaces import IContainerLikeInterface, IUIManagerInterface
from pygame_gui.elements import UITabContainer, UIButton, UIPanel

class TabbedPanel(UITabContainer):
    """
    A tabbed panel that supports both horizontal and vertical orientation.
    """
    def __init__(
        self,
        relative_rect: pygame.Rect,
        manager: Optional[IUIManagerInterface] = None,
        container: Optional[IContainerLikeInterface] = None,
        starting_height: int = 1,
        parent_element: Optional[UIElement] = None,
        object_id: Optional[Union[ObjectID, str]] = None,
        anchors: Optional[Dict[str, str]] = None,
        visible: int = 1,
        orientation: str = 'horizontal',
        tab_button_size: Tuple[int, int] = (150, 30)
    ):
        self.orientation = orientation
        self.tab_button_size = tab_button_size

        super().__init__(
            relative_rect=relative_rect,
            manager=manager,
            container=container,
            starting_height=starting_height,
            parent_element=parent_element,
            object_id=object_id,
            anchors=anchors,
            visible=visible
        )

        # Override button_height if provided via tab_button_size
        self.button_height = self.tab_button_size[1]

        # For vertical tabs, we need a button width as well.
        self.button_width = self.tab_button_size[0]

    def _calculate_container_rect_by_layout(self) -> pygame.Rect:
        # Use self.rect to ensure we are sizing relative to this widget
        # self.rect is absolute, but we want size.
        # And we return a relative rect for the child container.

        width = self.rect.width
        height = self.rect.height

        if self.orientation == 'vertical':
            # Tabs on the left, content on the right
            return pygame.Rect(
                self.button_width,
                0,
                max(0, width - self.button_width),
                height
            )
        else:
            # Tabs on top, content below (default behavior)
            return pygame.Rect(
                0,
                self.button_height,
                width,
                max(0, height - self.button_height),
            )

    def add_tab(
        self, title_text: str, title_object_id: str = "#tab_title_button"
    ) -> int:
        """
        Create a new tab.
        Override to support vertical layout.
        """
        # We must use self._root_container as container for children, verified by test.

        self.rebuild(len(self.tabs) + 1)

        # Calculate button rect
        if self.orientation == 'vertical':
            furthest_bottom = 0
            if len(self.tabs) > 0:
                 # Sum of heights of previous buttons
                 for tab in self.tabs:
                     furthest_bottom += tab["button"].rect.height

            button_rect = pygame.Rect(0, furthest_bottom, self.button_width, self.button_height)
            max_button_width = self.button_width

        else:
            # Horizontal
            max_button_width = self._calculate_max_button_width(len(self.tabs) + 1)
            furthest_right = 0
            if len(self.tabs) > 0:
                for tab in self.tabs:
                    furthest_right += tab["button"].rect.width
            button_rect = pygame.Rect(furthest_right, 0, -1, self.button_height)

        button = UIButton(
            relative_rect=button_rect,
            text=title_text,
            manager=self.ui_manager,
            container=self._root_container,
            parent_element=self,
            object_id=ObjectID(title_object_id, "@tab_title_button")
        )

        if self.orientation == 'horizontal':
             button.max_dynamic_width = max_button_width

        container_rect = self._calculate_container_rect_by_layout()
        container = UIPanel(
            relative_rect=container_rect,
            manager=self.ui_manager,
            container=self._root_container,
            parent_element=self,
        )

        self.tabs.append({"text": title_text, "button": button, "container": container})

        tab_id = len(self.tabs) - 1
        if self.current_container_index is None:
            self.current_container_index = tab_id
            button.select()
            container.show()
        else:
            container.hide()

        # Re-run rebuild to ensure everything is aligned
        self.rebuild()

        return tab_id

    def rebuild(self, count: Optional[int] = None):
        """
        Rebuilds the tab container.
        """
        UIElement.rebuild(self)

        if count is None:
            count = len(self.tabs)

        if self.orientation == 'vertical':
            current_bottom = 0
            for i, tab in enumerate(self.tabs, 0):
                button: UIButton = tab["button"]
                if i >= count:
                    continue

                button.set_relative_position((0, current_bottom))
                button.set_dimensions((self.button_width, self.button_height))

                current_bottom += self.button_height

                container = tab["container"]
                container_rect = self._calculate_container_rect_by_layout()
                container.set_relative_position(container_rect.topleft)
                container.set_dimensions(container_rect.size)

                if i == self.current_container_index:
                    container.show()
                    button.select()
                else:
                    container.hide()

        else:
            # Horizontal
            max_button_width = self._calculate_max_button_width(count)
            current_right = 0
            for i, tab in enumerate(self.tabs, 0):
                button: UIButton = tab["button"]
                if i >= count:
                    continue

                button.max_dynamic_width = max_button_width
                button.rebuild()
                button.set_relative_position((current_right, 0))
                current_right += button.rect.width

                container = tab["container"]
                container_rect = self._calculate_container_rect_by_layout()
                container.set_relative_position(container_rect.topleft)
                container.set_dimensions(container_rect.size)

                if i == self.current_container_index:
                    container.show()
                    button.select()
                else:
                    container.hide()
