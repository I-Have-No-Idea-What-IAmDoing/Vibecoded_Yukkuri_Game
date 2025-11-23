import pygame
from typing import TYPE_CHECKING
from ...engine.ecs import World
from ..components import Selectable
from ..yukkuri_components import YukkuriStats, ItemStats, AIState
from ..services import InputService
from pygame_gui.windows import UIMessageWindow

if TYPE_CHECKING:
    from .hud_layout import HudLayout
    from ..game_manager import GameManager

class HudRenderer:
    """
    Handles updating the visual state of the HUD.

    Attributes:
        layout (HudLayout): The layout component.
        gm (GameManager): The GameManager instance.
        world (World): The ECS World instance.
        fps (float): The current FPS value to display.
    """
    def __init__(self, layout: 'HudLayout', game_manager: 'GameManager', world: World):
        """
        Initializes the HudRenderer.

        Args:
            layout (HudLayout): The HudLayout component.
            game_manager (GameManager): The GameManager instance.
            world (World): The ECS World instance.
        """
        self.layout = layout
        self.gm = game_manager
        self.world = world
        self.fps = 0.0

    def update(self, dt: float, selected_entities: list[int], show_debug: bool) -> None:
        """
        Updates all HUD elements with current game data.

        Args:
            dt (float): Delta time.
            selected_entities (list[int]): The IDs of the selected entities.
            show_debug (bool): Whether to show debug information.

        Returns:
            None
        """
        # Update Top Bar
        if self.layout.money_label:
            self.layout.money_label.set_text(f"Money: ${self.gm.money}")

        minutes = int(self.gm.time_elapsed / 60)
        seconds = int(self.gm.time_elapsed % 60)
        if self.layout.time_label:
            self.layout.time_label.set_text(f"Time: {minutes:02d}:{seconds:02d}")

        # Update Selection Window
        if self.layout.selection_window and selected_entities:
            self._update_stats_display(selected_entities)

        # Update Debug Window
        if show_debug:
            self._update_debug_window(dt)

        # Update Hover Tooltip
        self._update_hover_tooltip()

        # Draw Selection Box
        self._draw_selection_box()

    def _draw_selection_box(self) -> None:
        """
        Draws the selection box if dragging.

        Returns:
            None
        """
        input_service = self.world.services.try_get(InputService)
        if input_service and input_service.is_dragging:
            start = input_service.drag_start_pos
            curr = input_service.drag_current_pos

            x = min(start[0], curr[0])
            y = min(start[1], curr[1])
            w = abs(start[0] - curr[0])
            h = abs(start[1] - curr[1])

            rect = pygame.Rect(x, y, w, h)

            # Draw directly to the display surface
            screen = pygame.display.get_surface()
            if screen:
                pygame.draw.rect(screen, (0, 255, 0), rect, 1)

    def _update_hover_tooltip(self) -> None:
        """
        Updates the hover tooltip based on input service state.

        Returns:
            None
        """
        input_service = self.world.services.try_get(InputService)
        if not input_service:
            return

        hovered_id = input_service.hovered_entity_id

        text = ""
        if hovered_id != -1 and self.world.entity_exists(hovered_id):
             # Get minimal stats
            ystats = self.world.get_component(hovered_id, YukkuriStats)
            if ystats:
                text = f"<b>{ystats.name}</b><br>HP: {int(ystats.health)}"
            else:
                istats = self.world.get_component(hovered_id, ItemStats)
                if istats:
                    text = f"<b>{istats.name}</b>"

        # Optimization: Check if text or position significantly changed?
        # Actually, input_service.hovered_entity_pos changes every mouse move.
        # But text only changes if entity or stats change.
        # Let HudLayout handle optimization if needed, or just pass it.
        self.layout.update_hover_tooltip(text, input_service.hovered_entity_pos)

    def _update_stats_display(self, selected_entities: list[int]) -> None:
        """
        Updates the stats display for the selected entity.

        Args:
            selected_entities (list[int]): The IDs of the selected entities.

        Returns:
            None
        """
        text = "Unknown"

        if len(selected_entities) > 1:
            yukkuris = 0
            items = 0
            for eid in selected_entities:
                if self.world.has_component(eid, YukkuriStats):
                    yukkuris += 1
                elif self.world.has_component(eid, ItemStats):
                    items += 1

            summary = []
            if yukkuris > 0:
                summary.append(f"{yukkuris} Yukkuri{'s' if yukkuris > 1 else ''}")
            if items > 0:
                summary.append(f"{items} Item{'s' if items > 1 else ''}")

            text = f"<b>Selection:</b><br>" + ", ".join(summary)
        elif len(selected_entities) == 1:
            selected_entity = selected_entities[0]
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

        Args:
            dt (float): Delta time.

        Returns:
            None
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
            message (str): The error message to display.

        Returns:
            None
        """
        UIMessageWindow(
            rect=pygame.Rect((self.layout.width - 400) // 2, (self.layout.height - 250) // 2, 400, 250),
            html_message=message,
            manager=self.layout.manager,
            window_title="Error"
        )
