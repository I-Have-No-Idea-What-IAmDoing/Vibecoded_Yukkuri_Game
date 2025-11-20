import pygame
from typing import Optional
from pygame_gui import UIManager
from pygame_gui.elements import UIWindow, UITextBox, UIButton

from ...engine.ecs import World
from ..yukkuri_components import YukkuriStats, ItemStats, AIState
from ..components import Selectable

class SelectionWindow:
    """
    Manages the entity selection window in the HUD.
    """

    def __init__(self, manager: UIManager, width: int):
        """
        Args:
            manager: The pygame_gui UIManager.
            width: The screen width (used for positioning).
        """
        self.manager = manager
        self.width = width
        self.window: Optional[UIWindow] = None
        self.info_label: Optional[UITextBox] = None
        self.sell_btn: Optional[UIButton] = None
        self.train_btn: Optional[UIButton] = None
        self.current_entity: int = -1

    def show(self, entity_id: int, world: World):
        """
        Shows the selection window for the given entity.

        Args:
            entity_id: The ID of the entity to show info for.
            world: The ECS World to retrieve component data.
        """
        if self.window and self.current_entity == entity_id:
            return # Already showing this entity

        self.hide() # Close existing window if any

        self.current_entity = entity_id

        # Increased width to prevent text cutoff
        self.window = UIWindow(
            rect=pygame.Rect(self.width - 350, 60, 330, 400),
            manager=self.manager,
            window_display_title="Entity Info",
            resizable=True
        )

        self.info_label = UITextBox(
            html_text="",
            relative_rect=pygame.Rect(10, 10, 290, 200),
            manager=self.manager,
            container=self.window,
            anchors={'top': 'top', 'bottom': 'top', 'left': 'left', 'right': 'right'}
        )

        # Actions for Yukkuri
        if world.has_component(entity_id, YukkuriStats):
            self.sell_btn = UIButton(
                relative_rect=pygame.Rect(10, 220, 290, 40),
                text="Sell",
                manager=self.manager,
                container=self.window
            )
            self.train_btn = UIButton(
                relative_rect=pygame.Rect(10, 270, 290, 40),
                text="Train (+Badge)",
                manager=self.manager,
                container=self.window
            )

        self.update(world)

    def hide(self):
        """Closes the selection window."""
        if self.window:
            self.window.kill()
            self.window = None
            self.info_label = None
            self.sell_btn = None
            self.train_btn = None
            self.current_entity = -1

    def update(self, world: World):
        """
        Updates the content of the selection window.

        Args:
             world: The ECS World.
        """
        if not self.window or self.current_entity == -1:
            return

        # Check if entity still exists and is selected
        if not world.has_component(self.current_entity, Selectable):
             # Entity might have been destroyed or component removed
             self.hide()
             return

        sel = world.get_component(self.current_entity, Selectable)
        if not sel.selected:
             # No longer selected
             self.hide()
             return

        text = "Unknown"
        stats = world.get_component(self.current_entity, YukkuriStats)
        if stats:
            ai_state = world.get_component(self.current_entity, AIState)
            action = ai_state.current_action if ai_state else "None"
            text = (f"<b>Name:</b> {stats.name}<br>"
                    f"<b>Hunger:</b> {int(stats.hunger)}<br>"
                    f"<b>Happiness:</b> {int(stats.happiness)}<br>"
                    f"<b>Health:</b> {int(stats.health)}<br>"
                    f"<b>Badges:</b> {stats.badges}<br>"
                    f"<b>Action:</b> {action}")
        else:
            istats = world.get_component(self.current_entity, ItemStats)
            if istats:
                text = f"<b>Item:</b> {istats.name}<br><b>Val:</b> {istats.cost}"

        if self.info_label:
            self.info_label.set_text(text)

    def is_active(self) -> bool:
        return self.window is not None


class DebugWindow:
    """
    Manages the debug window.
    """
    def __init__(self, manager: UIManager):
        self.manager = manager
        self.window: Optional[UIWindow] = None
        self.text_box: Optional[UITextBox] = None
        self.visible = False

    def toggle(self):
        """Toggles visibility of the debug window."""
        self.visible = not self.visible
        if self.visible:
            self._create()
        else:
            self._destroy()

    def _create(self):
        if self.window:
            self.window.kill()

        self.window = UIWindow(
            rect=pygame.Rect(10, 60, 300, 200),
            manager=self.manager,
            window_display_title="Debug Info",
            resizable=True
        )

        self.text_box = UITextBox(
            html_text="Debug info...",
            relative_rect=pygame.Rect(10, 10, 260, 140),
            manager=self.manager,
            container=self.window,
            anchors={'top': 'top', 'bottom': 'bottom', 'left': 'left', 'right': 'right'}
        )

    def _destroy(self):
        if self.window:
            self.window.kill()
            self.window = None
            self.text_box = None

    def update(self, game_manager, entity_count: int, fps: float = 0.0):
        """
        Updates the debug info.

        Args:
            game_manager: The GameManager to get state from.
            entity_count: Number of entities.
            fps: Current FPS.
        """
        if not self.visible or not self.text_box:
            return

        debug_text = (
            f"<b>FPS:</b> {fps:.2f}<br>"
            f"<b>Entities:</b> {entity_count}<br>"
            f"<b>Money:</b> {game_manager.money}<br>"
            f"<b>Time Scale:</b> {game_manager.time_scale if hasattr(game_manager, 'time_scale') else 'N/A'}<br>"
        )

        self.text_box.set_text(debug_text)
