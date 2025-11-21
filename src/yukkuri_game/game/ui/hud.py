import pygame
from typing import Optional, Callable, Any, Dict, TYPE_CHECKING
import pygame_gui
from ...engine.ecs import World
from ..components import Selectable, Transform
from ..yukkuri_components import YukkuriStats

# Import new components
from .hud_layout import HudLayout
from .hud_events import HudEvents
from .hud_renderer import HudRenderer

if TYPE_CHECKING:
    from ..game_manager import GameManager
    from ..entity_factory import EntityFactory

class HUD:
    """
    The Heads-Up Display (HUD) system for the game.

    Manages the UI layout, event handling, and rendering of game status and entity information.
    This class acts as a facade, delegating responsibilities to specialized sub-components:
    HudLayout, HudEvents, and HudRenderer.

    Attributes:
        manager (pygame_gui.UIManager): The UI manager instance.
        gm (GameManager): The game manager instance.
        world (World): The ECS World instance.
        factory (EntityFactory): The entity factory.
        width (int): The width of the screen.
        height (int): The height of the screen.
        layout (HudLayout): Manages the arrangement of UI elements.
        events (HudEvents): Manages UI event handling.
        renderer (HudRenderer): Manages the updating of UI element content.
        selected_entity (int): The ID of the currently selected entity.
        show_debug (bool): Whether to show the debug window.
        fps (float): The current frames per second.
    """

    def __init__(self, ui_manager: pygame_gui.UIManager, world: World):
        """
        Initializes the HUD.

        Args:
            ui_manager: The pygame_gui UIManager.
            world: The ECS World instance.
        """
        self.manager = ui_manager
        self.world = world
        from ..game_manager import GameManager
        from ..entity_factory import EntityFactory
        self.gm = world.services.get(GameManager)
        self.factory = world.services.get(EntityFactory)

        self.width = 1280
        self.height = 720

        # Callbacks
        self.toggle_pause_callback: Optional[Callable[[], None]] = None
        self.cycle_speed_callback: Optional[Callable[[], None]] = None
        self.start_placement_callback: Optional[Callable[[str, int, str], None]] = None

        # Initialize Components
        self.layout = HudLayout(self.manager, self.width, self.height)

        # Events component needs callbacks, which are set later.
        # We can pass a lambda or method that resolves them dynamically,
        # or update the events component when callbacks are set.
        # For now, we pass a dict that we can update.
        self._callbacks_store: Dict[str, Optional[Callable[..., Any]]] = {}
        self.events = HudEvents(self.layout, self.gm, self._callbacks_store) # type: ignore[arg-type]

        self.renderer = HudRenderer(self.layout, self.gm, self.world)

        # State
        self.selected_entity = -1
        self.show_debug = False
        self.fps = 0.0

    # Delegate property access for backward compatibility/convenience
    @property
    def money_label(self) -> Optional[pygame_gui.elements.UILabel]:
        """Returns the money label UI element."""
        return self.layout.money_label

    @property
    def time_label(self) -> Optional[pygame_gui.elements.UILabel]:
        """Returns the time label UI element."""
        return self.layout.time_label

    @property
    def save_btn(self) -> Optional[pygame_gui.elements.UIButton]:
        """Returns the save button UI element."""
        return self.layout.save_btn

    @property
    def load_btn(self) -> Optional[pygame_gui.elements.UIButton]:
        """Returns the load button UI element."""
        return self.layout.load_btn

    @property
    def pause_btn(self) -> Optional[pygame_gui.elements.UIButton]:
        """Returns the pause button UI element."""
        return self.layout.pause_btn

    @property
    def speed_btn(self) -> Optional[pygame_gui.elements.UIButton]:
        """Returns the speed button UI element."""
        return self.layout.speed_btn

    @property
    def add_reimu_btn(self) -> Optional[pygame_gui.elements.UIButton]:
        """Returns the add Reimu button UI element."""
        return self.layout.add_reimu_btn

    @property
    def add_cookie_btn(self) -> Optional[pygame_gui.elements.UIButton]:
        """Returns the add cookie button UI element."""
        return self.layout.add_cookie_btn

    @property
    def selection_window(self) -> Optional[pygame_gui.elements.UIWindow]:
        """Returns the selection window UI element."""
        return self.layout.selection_window

    @property
    def debug_window(self) -> Optional[pygame_gui.elements.UIWindow]:
        """Returns the debug window UI element."""
        return self.layout.debug_window

    def update(self, dt: float) -> None:
        """
        Updates the HUD state.

        Checks for selection changes and delegates rendering updates to HudRenderer.

        Args:
            dt: Delta time since last frame.
        """
        self.renderer.fps = self.fps # Sync FPS

        # Check selection logic
        current_selected = self._get_current_selected_entity()

        if current_selected != self.selected_entity:
            self.selected_entity = current_selected
            self.events.set_selected_entity(self.selected_entity)
            self._update_selection_window_layout()

        # Update Layout if needed (e.g. if selection changed, we already did it)

        # Render Updates
        self.renderer.update(dt, self.selected_entity, self.show_debug)

    def _get_current_selected_entity(self) -> int:
        """
        Finds the currently selected entity in the ECS world.

        Returns:
            int: The ID of the selected entity, or -1 if none are selected.
        """
        selected = self.world.get_entities_with(Selectable)
        for ent in selected:
            sel = self.world.get_component(ent, Selectable)
            if sel and sel.selected:
                return ent
        return -1

    def _update_selection_window_layout(self) -> None:
        """
        Updates the layout of the selection window based on the selected entity type.
        """
        if self.selected_entity == -1:
            self.layout.close_selection_window()
        else:
            has_stats = self.world.has_component(self.selected_entity, YukkuriStats)
            self.layout.create_selection_window(has_stats)

    def toggle_debug(self) -> None:
        """
        Toggles the visibility of the debug window.
        """
        self.show_debug = not self.show_debug
        if self.show_debug:
            self.layout.create_debug_window()
        else:
            self.layout.close_debug_window()

    def show_error(self, message: str) -> None:
        """
        Displays an error message (currently logged via renderer).

        Args:
            message: The error message to display.
        """
        self.renderer.show_error(message)

    def process_event(self, event: pygame.event.Event) -> None:
        """
        Processes UI events.

        Updates internal callback references and delegates to HudEvents.

        Args:
            event: The Pygame event to process.
        """
        # Update callbacks dict before processing (in case they were set after init)
        self._callbacks_store['toggle_pause'] = self.toggle_pause_callback
        self._callbacks_store['cycle_speed'] = self.cycle_speed_callback
        self._callbacks_store['start_placement'] = self.start_placement_callback

        # Add a special callback for training which was inline before
        self._callbacks_store['train_entity'] = self._train_entity

        handled = self.events.process_event(event)

        # Check if event processing resulted in state changes we need to react to immediately
        # For example, if sold, we need to clear selection
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if hasattr(self.layout, 'sell_btn') and event.ui_element == self.layout.sell_btn:
                # The event handler called sell, we need to clear selection locally
                self.selected_entity = -1
                self.layout.close_selection_window()
                self.events.set_selected_entity(-1)

    def _train_entity(self, entity_id: int) -> None:
        """
        Internal callback to train a Yukkuri.

        Args:
            entity_id: The ID of the entity to train.
        """
        stats = self.world.get_component(entity_id, YukkuriStats)
        if stats:
            stats.badges += 1
            stats.happiness += 10
