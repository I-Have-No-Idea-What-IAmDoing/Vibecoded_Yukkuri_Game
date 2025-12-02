"""
Module for rendering the HUD overlay.
"""
import pygame
from typing import TYPE_CHECKING, List
from ...engine.ecs import World
from ..components import Transform
from ..yukkuri_components import YukkuriStats, ItemStats, AIState, RelationshipRegistry, Personality, EmotionalState, Skills
from ..services import InputService, EconomyService, TimeService
from ..skill_service import SkillService
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
    def __init__(self, layout: 'HudLayout', world: World):
        """
        Initializes the HudRenderer.

        Args:
            layout (HudLayout): The HudLayout component.
            world (World): The ECS World instance.
        """
        self.layout = layout
        self.world = world
        self.fps = 0.0

    def update(self, dt: float, selected_entities: List[int], show_debug: bool) -> None:
        """
        Updates all HUD elements with current game data.

        Args:
            dt (float): Delta time.
            selected_entities (list[int]): The IDs of the selected entities.
            show_debug (bool): Whether to show debug information.

        Returns:
            None
        """
        economy = self.world.services.get(EconomyService)
        time_service = self.world.services.try_get(TimeService)

        # Update Top Bar
        if self.layout.money_label:
            self.layout.money_label.set_text(f"Money: ${economy.get_money()}")

        time_elapsed = time_service.time_elapsed if time_service else 0.0
        minutes = int(time_elapsed / 60)
        seconds = int(time_elapsed % 60)
        if self.layout.time_label:
            self.layout.time_label.set_text(f"Time: {minutes:02d}:{seconds:02d}")

        # Update Selection Window
        if self.layout.selection_window and selected_entities:
            self._update_stats_display(selected_entities)

        # Update Debug Window
        if show_debug:
            self._update_debug_window(dt)
            if selected_entities and len(selected_entities) == 1:
                self._draw_relationship_lines(selected_entities[0])

        # Update Hover Tooltip
        self._update_hover_tooltip()

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
        my_trans = self.world.get_component(selected_entity, Transform)
        registry = self.world.get_component(selected_entity, RelationshipRegistry)

        if not my_trans or not registry:
            return

        screen = pygame.display.get_surface()
        if not screen:
            return

        for other_id, rel_data in registry.relationships.items():
            if not self.world.entity_exists(other_id):
                continue

            other_trans = self.world.get_component(other_id, Transform)
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

            pygame.draw.line(screen, color, (my_trans.x, my_trans.y), (other_trans.x, other_trans.y), width)

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

        self.layout.update_hover_tooltip(text, input_service.hovered_entity_pos)

    def _update_stats_display(self, selected_entities: List[int]) -> None:
        """
        Updates the stats display for the selected entity.

        Args:
            selected_entities (list[int]): The IDs of the selected entities.

        Returns:
            None
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

            for eid in selected_entities:
                ystats = self.world.get_component(eid, YukkuriStats)
                emotional = self.world.get_component(eid, EmotionalState)
                if ystats:
                    yukkuris_count += 1
                    total_hp += ystats.health
                    total_hunger += ystats.hunger
                    if emotional:
                        total_happiness += emotional.happiness

                    total_value += ystats.calculate_value(emotional)

                    breed = ystats.type_id.capitalize()
                    yukkuri_breeds[breed] = yukkuri_breeds.get(breed, 0) + 1

                else:
                    istats = self.world.get_component(eid, ItemStats)
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
                    breed_str = ", ".join([f"{k}: {v}" for k, v in yukkuri_breeds.items()])
                    summary_lines.append(f"Yukkuris: {yukkuris_count} ({breed_str}) {stats_str}")
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
            stats = self.world.get_component(selected_entity, YukkuriStats)
            emotional = self.world.get_component(selected_entity, EmotionalState)

            if stats:
                ai_state = self.world.get_component(selected_entity, AIState)
                action = ai_state.current_action if ai_state else "None"

                # Personality & Relationships
                pers = self.world.get_component(selected_entity, Personality)
                rel_reg = self.world.get_component(selected_entity, RelationshipRegistry)

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
                text = (f"<b>Name:</b> {stats.name}<br>"
                        f"<b>Type:</b> {stats.type_id}<br>"
                        f"<b>Traits:</b> {traits_str}<br>"
                        f"<b>Mood:</b> {mood_str}<br>"
                        f"<br>"
                        f"<b>Health:</b> {int(stats.health)}<br>"
                        f"<b>Hunger:</b> {int(stats.hunger)}<br>"
                        f"<b>Happiness:</b> {happiness}<br>"
                        f"<b>Stress:</b> {stress}<br>"
                        f"<b>Badges:</b> {stats.badges}<br>"
                        f"<b>Action:</b> {action}")

                if pers and pers.axis:
                    text += "<br><br><b>Personality Axis:</b>"
                    text += f"<br> Kindness: {pers.axis.kindness}"
                    text += f"<br> Energy: {pers.axis.energy}"
                    text += f"<br> Bravery: {pers.axis.bravery}"
                    text += f"<br> Greed: {pers.axis.greed}"

        # Skills Text
        skills_text = ""
        skills_comp = self.world.get_component(selected_entity, Skills)
        skill_service = self.world.services.try_get(SkillService)

        if skills_comp and skill_service:
            # Sort skills by passion or name?
            # Proposal: "Display Skill Level, XP Bar, and Passion Icon (flame)."
            # We don't have icons easily here in text box, but we can use emojis.

            for skill_id, skill_data in skills_comp.skills.items():
                defn = skill_service.skill_definitions.get(skill_id, {})
                name = defn.get("name", skill_id.capitalize())

                passion_icon = ""
                if skill_data.passion > 2.0: passion_icon = "🔥"
                elif skill_data.passion > 1.2: passion_icon = "✨"
                elif skill_data.passion < 0.8: passion_icon = "💤"

                skills_text += f"<br><b>{name}</b> {passion_icon}"
                skills_text += f"<br> Lvl: {skill_data.level} (XP: {int(skill_data.xp)})"

        if self.layout.skills_label:
            if self.layout.skills_label.html_text != skills_text:
                self.layout.skills_label.set_text(skills_text)

                # Check height update
                new_height = self.layout.skills_label.rect.height
                if self.layout.skills_scroll_container:
                     self.layout.skills_scroll_container.set_scrollable_area_dimensions((270, new_height))

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
                     sorted_rels = sorted(rel_reg.relationships.items(), key=lambda x: x[1].last_update, reverse=True)
                     count = 0
                     for other_id, rel_data in sorted_rels:
                         if count >= 3: break
                         count += 1
                         other_stats = self.world.get_component(other_id, YukkuriStats)
                         name = other_stats.name if other_stats else f"ID {other_id}"

                         text += f"<br> <b>{name}</b> (Aff: {rel_data.affinity:.1f})"
                         # Show top headlines
                         if rel_data.core_buffer:
                             text += "<br>  Core:"
                             for h in rel_data.core_buffer[-2:]: # Last 2
                                 text += f"<br>   [{h.event_type}] Imp:{h.importance:.1f} {'(L)' if h.is_locked else ''}"
                         if rel_data.trivial_buffer:
                             text += "<br>  Trivial:"
                             for h in rel_data.trivial_buffer[-2:]: # Last 2
                                 text += f"<br>   [{h.event_type}] Imp:{h.importance:.1f}"

            else:
                istats = self.world.get_component(selected_entity, ItemStats)
                if istats:
                    text = f"<b>Item:</b> {istats.name}<br><b>Val:</b> {istats.cost}"

        if self.layout.info_label:
            # Only update if text actually changed
            if self.layout.info_label.html_text != text:
                # Get current dimensions
                old_height = self.layout.info_label.rect.height

                self.layout.info_label.set_text(text)

                # Check if dimensions changed
                new_height = self.layout.info_label.rect.height

                if old_height != new_height and self.layout.info_scroll_container:
                    # Save scroll position
                    scroll_pos = 0.0
                    if self.layout.info_scroll_container.vert_scroll_bar:
                        scroll_pos = self.layout.info_scroll_container.vert_scroll_bar.start_percentage

                    # Update scrolling container dimensions
                    # We set width to 270 (matching creation width) and height to new content height
                    self.layout.info_scroll_container.set_scrollable_area_dimensions((270, new_height))

                    # Restore scroll position
                    if self.layout.info_scroll_container.vert_scroll_bar:
                        self.layout.info_scroll_container.vert_scroll_bar.set_scroll_from_start_percentage(scroll_pos)

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

        # Accessing private _entities for debug
        try:
            entity_count = len(self.world.get_all_entities())
        except:
            entity_count = 0

        economy = self.world.services.get(EconomyService)

        debug_text = (
            f"<b>FPS:</b> {self.fps:.2f}<br>"
            f"<b>Entities:</b> {entity_count}<br>"
            f"<b>Money:</b> {economy.get_money()}<br>"
            f"<b>Time Scale:</b> N/A<br>"
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
