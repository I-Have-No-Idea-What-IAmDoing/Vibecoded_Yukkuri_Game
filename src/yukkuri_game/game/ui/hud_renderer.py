import pygame
from ...engine.ecs import World
from ..components import Selectable
from ..yukkuri_components import YukkuriStats, ItemStats, AIState
from pygame_gui.windows import UIMessageWindow

class HudRenderer:
    """
    Handles updating the visual state of the HUD.

    Attributes:
        layout (HudLayout): The layout component.
        gm (GameManager): The GameManager instance.
        world (World): The ECS World instance.
        fps (float): The current FPS value to display.
    """
    def __init__(self, layout, game_manager, world: World):
        """
        Initializes the HudRenderer.

        Args:
            layout: The HudLayout component.
            game_manager: The GameManager instance.
            world: The ECS World instance.
        """
        self.layout = layout
        self.gm = game_manager
        self.world = world
        self.fps = 0.0

    def update(self, dt: float, selected_entity: int, show_debug: bool) -> None:
        """
        Updates all HUD elements with current game data.

        Args:
            dt: Delta time.
            selected_entity: The ID of the selected entity.
            show_debug: Whether to show debug information.
        """
        # Update Top Bar
        self.layout.money_label.set_text(f"Money: ${self.gm.money}")

        minutes = int(self.gm.time_elapsed / 60)
        seconds = int(self.gm.time_elapsed % 60)
        self.layout.time_label.set_text(f"Time: {minutes:02d}:{seconds:02d}")

        # Update Selection Window
        if self.layout.selection_window and selected_entity != -1:
            self._update_stats_display(selected_entity)

        # Update Debug Window
        if show_debug:
            self._update_debug_window(dt)

    def _update_stats_display(self, selected_entity: int) -> None:
        """
        Updates the stats display for the selected entity.
        """
        text = "Unknown"
        stats = self.world.get_component(selected_entity, YukkuriStats)
        if stats:
            ai_state = self.world.get_component(selected_entity, AIState)
            action = ai_state.current_action if ai_state else "None"
            text = (f"<b>Name:</b> {stats.name}<br>"
                    f"<b>Hunger:</b> {int(stats.hunger)}<br>"
                    f"<b>Happiness:</b> {int(stats.happiness)}<br>"
                    f"<b>Health:</b> {int(stats.health)}<br>"
                    f"<b>Badges:</b> {stats.badges}<br>"
                    f"<b>Action:</b> {action}")
        else:
            istats = self.world.get_component(selected_entity, ItemStats)
            if istats:
                text = f"<b>Item:</b> {istats.name}<br><b>Val:</b> {istats.cost}"

        if self.layout.info_label:
            self.layout.info_label.set_text(text)

    def _update_debug_window(self, dt: float) -> None:
        """
        Updates the debug window with performance stats.
        """
        if not self.layout.debug_window or not self.layout.debug_text_box:
            return

        entity_count = len(self.world._entities) # Accessing private _entities for debug

        debug_text = (
            f"<b>FPS:</b> {self.fps:.2f}<br>"
            f"<b>Entities:</b> {entity_count}<br>"
            f"<b>Money:</b> {self.gm.money}<br>"
            f"<b>Time Scale:</b> {self.gm.time_scale if hasattr(self.gm, 'time_scale') else 'N/A'}<br>"
        )

        self.layout.debug_text_box.set_text(debug_text)

    def show_error(self, message: str) -> None:
        """
        Displays an error message in a popup window.

        Args:
            message: The error message to display.
        """
        UIMessageWindow(
            rect=pygame.Rect((self.layout.width - 400) // 2, (self.layout.height - 250) // 2, 400, 250),
            html_message=message,
            manager=self.layout.manager,
            window_title="Error"
        )
