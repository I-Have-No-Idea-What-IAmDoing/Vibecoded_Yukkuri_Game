"""
Module defining the HUD logic.
"""

from typing import TYPE_CHECKING, Any

import pygame
import pygame_gui

if TYPE_CHECKING:
    pass
from ...engine.ecs import World
from ...engine.event_bus import EventBus
from ...engine.events import InventoryChangedEvent
from ...engine.resource_manager import ResourceManager
from ..events import (
    ContextMenuRequestedEvent,
    EntitySelectedEvent,
    GamePausedEvent,
    InventoryItemActionEvent,
    InventoryViewRequestedEvent,
    LogMessageEvent,
)
from ..systems.ai_debug_renderer import AIDebugRenderer
from ..systems.navigation_debug_renderer import NavigationDebugRenderer
from ..systems.physics_debug_renderer import PhysicsDebugRenderer
from ..components import AIState, YukkuriStats
from .context_menu import ContextMenu
from .developer_console import DeveloperConsole
from .hud_events import HudEvents

# Import new components
from .hud_layout import HudLayout
from .hud_renderer import HudRenderer
from .inventory_panel import InventoryPanel


class HUD:
    """
    The Heads-Up Display (HUD) system for the game.

    Manages the UI layout, event handling, and rendering of game status and entity information.
    This class acts as a facade, delegating responsibilities to specialized sub-components:
    HudLayout, HudEvents, and HudRenderer.

    Attributes:
        manager (pygame_gui.UIManager): The UI manager.
        world (World): The ECS world.
        event_bus (EventBus): The event bus.
        width (int): Screen width.
        height (int): Screen height.
        layout (HudLayout): The layout manager.
        events (HudEvents): The event handler.
        renderer (HudRenderer): The renderer.
        context_menu (ContextMenu): The context menu.
        inventory_panel (InventoryPanel): The inventory panel.
        selected_entities (list[int]): List of selected entity IDs.
        show_debug (bool): Whether debug info is shown.
        fps (float): Current FPS.
        lighting_debug (bool): Whether lighting debug is enabled.
        navigation_debug_renderer (NavigationDebugRenderer | None): Debug renderer for navigation.
        ai_debug_renderer (AIDebugRenderer | None): Debug renderer for AI.
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
        self.scene: Any = None
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
        self.events.hud = self

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
        self.physics_debug_renderer: PhysicsDebugRenderer | None = None
        self.developer_console: DeveloperConsole | None = DeveloperConsole(
            self.manager, self.world, self
        )
        self.world.services.register(self, HUD)

        self.log_history: list[LogMessageEvent] = [
            LogMessageEvent(
                message="Welcome to Yukkuri Game!",
                color=(255, 255, 255),
                channel="General",
            )
        ]
        self.current_log_filter: str = "All"
        self.is_log_frozen: bool = False

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

        if self.developer_console:
            self.developer_console.close()

        self.world.services.unregister(HUD)

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
        # Always append to in-memory history
        self.log_history.append(event)

        # Do not update UI if log feed is frozen
        if self.is_log_frozen:
            return

        # Debug channels are only shown in debug mode (show_debug)
        if event.channel in ("AI", "Physics") and not self.show_debug:
            return

        if self.layout.log_box:
            if (
                self.current_log_filter == "All"
                or event.channel == self.current_log_filter
            ):
                # Convert color tuple to hex string
                hex_color = "#{:02x}{:02x}{:02x}".format(*event.color)
                message = f"<font color='{hex_color}'>{event.message}</font><br>"
                self.layout.log_box.append_html_text(message)

                self._scroll_log_box_to_bottom()

    def on_entity_selected(self, event: EntitySelectedEvent) -> None:
        """
        Handles the EntitySelectedEvent.

        Args:
            event (EntitySelectedEvent): The entity selected event.
        """
        # Clear is_inspected flag on previous entities
        for ent, ai in self.world.get_components(AIState).items():
            ai.is_inspected = False

        self.selected_entities = list(event.entity_ids)
        self.events.set_selected_entities(self.selected_entities)
        self._update_selection_window_layout()

        # Set is_inspected flag on newly selected entities
        for entity_id in self.selected_entities:
            ai = self.world.try_get_component(entity_id, AIState)
            if ai:
                ai.is_inspected = True

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
        from ..components import InventoryComponent

        inv = self.world.try_get_component(event.entity_id, InventoryComponent)
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
        from ..components import InventoryDropRequest

        if event.action == "drop":
            # Add drop request component - will be processed by InventorySystem
            req = InventoryDropRequest(
                item_type_id=event.item_type_id, quantity=event.quantity
            )
            if getattr(self.world, "_updating", False):
                self.world.commands.add_component(event.entity_id, req)
            else:
                self.world.add_component(event.entity_id, req)

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

        # Draw physics debug overlay
        if (
            self.physics_debug_renderer
            and self.physics_debug_renderer.enabled
        ):
            self.physics_debug_renderer.render(screen, self.world)

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
            self.layout.create_debug_window(self.world)
        else:
            self.layout.close_debug_window()

        self._rebuild_log_box_content()

    def toggle_console(self) -> None:
        """
        Toggles the visibility of the developer console.
        """
        if self.developer_console:
            if self.developer_console.is_open():
                self.developer_console.close()
            else:
                self.developer_console.open()

    def toggle_lighting_debug(self) -> None:
        """Toggles lighting debug visuals."""
        self.lighting_debug = not self.lighting_debug

    def toggle_navigation_debug(self) -> None:
        """Toggles navigation debug visuals (clusters, paths, steering)."""
        if self.navigation_debug_renderer:
            self.navigation_debug_renderer.toggle()

    def init_navigation_debug(self) -> None:
        """
        Initializes the navigation debug renderer.
        """
        self.navigation_debug_renderer = NavigationDebugRenderer(self.world)

    def init_ai_debug(self) -> None:
        """
        Initializes the AI debug renderer.
        """
        self.ai_debug_renderer = AIDebugRenderer(self.world)

    def toggle_ai_debug(self) -> None:
        """Toggles AI debug visuals."""
        if self.ai_debug_renderer:
            self.ai_debug_renderer.toggle()

    def init_physics_debug(self) -> None:
        """
        Initializes the physics debug renderer.
        """
        from ..systems.physics_debug_renderer import PhysicsDebugRenderer
        self.physics_debug_renderer = PhysicsDebugRenderer(self.world)

    def toggle_physics_debug(self) -> None:
        """Toggles physics debug visuals."""
        if self.physics_debug_renderer:
            self.physics_debug_renderer.toggle()

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
        # Handle Developer Console Events
        if (
            self.developer_console
            and self.developer_console.process_event(event)
        ):
            return

        # Handle ECS Inspector Events
        if (
            self.layout.ecs_inspector
            and self.layout.ecs_inspector.process_event(event)
        ):
            return

        # Handle System Profiler Events
        if (
            self.layout.system_profiler
            and self.layout.system_profiler.process_event(event)
        ):
            return

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

    def set_log_filter(self, channel: str) -> None:
        """Sets the active log category filter and rebuilds text."""
        self.current_log_filter = channel
        if not self.is_log_frozen:
            self._rebuild_log_box_content()

    def toggle_log_freeze(self) -> None:
        """Toggles scroll freeze state for the log feed."""
        self.is_log_frozen = not self.is_log_frozen
        if self.layout.log_freeze_btn:
            btn = self.layout.log_freeze_btn
            if self.is_log_frozen:
                getattr(btn, "select")()
                btn.set_text("Frozen")
            else:
                getattr(btn, "unselect")()
                btn.set_text("Freeze")

        if not self.is_log_frozen:
            self._rebuild_log_box_content()

    def _rebuild_log_box_content(self) -> None:
        """Clears and reprints matching logs from buffer history."""
        if not self.layout.log_box:
            return
        self.layout.log_box.set_text("")
        for event in self.log_history:
            # Debug channels are only shown in debug mode (show_debug)
            if event.channel in ("AI", "Physics") and not self.show_debug:
                continue

            if (
                self.current_log_filter == "All"
                or event.channel == self.current_log_filter
            ):
                hex_color = "#{:02x}{:02x}{:02x}".format(*event.color)
                message = (
                    f"<font color='{hex_color}'>{event.message}</font><br>"
                )
                self.layout.log_box.append_html_text(message)
        self._scroll_log_box_to_bottom()

    def _scroll_log_box_to_bottom(self) -> None:
        """Scrolls the log box viewport to the bottom."""
        if (
            self.layout.log_box
            and hasattr(self.layout.log_box, "scroll_bar")
            and self.layout.log_box.scroll_bar
        ):
            self.layout.log_box.scroll_bar.scroll_position = (
                self.layout.log_box.scroll_bar.scrollable_height
            )
            self.layout.log_box.scroll_bar.update(0)
