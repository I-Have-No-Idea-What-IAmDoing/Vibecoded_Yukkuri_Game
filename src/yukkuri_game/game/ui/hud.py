import pygame
import pygame_gui
from pygame_gui.elements import UIPanel, UILabel, UIButton, UIWindow, UITextBox
from pygame_gui.core import ObjectID
from pygame_gui.windows import UIMessageWindow
from ...engine.ecs import World
from ..components import Selectable, Transform
from ..yukkuri_components import YukkuriStats, ItemStats, AIState

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

        # Debug Overlay
        self.show_debug = False
        self.debug_window = None
        self.debug_text_box = None

    def update(self, dt):
        self.money_label.set_text(f"Money: ${self.gm.money}")

        minutes = int(self.gm.time_elapsed / 60)
        seconds = int(self.gm.time_elapsed % 60)
        self.time_label.set_text(f"Time: {minutes:02d}:{seconds:02d}")

        if self.show_debug:
            self.update_debug_window(dt)

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
            # Increased width to prevent text cutoff
            self.selection_window = UIWindow(
                rect=pygame.Rect(self.width - 350, 60, 330, 400),
                manager=self.manager,
                window_display_title="Entity Info",
                resizable=True
            )

            self.info_label = UITextBox(
                html_text="",
                relative_rect=pygame.Rect(10, 10, 290, 200),
                manager=self.manager,
                container=self.selection_window,
                anchors={'top': 'top', 'bottom': 'top', 'left': 'left', 'right': 'right'}
            )

            # Actions for Yukkuri
            if self.world.has_component(self.selected_entity, YukkuriStats):
                self.sell_btn = UIButton(
                    relative_rect=pygame.Rect(10, 220, 290, 40),
                    text="Sell",
                    manager=self.manager,
                    container=self.selection_window
                )
                self.train_btn = UIButton(
                    relative_rect=pygame.Rect(10, 270, 290, 40),
                    text="Train (+Badge)",
                    manager=self.manager,
                    container=self.selection_window
                )

    def update_stats_display(self):
        text = "Unknown"
        stats = self.world.get_component(self.selected_entity, YukkuriStats)
        if stats:
            ai_state = self.world.get_component(self.selected_entity, AIState)
            action = ai_state.current_action if ai_state else "None"
            text = (f"<b>Name:</b> {stats.name}<br>"
                    f"<b>Hunger:</b> {int(stats.hunger)}<br>"
                    f"<b>Happiness:</b> {int(stats.happiness)}<br>"
                    f"<b>Health:</b> {int(stats.health)}<br>"
                    f"<b>Badges:</b> {stats.badges}<br>"
                    f"<b>Action:</b> {action}")
        else:
            istats = self.world.get_component(self.selected_entity, ItemStats)
            if istats:
                text = f"<b>Item:</b> {istats.name}<br><b>Val:</b> {istats.cost}"

        self.info_label.set_text(text)

    def toggle_debug(self):
        self.show_debug = not self.show_debug
        if self.show_debug:
            self.create_debug_window()
        elif self.debug_window:
            self.debug_window.kill()
            self.debug_window = None

    def create_debug_window(self):
        if self.debug_window:
            self.debug_window.kill()

        self.debug_window = UIWindow(
            rect=pygame.Rect(10, 60, 300, 200),
            manager=self.manager,
            window_display_title="Debug Info",
            resizable=True
        )

        self.debug_text_box = UITextBox(
            html_text="Debug info...",
            relative_rect=pygame.Rect(10, 10, 260, 140),
            manager=self.manager,
            container=self.debug_window,
            anchors={'top': 'top', 'bottom': 'bottom', 'left': 'left', 'right': 'right'}
        )

    def update_debug_window(self, dt):
        if not self.debug_window or not self.debug_text_box:
            return

        # Gather debug info
        fps = self.gm.time_elapsed # Placeholder, need actual FPS
        entity_count = len(self.world.entities)

        # We can get FPS from clock if passed, but for now let's show what we have
        debug_text = (
            f"<b>Entities:</b> {entity_count}<br>"
            f"<b>Money:</b> {self.gm.money}<br>"
            f"<b>Time Scale:</b> {self.gm.time_scale if hasattr(self.gm, 'time_scale') else 'N/A'}<br>"
        )

        # If we have extra info passed from game loop, we could use it.
        # But since we are inside HUD update which is called from game loop,
        # we might need to pass fps separately.
        if hasattr(self, 'fps'):
             debug_text = f"<b>FPS:</b> {self.fps:.2f}<br>" + debug_text

        self.debug_text_box.set_text(debug_text)

    def show_error(self, message):
        UIMessageWindow(
            rect=pygame.Rect((self.width - 400) // 2, (self.height - 250) // 2, 400, 250),
            html_message=message,
            manager=self.manager,
            window_title="Error"
        )

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
