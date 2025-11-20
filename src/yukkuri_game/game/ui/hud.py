import pygame
import pygame_gui
from pygame_gui.elements import UIPanel, UILabel, UIButton, UIWindow
from pygame_gui.core import ObjectID
from ...engine.ecs import World
from ..components import Selectable, Transform
from ..yukkuri_components import YukkuriStats, ItemStats

class HUD:
    def __init__(self, ui_manager, game_manager, world, factory):
        self.manager = ui_manager
        self.gm = game_manager
        self.world = world
        self.factory = factory

        self.width = 1280
        self.height = 720

        # Top Bar
        self.top_panel = UIPanel(
            relative_rect=pygame.Rect(0, 0, self.width, 50),
            manager=self.manager
        )

        self.money_label = UILabel(
            relative_rect=pygame.Rect(10, 10, 200, 30),
            text=f"Money: ${self.gm.money}",
            manager=self.manager,
            container=self.top_panel
        )

        self.save_btn = UIButton(
            relative_rect=pygame.Rect(self.width - 220, 10, 100, 30),
            text="Save",
            manager=self.manager,
            container=self.top_panel
        )

        self.load_btn = UIButton(
            relative_rect=pygame.Rect(self.width - 110, 10, 100, 30),
            text="Load",
            manager=self.manager,
            container=self.top_panel
        )

        # Time Controls
        self.time_label = UILabel(
            relative_rect=pygame.Rect(220, 10, 150, 30),
            text="Time: 00:00",
            manager=self.manager,
            container=self.top_panel
        )

        self.pause_btn = UIButton(
            relative_rect=pygame.Rect(380, 10, 80, 30),
            text="Pause",
            manager=self.manager,
            container=self.top_panel
        )

        self.speed_btn = UIButton(
            relative_rect=pygame.Rect(470, 10, 80, 30),
            text="1x",
            manager=self.manager,
            container=self.top_panel
        )

        # Bottom Bar (Shop/Actions)
        self.bottom_panel = UIPanel(
            relative_rect=pygame.Rect(0, self.height - 100, self.width, 100),
            manager=self.manager
        )

        self.add_reimu_btn = UIButton(
            relative_rect=pygame.Rect(10, 10, 120, 40),
            text="Buy Reimu ($100)",
            manager=self.manager,
            container=self.bottom_panel
        )

        self.add_cookie_btn = UIButton(
            relative_rect=pygame.Rect(140, 10, 120, 40),
            text="Buy Cookie ($10)",
            manager=self.manager,
            container=self.bottom_panel
        )

        # Selection Panel
        self.selection_window = None
        self.selected_entity = -1

    def update(self, dt):
        self.money_label.set_text(f"Money: ${self.gm.money}")

        minutes = int(self.gm.time_elapsed / 60)
        seconds = int(self.gm.time_elapsed % 60)
        self.time_label.set_text(f"Time: {minutes:02d}:{seconds:02d}")

        # Check selection
        selected = self.world.get_entities_with(Selectable)
        current_selected = -1
        for ent in selected:
            sel = self.world.get_component(ent, Selectable)
            if sel.selected:
                current_selected = ent
                break

        if current_selected != self.selected_entity:
            self.selected_entity = current_selected
            self.update_selection_window()

        if self.selection_window and self.selected_entity != -1:
            self.update_stats_display()

    def update_selection_window(self):
        if self.selection_window:
            self.selection_window.kill()
            self.selection_window = None
            self.sell_btn = None
            self.train_btn = None

        if self.selected_entity != -1:
            self.selection_window = UIWindow(
                rect=pygame.Rect(self.width - 300, 60, 280, 400),
                manager=self.manager,
                window_display_title="Entity Info"
            )

            self.info_label = UILabel(
                relative_rect=pygame.Rect(10, 10, 240, 200),
                text="",
                manager=self.manager,
                container=self.selection_window
            )

            # Actions for Yukkuri
            if self.world.has_component(self.selected_entity, YukkuriStats):
                self.sell_btn = UIButton(
                    relative_rect=pygame.Rect(10, 220, 240, 40),
                    text="Sell",
                    manager=self.manager,
                    container=self.selection_window
                )
                self.train_btn = UIButton(
                    relative_rect=pygame.Rect(10, 270, 240, 40),
                    text="Train (+Badge)",
                    manager=self.manager,
                    container=self.selection_window
                )

    def update_stats_display(self):
        text = "Unknown"
        stats = self.world.get_component(self.selected_entity, YukkuriStats)
        if stats:
            text = (f"Name: {stats.name}\n"
                    f"Hunger: {int(stats.hunger)}\n"
                    f"Happiness: {int(stats.happiness)}\n"
                    f"Health: {int(stats.health)}\n"
                    f"Badges: {stats.badges}\n"
                    f"Action: {self.world.get_component(self.selected_entity, 'AIState').current_action if self.world.has_component(self.selected_entity, 'AIState') else 'None'}") # Fix AIState access
        else:
            istats = self.world.get_component(self.selected_entity, ItemStats)
            if istats:
                text = f"Item: {istats.name}\nVal: {istats.cost}"

        self.info_label.set_text(text)

    def process_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.save_btn:
                self.gm.save_game()
            elif event.ui_element == self.load_btn:
                self.gm.load_game()
            elif event.ui_element == self.pause_btn:
                # We need to toggle pause in GameLoop, but HUD doesn't have direct access to GameLoop instance easily
                # But GameLoop updates HUD.
                # We can emit an event or use a callback. For MVP, let's assume game_manager can handle or we pass a callback.
                # Actually HUD is initialized in YukkuriGame.setup.
                # We can pass a callback in __init__.
                if hasattr(self, 'toggle_pause_callback'):
                    self.toggle_pause_callback()

            elif event.ui_element == self.speed_btn:
                if hasattr(self, 'cycle_speed_callback'):
                    self.cycle_speed_callback()

            elif event.ui_element == self.add_reimu_btn:
                if self.gm.money >= 100:
                    # Enable placement mode instead of instant spawn
                    if hasattr(self, 'start_placement_callback'):
                        self.start_placement_callback("reimu", 100, "yukkuri")

            elif event.ui_element == self.add_cookie_btn:
                if self.gm.money >= 10:
                    if hasattr(self, 'start_placement_callback'):
                        self.start_placement_callback("cookie", 10, "item")
            elif hasattr(self, 'sell_btn') and event.ui_element == self.sell_btn:
                self.gm.sell_yukkuri(self.selected_entity)
                self.selected_entity = -1
                if self.selection_window:
                    self.selection_window.kill()
                    self.selection_window = None
            elif hasattr(self, 'train_btn') and event.ui_element == self.train_btn:
                stats = self.world.get_component(self.selected_entity, YukkuriStats)
                if stats:
                    stats.badges += 1
                    stats.happiness += 10
