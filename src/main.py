import pygame as pg
import sys
import random
import json
from .yukkurrium import Yukkurrium
from .entities import Yukkuri, Item
from .ai import UtilityAIEngine
from .config import load_yukkuri_types, load_item_types

# Constants
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

class GameLoop:
    def __init__(self):
        pg.init()
        self.screen = pg.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pg.display.set_caption("Yukkuri Raising Game")
        self.clock = pg.time.Clock()
        self.font = pg.font.Font(None, 24)

        self.yukkurrium = Yukkurrium()
        self.ai_engine = UtilityAIEngine()

        self.yukkuri_types = load_yukkuri_types()
        self.item_types = load_item_types()

        self.camera_x = 0
        self.camera_y = 0
        self.zoom = 1.0

        self.player_currency = 1000
        self.selected_yukkuri = None
        self.item_to_place = None

        self.last_tick = pg.time.get_ticks()
        self.needs_decay_interval = 2000 # 2 seconds

        self.populate_yukkurrium()

    def populate_yukkurrium(self):
        """Adds initial Yukkuris and items for testing."""
        for _ in range(5): # Start with 5 for now
            y_type = random.choice(list(self.yukkuri_types.keys()))
            pos = (random.randint(100, SCREEN_WIDTH - 100), random.randint(100, SCREEN_HEIGHT - 100))
            self.yukkurrium.add_yukkuri(y_type, pos)

        for _ in range(3):
            i_type = "food_pellet"
            pos = (random.randint(100, SCREEN_WIDTH - 100), random.randint(100, SCREEN_HEIGHT - 100))
            self.yukkurrium.add_item(i_type, pos)


    def run(self):
        running = True
        while running:
            self.clock.tick(FPS)

            for event in pg.event.get():
                if event.type == pg.QUIT:
                    running = False
                self.handle_input(event)

            self.update()
            self.draw()

        pg.quit()
        sys.exit()

    def handle_input(self, event):
        # Basic camera controls
        if event.type == pg.MOUSEWHEEL:
            self.zoom += event.y * 0.1
            self.zoom = max(0.5, min(3.0, self.zoom))

        keys = pg.key.get_pressed()
        pan_speed = 10
        if keys[pg.K_LEFT]: self.camera_x -= pan_speed
        if keys[pg.K_RIGHT]: self.camera_x += pan_speed
        if keys[pg.K_UP]: self.camera_y -= pan_speed
        if keys[pg.K_DOWN]: self.camera_y += pan_speed

        if event.type == pg.MOUSEBUTTONDOWN:
            # Check for Yukkuri selection
            for yukkuri in self.yukkurrium.yukkuris:
                if yukkuri.rect.collidepoint(event.pos):
                    self.selected_yukkuri = yukkuri
                    break
            else:
                self.selected_yukkuri = None

            # Check for UI button clicks
            if self.selected_yukkuri:
                if self.sell_button_rect.collidepoint(event.pos):
                    self.sell_yukkuri(self.selected_yukkuri)
                elif self.train_button_rect.collidepoint(event.pos):
                    self.train_yukkuri(self.selected_yukkuri)

            if self.save_button_rect.collidepoint(event.pos):
                self.save_game()
            elif self.load_button_rect.collidepoint(event.pos):
                self.load_game()

            for item_type, button_rect in self.item_buttons.items():
                if button_rect.collidepoint(event.pos):
                    self.item_to_place = item_type
                    print(f"Selected {item_type} to place.")
                    break

            if self.item_to_place and not self.selected_yukkuri:
                price = self.item_types[self.item_to_place]["price"]
                if self.player_currency >= price:
                    self.player_currency -= price
                    self.yukkurrium.add_item(self.item_to_place, event.pos)
                    print(f"Placed {self.item_to_place} for {price}.")
                    self.item_to_place = None
                else:
                    print("Not enough money!")

    def execute_action(self, yukkuri, action):
        """Executes the chosen AI action."""
        if action == "eat":
            # Find the closest food item
            food_items = [i for i in self.yukkurrium.items if i.type == "food_pellet"]
            if food_items:
                closest_food = min(food_items, key=lambda i: pg.math.Vector2(i.rect.center).distance_to(yukkuri.rect.center))
                if pg.math.Vector2(closest_food.rect.center).distance_to(yukkuri.rect.center) < 5:
                    yukkuri.hunger = max(0, yukkuri.hunger - self.item_types["food_pellet"]["value"])
                    self.yukkurrium.remove_item(closest_food)
                    print(f"{yukkuri.name} ate some food.")
                else:
                    # Move towards food
                    pass # Basic movement would go here
        elif action == "sleep":
            yukkuri.health = min(100, yukkuri.health + 1)
        elif action == "play":
            yukkuri.happiness = min(100, yukkuri.happiness + 1)
        # Other actions can be implemented here...

    def sell_yukkuri(self, yukkuri):
        """Sells a Yukkuri and adds its value to the player's currency."""
        self.player_currency += yukkuri.calculate_quality_score()
        self.yukkurrium.remove_yukkuri(yukkuri)
        self.selected_yukkuri = None
        print(f"Sold a yukkuri! Current money: {self.player_currency}")

    def train_yukkuri(self, yukkuri):
        """Adds a badge to the selected Yukkuri."""
        yukkuri.badges.append("trained")
        print(f"{yukkuri.name} earned a badge!")

    def update(self):
        now = pg.time.get_ticks()
        if now - self.last_tick > self.needs_decay_interval:
            self.last_tick = now
            for yukkuri in self.yukkurrium.yukkuris:
                yukkuri.hunger = min(100, yukkuri.hunger + 1)
                yukkuri.happiness = max(0, yukkuri.happiness - 1)

        self.yukkurrium.update()
        for yukkuri in self.yukkurrium.yukkuris:
            action = self.ai_engine.select_action(yukkuri)
            if action:
                self.execute_action(yukkuri, action)

    def draw(self):
        self.screen.fill((200, 255, 200))
        game_surface = pg.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pg.SRCALPHA)
        self.yukkurrium.draw(game_surface)

        if self.selected_yukkuri:
            pg.draw.rect(game_surface, (255, 0, 0), self.selected_yukkuri.rect, 2)

        scaled_surface = pg.transform.scale(game_surface,
                                            (int(SCREEN_WIDTH * self.zoom),
                                             int(SCREEN_HEIGHT * self.zoom)))
        blit_pos = (-self.camera_x, -self.camera_y)
        self.screen.blit(scaled_surface, blit_pos)

        self.draw_ui()
        pg.display.flip()

    def draw_ui(self):
        # Display player currency
        currency_text = self.font.render(f"Money: {self.player_currency}", True, (0,0,0))
        self.screen.blit(currency_text, (10, 10))

        if self.selected_yukkuri:
            # Display stats
            stats = self.selected_yukkuri.get_state()
            y, h = 40, 25
            for key, val in stats.items():
                stat_text = self.font.render(f"{key.capitalize()}: {val}", True, (0,0,0))
                self.screen.blit(stat_text, (10, y))
                y += h

            # Sell button
            self.sell_button_rect = pg.Rect(10, y + 20, 100, 40)
            pg.draw.rect(self.screen, (0, 200, 0), self.sell_button_rect)
            sell_text = self.font.render("Sell", True, (255,255,255))
            self.screen.blit(sell_text, (self.sell_button_rect.x + 35, self.sell_button_rect.y + 10))

            # Train button
            self.train_button_rect = pg.Rect(120, y + 20, 100, 40)
            pg.draw.rect(self.screen, (200, 0, 0), self.train_button_rect)
            train_text = self.font.render("Train", True, (255,255,255))
            self.screen.blit(train_text, (self.train_button_rect.x + 30, self.train_button_rect.y + 10))

        # Save/Load buttons
        self.save_button_rect = pg.Rect(SCREEN_WIDTH - 220, 10, 100, 40)
        pg.draw.rect(self.screen, (0, 0, 200), self.save_button_rect)
        save_text = self.font.render("Save", True, (255,255,255))
        self.screen.blit(save_text, (self.save_button_rect.x + 30, self.save_button_rect.y + 10))

        self.load_button_rect = pg.Rect(SCREEN_WIDTH - 110, 10, 100, 40)
        pg.draw.rect(self.screen, (100, 100, 100), self.load_button_rect)
        load_text = self.font.render("Load", True, (255,255,255))
        self.screen.blit(load_text, (self.load_button_rect.x + 30, self.load_button_rect.y + 10))

        # Item placement UI
        self.item_buttons = {}
        y = 100
        for item_type, item_data in self.item_types.items():
            button_rect = pg.Rect(SCREEN_WIDTH - 120, y, 110, 40)
            self.item_buttons[item_type] = button_rect
            pg.draw.rect(self.screen, (0, 100, 200), button_rect)
            text = self.font.render(f"Buy {item_data['name']}", True, (255,255,255))
            self.screen.blit(text, (button_rect.x + 10, button_rect.y + 10))
            y += 50

    def save_game(self, file_path="savegame.json"):
        """Saves the current game state to a file."""
        state = {
            "player_currency": self.player_currency,
            "yukkurrium": self.yukkurrium.get_state(),
        }
        with open(file_path, "w") as f:
            json.dump(state, f, indent=4)
        print("Game saved!")

    def load_game(self, file_path="savegame.json"):
        """Loads the game state from a file."""
        try:
            with open(file_path, "r") as f:
                state = json.load(f)

            self.player_currency = state["player_currency"]
            self.yukkurrium.yukkuris.empty()
            self.yukkurrium.items.empty()

            for y_data in state["yukkurrium"]["yukkuris"]:
                yukkuri = Yukkuri(y_data["type"], y_data["position"])
                yukkuri.name = y_data["name"]
                yukkuri.health = y_data["health"]
                yukkuri.hunger = y_data["hunger"]
                yukkuri.happiness = y_data["happiness"]
                yukkuri.cleanliness = y_data["cleanliness"]
                yukkuri.age = y_data["age"]
                yukkuri.growth_stage = y_data["growth_stage"]
                yukkuri.badges = y_data["badges"]
                self.yukkurrium.yukkuris.add(yukkuri)

            for i_data in state["yukkurrium"]["items"]:
                item = Item(i_data["type"], i_data["position"])
                self.yukkurrium.items.add(item)

            print("Game loaded!")
        except FileNotFoundError:
            print("No save file found.")

if __name__ == "__main__":
    game = GameLoop()
    game.run()
