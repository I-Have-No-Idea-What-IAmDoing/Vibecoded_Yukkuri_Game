import pygame
from typing import Any
from src.engine.ecs import Entity, EntityManager
from src.engine.components import Stats, AIComponent, Identity
from src.utils.loader import game_data

class Interface:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.font = pygame.font.SysFont("Arial", 16)
        self.small_font = pygame.font.SysFont("Arial", 12)
        self.config = game_data.configs["ui"]

        # Parse config color
        c_str = self.config.get("panel_color", "50, 50, 50, 200").split(",")
        self.panel_color = tuple(map(int, c_str)) if len(c_str) >= 3 else (50, 50, 50, 200)

    def draw_panel(self, rect, color=None):
        s = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
        s.fill(color or self.panel_color)
        self.screen.blit(s, (rect[0], rect[1]))

    def render_ui(self, state: Any, ecs: EntityManager):
        self.render_top_bar(state)
        self.render_selected_entity_info(state, ecs)

    def render_top_bar(self, state: Any):
        w, h = self.screen.get_size()
        self.draw_panel((0, 0, w, 40))

        # Money
        money_text = self.font.render(f"Money: ${state.money}", True, (255, 215, 0))
        self.screen.blit(money_text, (20, 10))

        # Time
        days = state.day_count
        speed_str = f"{state.simulation_speed}x"
        if state.simulation_speed == 0: speed_str = "PAUSED"
        time_text = self.font.render(f"Day: {days} ({int(state.time_elapsed)}s) [{speed_str}]", True, (200, 200, 255))
        self.screen.blit(time_text, (200, 10))

        # Controls Hint
        hint_text = self.small_font.render("L-Click: Select | R-Click: Buy Food ($5) | S: Sell | T: Train", True, (150, 150, 150))
        self.screen.blit(hint_text, (w - 350, 12))

    def render_selected_entity_info(self, state: Any, ecs: EntityManager):
        if not state.selected_entity_id:
            return

        # Find entity
        entity = next((e for e in ecs.entities if e.id == state.selected_entity_id), None)
        if not entity:
            state.selected_entity_id = None
            return

        stats = entity.get_component(Stats)
        identity = entity.get_component(Identity)
        ai = entity.get_component(AIComponent)

        if not stats or not identity:
            return

        # Panel Background
        panel_w = 250
        panel_h = 300
        panel_x = self.screen.get_width() - panel_w - 20
        panel_y = 60

        self.draw_panel((panel_x, panel_y, panel_w, panel_h))

        y_off = 10
        x_off = 10

        # Name & Type
        name_text = self.font.render(f"{identity.name} ({identity.type_id})", True, (255, 255, 255))
        self.screen.blit(name_text, (panel_x + x_off, panel_y + y_off))
        y_off += 25

        # Stats
        stats_to_show = [
            ("Health", stats.health, stats.max_health),
            ("Hunger", stats.hunger, stats.max_hunger), # Show as bar
            ("Happiness", stats.happiness, stats.max_happiness),
            ("Energy", stats.energy, stats.max_energy),
            ("Clean", stats.cleanliness, stats.max_cleanliness)
        ]

        for label, val, max_val in stats_to_show:
            text = self.small_font.render(f"{label}: {int(val)}/{int(max_val)}", True, (200, 200, 200))
            self.screen.blit(text, (panel_x + x_off, panel_y + y_off))

            # Bar
            bar_w = 150
            bar_h = 8
            pct = max(0, min(1, val / max_val)) if max_val > 0 else 0

            # Hunger is inverse (good is 0) - Wait, usually hunger bar full = full stomach?
            # In my system 0 is full, 100 is starving. So drawing it...
            # If label is hunger, pct should be 1 - pct if we want "Fullness" bar.
            # Let's draw "Hunger" bar (Full bar = Starving).

            pygame.draw.rect(self.screen, (50, 0, 0), (panel_x + x_off, panel_y + y_off + 15, bar_w, bar_h))
            pygame.draw.rect(self.screen, (0, 200, 0) if label != "Hunger" else (200, 0, 0),
                             (panel_x + x_off, panel_y + y_off + 15, bar_w * pct, bar_h))

            y_off += 30

        # Age & Stage
        age_text = self.small_font.render(f"Age: {int(stats.age)}s ({stats.growth_stage})", True, (200, 200, 200))
        self.screen.blit(age_text, (panel_x + x_off, panel_y + y_off))
        y_off += 20

        # AI Status
        if ai:
            action = ai.current_action or "Idle"
            ai_text = self.small_font.render(f"Action: {action}", True, (200, 200, 255))
            self.screen.blit(ai_text, (panel_x + x_off, panel_y + y_off))
            y_off += 20

        # Quality Score
        qs_text = self.font.render(f"Quality: {int(stats.quality_score)}", True, (255, 215, 0))
        self.screen.blit(qs_text, (panel_x + x_off, panel_y + y_off))
        y_off += 25

        # Badges
        badge_text = self.small_font.render(f"Badges: {stats.badges}", True, (255, 100, 100))
        self.screen.blit(badge_text, (panel_x + x_off, panel_y + y_off))
