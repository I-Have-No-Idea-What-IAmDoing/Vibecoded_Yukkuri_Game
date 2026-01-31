"""
Module defining the HUD logic.
"""

import pygame
import pygame_gui
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..ai.navigation_service import NavigationService
    from ..camera import Camera
from ...engine.ecs import World
from ...engine.event_bus import EventBus
from ..events import (
    EntitySelectedEvent,
    GamePausedEvent,
    LogMessageEvent,
    ContextMenuRequestedEvent,
    InventoryViewRequestedEvent,
    InventoryItemActionEvent,
)
from ...engine.events import InventoryChangedEvent
from ..yukkuri_components import YukkuriStats
from ...engine.resource_manager import ResourceManager

# Import new components
from .hud_layout import HudLayout
from .hud_events import HudEvents
from .hud_renderer import HudRenderer
from .context_menu import ContextMenu
from .inventory_panel import InventoryPanel
from ..systems.navigation_debug_renderer import NavigationDebugRenderer
from ..systems.ai_debug_renderer import AIDebugRenderer


class HUD:
    """
    The Heads-Up Display (HUD) system for the game.

    Manages the UI layout, event handling, and rendering of game status and entity information.
    This class acts as a facade, delegating responsibilities to specialized sub-components:
    HudLayout, HudEvents, and HudRenderer.
    """

    def __init__(self, ui_manager: pygame_gui.UIManager, world: World):
        """
        Initializes the HUD.

        Args:
            ui_manager (pygame_gui.UIManager): The pygame_gui UIManager.
            world (World): The ECS World instance.
        """
        self.manager = ui_manager
        self.world = world
        self.event_bus = world.services.get(EventBus)
        rm = world.services.get(ResourceManager)

        self.width = 1280
        self.height = 720

        self.layout = HudLayout(
            self.manager, self.width, self.height, rm.yukkuri_types, rm.item_types
        )

        self.events = HudEvents(
            self.layout, self.world, self.event_bus, self.show_error
        )

        self.renderer = HudRenderer(self.layout, self.world)

        self.context_menu = ContextMenu(self.manager)

        # Inventory Panel (with event_bus for event-driven actions)
        self.inventory_panel = InventoryPanel(self.manager, self.world, self.event_bus)

        self.selected_entities: list[int] = []
        self.show_debug = False
        self.fps = 0.0
        self.fps_timer = 0.0
        self.lighting_debug = False
        self.navigation_debug_renderer: NavigationDebugRenderer | None = None
        self.ai_debug_renderer: AIDebugRenderer | None = None

        self.event_bus.subscribe(EntitySelectedEvent, self.on_entity_selected)
        self.event_bus.subscribe(GamePausedEvent, self.on_game_paused)
        self.event_bus.subscribe(LogMessageEvent, self.on_log_message)
        self.event_bus.subscribe(
            ContextMenuRequestedEvent, self.on_context_menu_requested
        )
        self.event_bus.subscribe(
            InventoryViewRequestedEvent, self.on_inventory_view_requested
        )
        self.event_bus.subscribe(InventoryChangedEvent, self.on_inventory_changed)
        self.event_bus.subscribe(
            InventoryItemActionEvent, self.on_inventory_item_action
        )

    def cleanup(self) -> None:
        """
        Unsubscribes all event listeners.
        Must be called when the HUD is destroyed to prevent memory leaks.
        """
        self.event_bus.unsubscribe(EntitySelectedEvent, self.on_entity_selected)
        self.event_bus.unsubscribe(GamePausedEvent, self.on_game_paused)
        self.event_bus.unsubscribe(LogMessageEvent, self.on_log_message)
        self.event_bus.unsubscribe(
            ContextMenuRequestedEvent, self.on_context_menu_requested
        )
        self.event_bus.unsubscribe(
            InventoryViewRequestedEvent, self.on_inventory_view_requested
        )
        self.event_bus.unsubscribe(InventoryChangedEvent, self.on_inventory_changed)
        self.event_bus.unsubscribe(
            InventoryItemActionEvent, self.on_inventory_item_action
        )

        if self.inventory_panel:
            self.inventory_panel.close()

    def resize(self, width: int, height: int) -> None:
        """
        Resizes the HUD.

        Args:
            width (int): The new width.
            height (int): The new height.
        """
        self.width = width
        self.height = height
        self.manager.set_window_resolution((width, height))
        self.layout.resize(width, height)

    def on_log_message(self, event: LogMessageEvent) -> None:
        """
        Handles LogMessageEvent.

        Args:
            event (LogMessageEvent): The event data.
        """
        if self.layout.log_box:
            # Convert color tuple to hex string
            hex_color = "#{:02x}{:02x}{:02x}".format(*event.color)
            message = f"<font color='{hex_color}'>{event.message}</font><br>"
            self.layout.log_box.append_html_text(message)

            # Scroll to bottom
            if (
                hasattr(self.layout.log_box, "scroll_bar")
                and self.layout.log_box.scroll_bar
            ):
                self.layout.log_box.scroll_bar.scroll_position = (
                    self.layout.log_box.scroll_bar.scrollable_height
                )
                self.layout.log_box.scroll_bar.update(0)

    def on_entity_selected(self, event: EntitySelectedEvent) -> None:
        """
        Handles the EntitySelectedEvent.

        Args:
            event (EntitySelectedEvent): The entity selected event.
        """
        self.selected_entities = list(event.entity_ids)
        self.events.set_selected_entities(self.selected_entities)
        self._update_selection_window_layout()

    def on_game_paused(self, event: GamePausedEvent) -> None:
        """
        Handles the GamePausedEvent.

        Args:
            event (GamePausedEvent): The game paused event.
        """
        if self.layout.pause_btn:
            self.layout.pause_btn.set_text("Resume" if event.paused else "Pause")

    def on_context_menu_requested(self, event: ContextMenuRequestedEvent) -> None:
        """
        Handles ContextMenuRequestedEvent.

        Args:
            event (ContextMenuRequestedEvent): The context menu requested event.
        """
        options = []

        # Check entity capabilities to determine options
        from ..inventory_component import InventoryComponent

        inv = self.world.get_component(event.entity_id, InventoryComponent)
        if inv:
            item_count = len(inv.items)
            label = f"Inventory ({item_count})" if item_count > 0 else "Inventory"
            options.append((label, "view_inventory"))

        # Standard options
        options.append(("Inspect", "inspect"))

        if options:
            self.context_menu.show(
                event.position,
                options,
                self.on_context_menu_action,
                (event.entity_id, event.position),  # Pass position for inventory panel
            )

    def on_context_menu_action(
        self, action_id: str, target_data: tuple[int, tuple[int, int]]
    ) -> None:
        """
        Callback for context menu actions. Uses event-driven approach.

        Args:
            action_id (str): The ID of the selected action.
            target_data (tuple[int, tuple[int, int]]): The target entity ID and position.
        """
        entity_id, position = target_data
        if action_id == "view_inventory":
            # Publish event instead of direct method call for loose coupling
            self.event_bus.publish(InventoryViewRequestedEvent(entity_id, position))
        elif action_id == "inspect":
            self.event_bus.publish(EntitySelectedEvent((entity_id,)))

    def on_inventory_view_requested(self, event: InventoryViewRequestedEvent) -> None:
        """
        Handles InventoryViewRequestedEvent to show inventory panel.

        Args:
            event (InventoryViewRequestedEvent): The inventory view requested event.
        """
        position = event.position if event.position else (100, 100)
        self.inventory_panel.show(event.entity_id, position)

    def on_inventory_changed(self, event: InventoryChangedEvent) -> None:
        """
        Handles InventoryChangedEvent to auto-refresh inventory panel.

        Args:
            event (InventoryChangedEvent): The inventory changed event.
        """
        # Only refresh if the changed entity is currently being viewed
        if (
            self.inventory_panel.entity_id is not None
            and self.inventory_panel.entity_id == event.entity_id
        ):
            self.inventory_panel.refresh()

    def on_inventory_item_action(self, event: InventoryItemActionEvent) -> None:
        """
        Handles InventoryItemActionEvent for drop/use/transfer actions.

        Args:
            event (InventoryItemActionEvent): The inventory item action event.
        """
        from ..inventory_component import InventoryDropRequest

        if event.action == "drop":
            # Add drop request component - will be processed by InventorySystem
            self.world.add_component(
                event.entity_id,
                InventoryDropRequest(
                    item_type_id=event.item_type_id, quantity=event.quantity
                ),
            )

    def update(self, dt: float) -> None:
        """
        Updates the HUD state.

        Checks for selection changes and delegates rendering updates to HudRenderer.

        Args:
            dt (float): Delta time since last frame in seconds.
        """
        self.renderer.fps = self.fps  # Sync FPS

        # Selection is now handled via events, so we don't need to poll

        # Render Updates
        self.renderer.update(dt, self.selected_entities, self.show_debug)

    def draw(self, screen: pygame.Surface) -> None:
        """
        Draws the HUD overlays.

        Args:
            screen (pygame.Surface): The screen surface to draw on.
        """
        self.renderer.draw(screen)

        # Draw navigation debug overlay
        if self.navigation_debug_renderer and self.navigation_debug_renderer.enabled:
            self.navigation_debug_renderer.render(screen, self.world)

        # Draw AI debug overlay
        if self.ai_debug_renderer and self.ai_debug_renderer.enabled:
            self.ai_debug_renderer.render(screen, self.world)

    def _update_selection_window_layout(self) -> None:
        """
        Updates the layout of the selection window based on the selected entity type.
        """
        if not self.selected_entities:
            self.layout.close_selection_window()
        elif len(self.selected_entities) == 1:
            entity_id = self.selected_entities[0]
            has_stats = self.world.has_component(entity_id, YukkuriStats)
            self.layout.create_selection_window(has_stats, 1)
        else:
            all_yukkuris = all(
                self.world.has_component(eid, YukkuriStats)
                for eid in self.selected_entities
            )
            self.layout.create_selection_window(
                all_yukkuris, len(self.selected_entities)
            )

    def toggle_debug(self) -> None:
        """
        Toggles the visibility of the debug window.
        """
        self.show_debug = not self.show_debug
        if self.show_debug:
            self.layout.create_debug_window()
        else:
            self.layout.close_debug_window()

    def toggle_lighting_debug(self) -> None:
        """Toggles lighting debug visuals."""
        self.lighting_debug = not self.lighting_debug

    def toggle_navigation_debug(self) -> None:
        """Toggles navigation debug visuals (clusters, paths, steering)."""
        if self.navigation_debug_renderer:
            self.navigation_debug_renderer.toggle()

    def init_navigation_debug(
        self, nav_service: "NavigationService", camera: "Camera"
    ) -> None:
        """
        Initializes the navigation debug renderer.

        Args:
            nav_service (NavigationService): The navigation service.
            camera (Camera): The game camera.
        """

        self.navigation_debug_renderer = NavigationDebugRenderer(nav_service, camera)

    def init_ai_debug(self, camera: "Camera") -> None:
        """
        Initializes the AI debug renderer.

        Args:
            camera (Camera): The game camera.
        """
        self.ai_debug_renderer = AIDebugRenderer(camera)

    def toggle_ai_debug(self) -> None:
        """Toggles AI debug visuals."""
        if self.ai_debug_renderer:
            self.ai_debug_renderer.toggle()

    def show_error(self, message: str) -> None:
        """
        Displays an error message (currently logged via renderer).

        Args:
            message (str): The error message to display.
        """
        self.renderer.show_error(message)

    def process_event(self, event: pygame.event.Event) -> None:
        """
        Processes UI events.

        Delegates to HudEvents.

        Args:
            event (pygame.event.Event): The Pygame event to process.
        """
        # Handle Context Menu Events
        if self.context_menu.process_event(event):
            return

        # Handle Inventory Panel Events
        if self.inventory_panel.process_event(event):
            return

        self.events.process_event(event)

        # Check if event processing resulted in state changes we need to react to immediately
        # For example, if sold, we need to clear selection
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if (
                hasattr(self.layout, "sell_btn")
                and event.ui_element == self.layout.sell_btn
            ):
                # The event handler called sell, we need to clear selection locally
                self.selected_entities = []
                self.layout.close_selection_window()
                self.events.set_selected_entities([])
