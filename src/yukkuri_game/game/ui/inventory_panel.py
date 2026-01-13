"""
Module for Inventory UI Panel.
"""

import pygame
import pygame_gui
from pygame_gui.elements import UIWindow, UIButton, UIScrollingContainer, UILabel, UIPanel
from typing import Optional, TYPE_CHECKING
from ..inventory_component import InventoryComponent, InventoryDropRequest

if TYPE_CHECKING:
    from ...engine.ecs import World
    from ...engine.resource_manager import ResourceManager

class InventoryPanel:
    """
    UI Panel to display and manage an entity's inventory.
    """

    def __init__(self, manager: pygame_gui.UIManager, world: "World"):
        self.manager = manager
        self.world = world
        self.window: Optional[UIWindow] = None
        self.entity_id: Optional[int] = None
        self.scroll_container: Optional[UIScrollingContainer] = None

    def show(self, entity_id: int, position: tuple[int, int] = (100, 100)) -> None:
        """
        Shows the inventory for the specified entity.
        """
        self.close()
        self.entity_id = entity_id

        # Verify entity has inventory
        inventory = self.world.get_component(entity_id, InventoryComponent)
        if not inventory:
            return

        self.window = UIWindow(
            rect=pygame.Rect(position[0], position[1], 300, 400),
            manager=self.manager,
            window_display_title=f"Inventory (ID: {entity_id})",
            resizable=True
        )

        self.scroll_container = UIScrollingContainer(
            relative_rect=pygame.Rect(0, 0, 268, 330),
            manager=self.manager,
            container=self.window,
            anchors={'top': 'top', 'bottom': 'bottom', 'left': 'left', 'right': 'right'}
        )

        self.refresh()

    def close(self) -> None:
        """Closes the inventory window."""
        if self.window:
            self.window.kill()
            self.window = None
            self.scroll_container = None
            self.entity_id = None

    def refresh(self) -> None:
        """Refreshes the item list."""
        if not self.window or not self.scroll_container or self.entity_id is None:
            return

        # Clear existing items (pygame_gui doesn't have a clear children method easily,
        # so we rely on kill()ing children or recreating container.
        # Recreating container is safer/cleaner here.)
        self.scroll_container.kill()
        self.scroll_container = UIScrollingContainer(
            relative_rect=pygame.Rect(0, 0, self.window.get_container().rect.width, self.window.get_container().rect.height),
            manager=self.manager,
            container=self.window,
             anchors={'top': 'top', 'bottom': 'bottom', 'left': 'left', 'right': 'right'}
        )

        inventory = self.world.get_component(self.entity_id, InventoryComponent)
        if not inventory or not inventory.items:
            UILabel(
                relative_rect=pygame.Rect(10, 10, 200, 30),
                text="Empty",
                manager=self.manager,
                container=self.scroll_container
            )
            return

        y_pos = 5
        item_height = 40

        from ...engine.resource_manager import ResourceManager
        rm = self.world.services.try_get(ResourceManager)

        for item in inventory.items:
            name = item.item_type_id
            if rm:
                item_data = rm.item_types.get(item.item_type_id)
                if item_data:
                    name = getattr(item_data, "name", name)

            panel = UIPanel(
                relative_rect=pygame.Rect(5, y_pos, 250, item_height),
                manager=self.manager,
                container=self.scroll_container,
                starting_layer_height=1
            )

            UILabel(
                relative_rect=pygame.Rect(5, 5, 150, 30),
                text=f"{name} x{item.quantity}",
                manager=self.manager,
                container=panel
            )

            drop_btn = UIButton(
                relative_rect=pygame.Rect(160, 5, 80, 30),
                text="Drop",
                manager=self.manager,
                container=panel,
                object_id=f"drop_btn_{item.item_type_id}"
            )
            # We need to map button to action. Since this class manages it, we can store it or bind generic event.
            # Storing button->action map in this instance is easiest.
            # However, for simplicity let's just use the object_id in the event handler if we wire it up.
            # But the event handler is usually HudEvents.
            # Ideally InventoryPanel should handle its own events or delegate.
            # Let's attach metadata to the button if possible, or keep a dict.
            # For now, we will handle events in `process_event` of this class if we add one,
            # or rely on the main HUD event loop calling into this.

            y_pos += item_height + 5

        self.scroll_container.set_scrollable_area_dimensions((250, y_pos))

    def process_event(self, event: pygame.event.Event) -> bool:
        if not self.window or self.entity_id is None:
            return False

        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if hasattr(event.ui_element, "object_ids"): # PygameGUI 0.6.9+
                ids = event.ui_element.object_ids
                if ids and ids[-1].startswith("drop_btn_"):
                    item_type_id = ids[-1].replace("drop_btn_", "")
                    self._drop_item(item_type_id)
                    return True
            # Fallback for older pygame_gui or simple object_id string
            elif isinstance(event.ui_element.object_id, str) and event.ui_element.object_id.startswith("drop_btn_"):
                 item_type_id = event.ui_element.object_id.replace("drop_btn_", "")
                 self._drop_item(item_type_id)
                 return True

        return False

    def _drop_item(self, item_type_id: str) -> None:
        if self.entity_id is None:
            return

        # Add Drop Request
        self.world.add_component(
            self.entity_id,
            InventoryDropRequest(item_type_id=item_type_id, quantity=1)
        )
        # Refresh UI next frame or immediately?
        # The system processes it in update(). So UI might lag one frame.
        # We can force refresh later or just wait.
        # But for feedback, let's just print/log.
        print(f"Requesting drop of {item_type_id} from {self.entity_id}")
