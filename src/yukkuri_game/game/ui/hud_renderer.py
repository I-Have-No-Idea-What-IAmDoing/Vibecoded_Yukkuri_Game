"""
Module for rendering the HUD overlay.
"""

import pygame
from typing import TYPE_CHECKING
from ...engine.ecs import World
from ..components import (
    AIState,
    EmotionalState,
    InventoryComponent,
    ItemStats,
    Needs,
    Personality,
    RelationshipRegistry,
    Skills,
    YukkuriStats,
)
from yukkuri_game.engine.components import (
    Transform,
)
from ..services import EconomyService, InputService
from yukkuri_game.engine.services.time_service import TimeService
from ..skill_service import SkillService
from ...engine.resource_manager import ResourceManager
from ...config import GameConfig
from pygame_gui.windows import UIMessageWindow

if TYPE_CHECKING:
    from .hud_layout import HudLayout


class HudRenderer:
    """
    Handles updating the visual state of the HUD.

    Attributes:
        layout (HudLayout): The layout component.
        world (World): The ECS World instance.
        fps (float): The current FPS value to display.
    """

    def __init__(self, layout: "HudLayout", world: World):
        """
        Initializes the HudRenderer.

        Args:
            layout (HudLayout): The HudLayout component.
            world (World): The ECS World instance.
        """
        self.layout = layout
        self.world = world
        self.fps = 0.0
        self.selection_update_timer = 0.0
        self.SELECTION_UPDATE_INTERVAL = 0.1

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
        self._update_top_bar()
        self._update_time_display()
        self.selection_update_timer += dt
        if self.selection_update_timer >= self.SELECTION_UPDATE_INTERVAL:
            self._update_selection_info(selected_entities)
            self.selection_update_timer = 0.0
        self._update_debug_info(dt, selected_entities, show_debug)
        self._update_hover_tooltip()
        self._update_buy_button_highlights()

    def _update_top_bar(self) -> None:
        """Updates the top bar (Money)."""
        economy = self.world.services.get(EconomyService)
        if self.layout.money_label:
            self.layout.money_label.set_text(f"Money: ${economy.money}")

    def _update_time_display(self) -> None:
        """
        Updates the time display with day, time, and current game speed.
        Formats time as HH:MM and adds a speed multiplier suffix if not 1.0x.
        """
        time_service = self.world.services.try_get(TimeService)
        if time_service:
            day = time_service.day
            hour_of_day = time_service.hour_of_day
            hours = int(hour_of_day)
            minutes = int((hour_of_day % 1) * 60)
            speed = time_service.game_speed
        else:
            day = 1
            hours = 0
            minutes = 0
            speed = 1.0

        if self.layout.time_label:
            speed_str = f" ({speed:.1f}x)" if speed != 1.0 else ""
            self.layout.time_label.set_text(
                f"Day {day} - {hours:02d}:{minutes:02d}{speed_str}"
            )

    def _update_selection_info(self, selected_entities: list[int]) -> None:
        """Updates the selection window info."""
        if self.layout.entity_info_panel and selected_entities:
            self._update_stats_display(selected_entities)
            self._update_skills_display(selected_entities)
            self._update_ai_display(selected_entities)

    def _update_debug_info(
        self, dt: float, selected_entities: list[int], show_debug: bool
    ) -> None:
        """Updates debug window and lines."""
        if show_debug:
            self._update_debug_window(dt)
            if selected_entities and len(selected_entities) == 1:
                self._draw_relationship_lines(selected_entities[0])

    def draw(self, screen: pygame.Surface) -> None:
        """
        Draws HUD overlays directly to the screen.

        Args:
            screen (pygame.Surface): The screen surface to draw on.
        """
        self._draw_selection_box(screen)

    def _draw_selection_box(self, screen: pygame.Surface) -> None:
        """
        Draws the selection box if dragging.

        Args:
            screen (pygame.Surface): The screen surface.
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
            pygame.draw.rect(screen, (0, 255, 0), rect, 1)

    def _draw_relationship_lines(self, selected_entity: int) -> None:
        """
        Draws debug lines connecting the selected entity to others it has a relationship with.
        Color indicates affinity.

        Args:
            selected_entity (int): The ID of the selected entity.
        """
        my_trans = self.world.try_get_component(selected_entity, Transform)
        registry = self.world.try_get_component(selected_entity, RelationshipRegistry)

        if not my_trans or not registry:
            return

        screen = pygame.display.get_surface()
        if not screen:
            return

        for other_id, rel_data in registry.relationships.items():
            if not self.world.entity_exists(other_id):
                continue

            other_trans = self.world.try_get_component(other_id, Transform)
            if not other_trans:
                continue

            # Determine color based on affinity
            # Red (-100) -> Grey (0) -> Green (100)
            affinity = rel_data.affinity
            color = (128, 128, 128)
            width = 2

            if affinity > 0:
                # Green gradient
                intensity = int(min(255, 50 + affinity * 2))
                color = (50, intensity, 50)
                width = max(2, int(affinity / 20))
            elif affinity < 0:
                # Red gradient
                intensity = int(min(255, 50 + abs(affinity) * 2))
                color = (intensity, 50, 50)
                width = max(2, int(abs(affinity) / 20))

            pygame.draw.line(
                screen,
                color,
                (my_trans.x, my_trans.y),
                (other_trans.x, other_trans.y),
                width,
            )

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
            ystats = self.world.try_get_component(hovered_id, YukkuriStats)
            needs = self.world.try_get_component(hovered_id, Needs)
            if ystats and needs:
                text = f"<b>{ystats.name}</b><br>HP: {int(needs.health)}"
            else:
                istats = self.world.try_get_component(hovered_id, ItemStats)
                if istats:
                    text = f"<b>{istats.name}</b>"

        self.layout.update_hover_tooltip(text, input_service.hovered_entity_pos)

    def _update_stats_display(self, selected_entities: list[int]) -> None:
        """
        Updates the stats display for the selected entity.

        Args:
            selected_entities (list[int]): The IDs of the selected entities.
        """
        text = "Unknown"

        if len(selected_entities) > 1:
            yukkuris_count = 0
            items_count = 0
            total_hp = 0.0
            total_hunger = 0.0
            total_happiness = 0.0
            total_value = 0
            yukkuri_breeds: dict[str, int] = {}
            items_val = 0

            config = self.world.services.try_get(GameConfig)
            stats_config = config.rules.stats if config else None

            for eid in selected_entities:
                ystats = self.world.try_get_component(eid, YukkuriStats)
                needs = self.world.try_get_component(eid, Needs)
                emotional = self.world.try_get_component(eid, EmotionalState)
                if ystats and needs:
                    yukkuris_count += 1
                    total_hp += needs.health
                    total_hunger += needs.hunger
                    if emotional:
                        total_happiness += emotional.happiness

                    total_value += ystats.calculate_value(
                        needs, emotional, stats_config=stats_config
                    )

                    breed = ystats.type_id.capitalize()
                    yukkuri_breeds[breed] = yukkuri_breeds.get(breed, 0) + 1

                else:
                    istats = self.world.try_get_component(eid, ItemStats)
                    if istats:
                        items_count += 1
                        items_val += istats.cost

            summary_lines = [f"<b>Selected: {len(selected_entities)} entities</b>"]

            if yukkuris_count > 0:
                avg_hp = int(total_hp / yukkuris_count)
                avg_hunger = int(total_hunger / yukkuris_count)
                avg_happy = int(total_happiness / yukkuris_count)

                stats_str = f"(Avg HP: {avg_hp}, Avg Hunger: {avg_hunger}, Avg Happy: {avg_happy})"

                # Breed breakdown if only yukkuris are selected
                if items_count == 0 and len(yukkuri_breeds) > 0:
                    breed_str = ", ".join(
                        [f"{k}: {v}" for k, v in yukkuri_breeds.items()]
                    )
                    summary_lines.append(
                        f"Yukkuris: {yukkuris_count} ({breed_str}) {stats_str}"
                    )
                else:
                    summary_lines.append(f"Yukkuris: {yukkuris_count} {stats_str}")

            if items_count > 0:
                avg_val = int(items_val / items_count) if items_count > 0 else 0
                summary_lines.append(f"Items: {items_count} (Avg Value: {avg_val})")

            grand_total = total_value + items_val
            summary_lines.append(f"<br><b>Total value if sold: {grand_total:,}￥</b>")

            text = "<br>".join(summary_lines)

        elif len(selected_entities) == 1:
            selected_entity = selected_entities[0]
            stats = self.world.try_get_component(selected_entity, YukkuriStats)
            needs = self.world.try_get_component(selected_entity, Needs)
            emotional = self.world.try_get_component(selected_entity, EmotionalState)

            if stats and needs:
                ai_state = self.world.try_get_component(selected_entity, AIState)
                action = ai_state.current_action if ai_state else "None"

                # Personality & Relationships
                pers = self.world.try_get_component(selected_entity, Personality)
                rel_reg = self.world.try_get_component(
                    selected_entity, RelationshipRegistry
                )

                traits_str = "None"
                mood_str = "Neutral"

                happiness = 0
                stress = 0

                if emotional:
                    mood_str = emotional.get_dominant_emotion()
                    happiness = int(emotional.happiness)
                    stress = int(emotional.stress)

                if pers:
                    if pers.traits:
                        traits_str = ", ".join(list(pers.traits))

                # Format
                text = (
                    f"<b>Name:</b> {stats.name}<br>"
                    f"<b>Type:</b> {stats.type_id}<br>"
                    f"<b>Traits:</b> {traits_str}<br>"
                    f"<b>Mood:</b> {mood_str}<br>"
                    f"<br>"
                    f"<b>Health:</b> {int(needs.health)}<br>"
                    f"<b>Hunger:</b> {int(needs.hunger)}<br>"
                    f"<b>Happiness:</b> {happiness}<br>"
                    f"<b>Stress:</b> {stress}<br>"
                    f"<b>Tastebuds Spoiled:</b> {stats.tastebud_spoiled:.1f}<br>"
                    f"<b>Badges:</b> {stats.badges}<br>"
                    f"<b>Agility:</b> {stats.agility:.1f}<br>"
                    f"<b>Action:</b> {action}"
                )

                if pers and pers.axis:
                    text += "<br><br><b>Personality Axis:</b>"
                    text += f"<br> Kindness: {pers.axis.kindness}"
                    text += f"<br> Energy: {pers.axis.energy}"
                    text += f"<br> Bravery: {pers.axis.bravery}"
                    text += f"<br> Greed: {pers.axis.greed}"

                if rel_reg:
                    if rel_reg.family_group_id:
                        text += f"<br><b>Family ID:</b> {rel_reg.family_group_id}"

                    # Memory Inspector (Debug)
                    if self.layout.debug_window and self.layout.debug_window.visible:
                        text += "<br><br><b>Memory Inspector:</b>"
                        if not rel_reg.relationships:
                            text += "<br> No relationships."
                        else:
                            # Just show memory for the first few relationships or most recent
                            # Sort by affinity or recent?
                            sorted_rels = sorted(
                                rel_reg.relationships.items(),
                                key=lambda x: x[1].last_update,
                                reverse=True,
                            )
                            count = 0
                            for other_id, rel_data in sorted_rels:
                                if count >= 3:
                                    break
                                count += 1
                                other_stats = self.world.try_get_component(
                                    other_id, YukkuriStats
                                )
                                name = (
                                    other_stats.name
                                    if other_stats
                                    else f"ID {other_id}"
                                )

                                text += (
                                    f"<br> <b>{name}</b> (Aff: {rel_data.affinity:.1f})"
                                )
                                # Show top headlines
                                if rel_data.core_buffer:
                                    text += "<br>  Core:"
                                    for h in list(rel_data.core_buffer)[-2:]:  # Last 2
                                        text += f"<br>   [{h.event_type}] Imp:{h.importance:.1f} {'(L)' if h.is_locked else ''}"
                                if rel_data.trivial_buffer:
                                    text += "<br>  Trivial:"
                                    for h in list(rel_data.trivial_buffer)[-2:]:  # Last 2
                                        text += f"<br>   [{h.event_type}] Imp:{h.importance:.1f}"

            else:
                istats = self.world.try_get_component(selected_entity, ItemStats)
                if istats:
                    text = f"<b>Item:</b> {istats.name}<br><b>Val:</b> {istats.cost}"

            # --- Inventory Display (Debug) ---
            inventory = self.world.try_get_component(selected_entity, InventoryComponent)
            if inventory and inventory.items:
                text += "<br><br><b>Inventory:</b>"
                rm = self.world.services.try_get(ResourceManager)

                for item in inventory.items:
                    item_name = item.item_type_id
                    if rm:
                        item_type = rm.item_types.get(item.item_type_id)
                        if item_type:
                            item_name = item_type.name

                    text += f"<br> {item_name} x{item.quantity}"
            elif inventory:
                text += "<br><br><b>Inventory:</b> Empty"

        if self.layout.entity_info_panel:
            self.layout.entity_info_panel.update_stats(text)

    def _update_skills_display(self, selected_entities: list[int]) -> None:
        """
        Updates the skills display for the selected entity.

        Args:
            selected_entities (list[int]): The IDs of the selected entities.
        """
        if not self.layout.entity_info_panel:
            return

        text = ""
        if len(selected_entities) == 1:
            eid = selected_entities[0]
            skills = self.world.try_get_component(eid, Skills)

            if skills:
                skill_service = self.world.services.try_get(SkillService)
                # Need definitions to get names and required xp

                text_lines = []
                for skill_id, state in skills.states.items():
                    name = skill_id.capitalize()

                    if skill_service and skill_id in skill_service.skill_definitions:
                        defn = skill_service.skill_definitions[skill_id]
                        name = defn.name

                    level = state.level
                    xp = state.current_xp

                    req_xp = 100.0 * (1.5**level)
                    if skill_service:
                        req_xp = skill_service.get_required_xp(level)

                    percentage = int((xp / req_xp) * 100) if req_xp > 0 else 0

                    passion_icon = ""
                    if state.passion > 1.5:
                        passion_icon = "🔥"
                    elif state.passion > 1.0:
                        passion_icon = "✨"
                    elif state.passion < 1.0:
                        passion_icon = "❄️"

                    text_lines.append(f"<b>{name}</b> {passion_icon}")
                    text_lines.append(
                        f" Lv. {level} | XP: {int(xp)}/{int(req_xp)} ({percentage}%)"
                    )
                    text_lines.append("")  # Spacer

                if not text_lines:
                    text = "No skills learned."
                else:
                    text = "<br>".join(text_lines)
            else:
                text = "No skills component."
        else:
            text = "Multiple selection not supported for Skills."

        self.layout.entity_info_panel.update_skills(text)

    def _update_ai_display(self, selected_entities: list[int]) -> None:
        """
        Updates the AI introspection tab for the selected entity.

        Args:
            selected_entities (list[int]): The IDs of the selected entities.
        """
        if not self.layout.entity_info_panel:
            return

        text = ""
        if len(selected_entities) == 1:
            eid = selected_entities[0]
            ai = self.world.try_get_component(eid, AIState)
            if ai:
                breakdown = ai.last_utility_breakdown
                if not breakdown:
                    text = "Waiting for AI calculations..."
                else:
                    active_action = breakdown.get("active_action")
                    sorted_actions = breakdown.get("sorted_actions", [])

                    lines = []
                    for name, data in sorted_actions:
                        score = data.get("final_score", 0.0)
                        is_active = (name == active_action)

                        if is_active:
                            header = (
                                f"<b>▶ [ACTIVE] <font color='#00FFFF'>"
                                f"{name} (Score: {score:.4f})</font></b>"
                            )
                        else:
                            if score > 0.6:
                                color = "#00FF66"
                            elif score > 0.01:
                                color = "#FFCC00"
                            else:
                                color = "#808080"
                            header = (
                                f"<b><font color='{color}'>"
                                f"{name} (Score: {score:.4f})</font></b>"
                            )
                        lines.append(header)

                        for cons in data.get("considerations", []):
                            cons_name = cons.get("name", "")
                            raw_val = cons.get("raw_value", 0.0)
                            norm_val = cons.get("normalized_value", 0.0)
                            curve = cons.get("curve", "linear")
                            params = cons.get("params", {})
                            cons_score = cons.get("score", 0.0)

                            param_strs = []
                            for pk, pv in params.items():
                                if isinstance(pv, float):
                                    param_strs.append(f"{pk}={pv:.2f}")
                                else:
                                    param_strs.append(f"{pk}={pv}")
                            param_str = ", ".join(param_strs)

                            if cons_score <= 0.01:
                                cons_str = (
                                    f"&nbsp;&nbsp;• <font color='#FF3333'>"
                                    f"<b>[REJECTED]</b> {cons_name}: "
                                    f"{raw_val:.2f} -> {norm_val:.2f} "
                                    f"({curve}: {param_str}) "
                                    f"score: {cons_score:.3f}</font>"
                                )
                            else:
                                cons_str = (
                                    f"&nbsp;&nbsp;• {cons_name}: "
                                    f"{raw_val:.2f} -> {norm_val:.2f} "
                                    f"({curve}: {param_str}) "
                                    f"score: {cons_score:.3f}"
                                )
                            lines.append(cons_str)
                        lines.append("")  # Spacer between actions

                    text = "<br>".join(lines)
            else:
                text = "No AI component found for this entity."
        else:
            text = "Multiple selection not supported for AI Introspection."

        self.layout.entity_info_panel.update_ai(text)

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

        # Get entity count for debug display (fallback to 0 if world is in inconsistent state)
        try:
            entity_count = len(self.world.get_all_entities())
        except (AttributeError, KeyError):
            entity_count = 0

        economy = self.world.services.get(EconomyService)
        time_service = self.world.services.try_get(TimeService)

        time_scale_str = "N/A"
        if time_service:
            time_scale_str = f"{time_service.scale}x @ {time_service.game_speed}x speed"

        debug_text = (
            f"<b>FPS:</b> {self.fps:.2f}<br>"
            f"<b>Entities:</b> {entity_count}<br>"
            f"<b>Money:</b> {economy.money}<br>"
            f"<b>Time Scale:</b> {time_scale_str}<br>"
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
            rect=pygame.Rect(
                (self.layout.width - 400) // 2,
                (self.layout.height - 250) // 2,
                400,
                250,
            ),
            html_message=message,
            manager=self.layout.manager,
            window_title="Error",
        )

    def _update_buy_button_highlights(self) -> None:
        """
        Updates buy button visual states based on current placement mode.

        Highlights the active buy button when in placement mode, and
        clears selection when not placing.
        """
        input_service = self.world.services.try_get(InputService)
        if not input_service:
            return

        is_placing = input_service.is_placing
        current_type = input_service.place_type
        is_cleaning = input_service.is_cleaning

        # Update buy buttons
        for btn, data in self.layout.buy_buttons.items():
            if is_placing and data["type_id"] == current_type:
                btn.select()  # type: ignore[no-untyped-call]
            else:
                btn.unselect()  # type: ignore[no-untyped-call]

        # Update clean button
        if self.layout.clean_btn:
            if is_cleaning:
                self.layout.clean_btn.select()  # type: ignore[no-untyped-call]
            else:
                self.layout.clean_btn.unselect()  # type: ignore[no-untyped-call]
