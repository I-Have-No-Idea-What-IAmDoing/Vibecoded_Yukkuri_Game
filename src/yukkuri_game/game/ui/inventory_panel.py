"""
Module for Inventory UI Panel.
"""

from typing import TYPE_CHECKING

import pygame
import pygame_gui
from loguru import logger
from pygame_gui.elements import (
    UIButton,
    UILabel,
    UIPanel,
    UIScrollingContainer,
    UIWindow,
)

from ..events import InventoryItemActionEvent
from ..components import InventoryComponent

if TYPE_CHECKING:
    from ...engine.ecs import World
    from ...engine.event_bus import EventBus
    from ...engine.resource_manager import ResourceManager


class InventoryPanel:
    """
    UI Panel to display and manage an entity's inventory.

    Performance improvements:
    - Caches ResourceManager reference
    - Uses item name cache to avoid repeated lookups
    - Supports event-driven updates (auto-refresh on InventoryChangedEvent)

    Attributes:
        manager (pygame_gui.UIManager): UI Manager.
        world (World): ECS World.
        event_bus (EventBus | None): Event bus.
        window (UIWindow | None): The UI window element.
        entity_id (int | None): The ID of the entity whose inventory is shown.
        scroll_container (UIScrollingContainer | None): The scroll container.
    """

    def __init__(
        self,
        manager: pygame_gui.UIManager,
        world: "World",
        event_bus: "EventBus | None" = None,
    ):
        """
        Initializes the InventoryPanel.

        Args:
            manager (pygame_gui.UIManager): UI Manager.
            world (World): ECS World.
            event_bus (EventBus | None): Event bus.
        """
        self.manager = manager
        self.world = world
        self.event_bus = event_bus
        self.window: UIWindow | None = None
        self.entity_id: int | None = None
        self.scroll_container: UIScrollingContainer | None = None

        # Performance: Cache ResourceManager reference
        self._resource_manager: "ResourceManager | None" = None
        # Performance: Cache item names to avoid repeated lookups
        self._item_name_cache: dict[str, str] = {}

    @property
    def is_visible(self) -> bool:
        """Returns True if the inventory panel is currently visible."""
        return self.window is not None and self.entity_id is not None

    def _get_resource_manager(self) -> "ResourceManager | None":
        """Lazy load and cache ResourceManager."""
        if self._resource_manager is None:
            from ...engine.resource_manager import ResourceManager

            self._resource_manager = self.world.services.try_get(ResourceManager)
        return self._resource_manager

    def _get_item_name(self, item_type_id: str) -> str:
        """Get item display name with caching."""
        if item_type_id in self._item_name_cache:
            return self._item_name_cache[item_type_id]

        name = item_type_id  # Default to type_id
        rm = self._get_resource_manager()
        if rm:
            item_data = rm.item_types.get(item_type_id)
            if item_data:
                name = getattr(item_data, "name", name)

        self._item_name_cache[item_type_id] = name
        return name

    def show(self, entity_id: int, position: tuple[int, int] = (100, 100)) -> None:
        """
        Shows the inventory for the specified entity.

        Args:
            entity_id (int): The entity ID.
            position (tuple[int, int]): Screen coordinates for the window.
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
            resizable=True,
        )

        self.scroll_container = UIScrollingContainer(
            relative_rect=pygame.Rect(0, 0, 268, 330),
            manager=self.manager,
            container=self.window,
            anchors={
                "top": "top",
                "bottom": "bottom",
                "left": "left",
                "right": "right",
            },
        )

        self.refresh()

    def close(self) -> None:
        """Closes the inventory window."""
        if self.window:
            self.window.kill()  # type: ignore[no-untyped-call]
            self.window = None
            self.scroll_container = None
            self.entity_id = None

    def refresh(self) -> None:
        """Refreshes the item list with optimized lookups."""
        if not self.window or not self.scroll_container or self.entity_id is None:
            return

        # Clear existing items by recreating container
        self.scroll_container.kill()  # type: ignore[no-untyped-call]
        self.scroll_container = UIScrollingContainer(
            relative_rect=pygame.Rect(
                0,
                0,
                self.window.get_container().rect.width,
                self.window.get_container().rect.height,
            ),
            manager=self.manager,
            container=self.window,
            anchors={
                "top": "top",
                "bottom": "bottom",
                "left": "left",
                "right": "right",
            },
        )

        inventory = self.world.get_component(self.entity_id, InventoryComponent)
        if not inventory or not inventory.items:
            UILabel(
                relative_rect=pygame.Rect(10, 10, 200, 30),
                text="Empty",
                manager=self.manager,
                container=self.scroll_container,
            )
            return

        y_pos = 5
        item_height = 40

        for item in inventory.items:
            # Use cached name lookup
            name = self._get_item_name(item.item_type_id)

            panel = UIPanel(
                relative_rect=pygame.Rect(5, y_pos, 250, item_height),
                manager=self.manager,
                container=self.scroll_container,
                starting_height=1,
            )

            UILabel(
                relative_rect=pygame.Rect(5, 5, 150, 30),
                text=f"{name} x{item.quantity}",
                manager=self.manager,
                container=panel,
            )

            UIButton(
                relative_rect=pygame.Rect(160, 5, 80, 30),
                text="Drop",
                manager=self.manager,
                container=panel,
                object_id=f"drop_btn_{item.item_type_id}",
                tool_tip_text=f"Drop 1 {name} on the ground",
            )

            y_pos += item_height + 5

        self.scroll_container.set_scrollable_area_dimensions((250, y_pos))

    def process_event(self, event: pygame.event.Event) -> bool:
        """
        Process UI events and handle button clicks.

        Args:
            event (pygame.event.Event): The event to process.

        Returns:
            bool: True if event was handled.
        """
        if not self.window or self.entity_id is None:
            return False

        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            # Check for drop button clicks
            if hasattr(event.ui_element, "object_ids"):  # PygameGUI 0.6.9+
                ids = event.ui_element.object_ids
                if ids and ids[-1].startswith("drop_btn_"):
                    item_type_id = ids[-1].replace("drop_btn_", "")
                    self._drop_item(item_type_id)
                    return True
            # Fallback for older pygame_gui or simple object_id string
            elif isinstance(
                event.ui_element.object_id, str
            ) and event.ui_element.object_id.startswith("drop_btn_"):
                item_type_id = event.ui_element.object_id.replace("drop_btn_", "")
                self._drop_item(item_type_id)
                return True

        return False

    def _drop_item(self, item_type_id: str) -> None:
        """Request to drop an item using event-driven approach."""
        if self.entity_id is None:
            return

        # Play sound
        from ...engine.audio import AudioManager

        audio = self.world.services.try_get(AudioManager)
        if audio:
            audio.play_sound("click")

        if self.event_bus:
            # Preferred: Use event-driven approach for loose coupling
            self.event_bus.publish(
                InventoryItemActionEvent(
                    entity_id=self.entity_id,
                    item_type_id=item_type_id,
                    action="drop",
                    quantity=1,
                )
            )
            logger.debug(
                f"Published drop request for {item_type_id} from entity {self.entity_id}"
            )
        else:
            # Fallback: Direct component addition (for backwards compatibility)
            from ..components import InventoryDropRequest

            self.world.add_component(
                self.entity_id,
                InventoryDropRequest(item_type_id=item_type_id, quantity=1),
            )
            logger.debug(
                f"Added InventoryDropRequest for {item_type_id} from entity {self.entity_id}"
            )
