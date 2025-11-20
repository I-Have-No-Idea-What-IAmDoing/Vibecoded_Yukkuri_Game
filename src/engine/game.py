import pygame
from src.engine.ecs import EntityManager
from src.utils.loader import game_data
from src.engine.systems import MovementSystem, NeedsSystem, InteractionSystem
from src.engine.utility_ai import AISystem
from src.engine.ecs import Entity
from src.engine.components import Transform, Stats, Identity, AIComponent, ItemComponent
from src.ui.renderer import Renderer
from src.ui.interface import Interface
from src.utils.persistence import Persistence
from src.utils.audio_manager import AudioManager
import random

class GameState:
    def __init__(self):
        self.money = 0
        self.time_elapsed = 0.0 # in seconds
        self.day_count = 1
        self.simulation_speed = 1.0
        self.selected_entity_id = None
        self.camera_x = 0.0
        self.camera_y = 0.0
        self.zoom = 1.0

class Game:
    def __init__(self):
        self.running = True
        self.clock = pygame.time.Clock()
        self.ecs = EntityManager()
        self.state = GameState()

        # Load configurations
        self.config = game_data.configs
        self.width = self.config["game"]["screen_width"]
        self.height = self.config["game"]["screen_height"]
        self.target_fps = self.config["game"]["fps"]

        self.screen = None

        # Initialize starting state
        self.state.money = self.config["game"]["starting_money"]
        self.renderer = None
        self.interface = None
        self.persistence = Persistence()
        self.audio_manager = None

    def initialize(self):
        pygame.init()
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
        pygame.display.set_caption("Yukkuri Raising Game (MVP)")

        # Initialize Audio
        audio_config = self.config.get("audio", {})
        self.audio_manager = AudioManager(audio_config)

        self.renderer = Renderer(self.screen)
        self.interface = Interface(self.screen)

        # Initialize Systems
        self.ecs.add_system(AISystem())
        self.ecs.add_system(MovementSystem())
        self.ecs.add_system(InteractionSystem())
        self.ecs.add_system(NeedsSystem())

        # Spawn initial Yukkuris
        self.spawn_yukkuri("marisa", 100, 100)
        self.spawn_yukkuri("reimu", 300, 200)

    def spawn_yukkuri(self, type_id, x, y):
        types = game_data.yukkuri_types
        if type_id not in types:
            return

        data = types[type_id]
        e = Entity()
        e.add_component(Transform(x=x, y=y))
        e.add_component(Stats(
            max_health=data.get("base_health", 100),
            health=data.get("base_health", 100),
            max_hunger=data.get("base_hunger", 100),
            max_happiness=data.get("base_happiness", 100)
        ))

        # Parse color string "r, g, b"
        c_str = data.get("image_color", "255, 255, 255")
        color = tuple(map(int, c_str.split(",")))

        e.add_component(Identity(name=data.get("name", "Yukkuri"), type_id=type_id, color=color))
        e.add_component(AIComponent())

        self.ecs.add_entity(e)

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            # Basic camera controls (placeholder for now)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False

                # Camera Pan
                elif event.key == pygame.K_LEFT:
                    self.state.camera_x -= 50
                elif event.key == pygame.K_RIGHT:
                    self.state.camera_x += 50
                elif event.key == pygame.K_UP:
                    self.state.camera_y -= 50
                elif event.key == pygame.K_DOWN:
                    self.state.camera_y += 50

                # Zoom
                elif event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS:
                    self.state.zoom = min(2.0, self.state.zoom + 0.1)
                elif event.key == pygame.K_MINUS:
                    self.state.zoom = max(0.5, self.state.zoom - 0.1)

                # Simulation Speed
                elif event.key == pygame.K_1:
                    self.state.simulation_speed = 1.0
                elif event.key == pygame.K_2:
                    self.state.simulation_speed = 2.0
                elif event.key == pygame.K_3:
                    self.state.simulation_speed = 5.0
                elif event.key == pygame.K_SPACE:
                     self.state.simulation_speed = 0.0 if self.state.simulation_speed > 0 else 1.0

                # Sell / Train shortcut
                elif event.key == pygame.K_s and pygame.key.get_mods() & pygame.KMOD_CTRL:
                     # Ctrl+S to save
                     self.persistence.save_game(self)
                elif event.key == pygame.K_l and pygame.key.get_mods() & pygame.KMOD_CTRL:
                     # Ctrl+L to load
                     self.persistence.load_game(self)
                elif event.key == pygame.K_s:
                    self.sell_selected()
                elif event.key == pygame.K_t:
                    self.train_selected()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: # Left Click
                    self.handle_click(event.pos, button=1)
                elif event.button == 3: # Right Click
                    self.handle_click(event.pos, button=3)

    def handle_click(self, pos, button=1):
        # Simple hit testing
        # Convert screen pos to world pos
        world_x = (pos[0] / self.state.zoom) + self.state.camera_x
        world_y = (pos[1] / self.state.zoom) + self.state.camera_y

        if button == 3:
            # Right click: Spawn Food (Basic interaction for MVP)
            # Default to food pellet
            self.spawn_item("food_pellet", world_x - 10, world_y - 10)
            return

        # Check entities
        # Reverse list to check top-most first (which are usually drawn last)
        for entity in reversed(self.ecs.entities):
            t = entity.get_component(Transform)
            if t:
                if t.x <= world_x <= t.x + t.width and t.y <= world_y <= t.y + t.height:
                    self.state.selected_entity_id = entity.id
                    print(f"Selected: {entity.id}")
                    return

        # If no entity clicked, deselect
        self.state.selected_entity_id = None

        # If Right click (Context Menu / Spawn Item)
        # For MVP: just spawn random food if money > 10
        # In full version: Open context menu
        pass # handled in handle_input

    def spawn_item(self, item_id, x, y):
        items = game_data.items
        if item_id not in items:
            return

        data = items[item_id]
        cost = data.get("cost", 10)

        if self.state.money < cost:
            print("Not enough money!")
            return

        self.state.money -= cost

        e = Entity()
        e.add_component(Transform(x=x, y=y, width=20, height=20))
        e.add_component(ItemComponent(item_type=data.get("type", "unknown"), value=data.get("value", 0), cost=cost))

        c_str = data.get("image_color", "200, 200, 200")
        color = tuple(map(int, c_str.split(",")))
        e.add_component(Identity(name=data.get("name", "Item"), type_id=item_id, color=color))

        self.ecs.add_entity(e)
        print(f"Bought {data.get('name')} for ${cost}")

    def sell_selected(self):
        if not self.state.selected_entity_id: return
        entity = next((e for e in self.ecs.entities if e.id == self.state.selected_entity_id), None)
        if entity and entity.get_component(Identity):
            stats = entity.get_component(Stats)
            if stats:
                val = int(stats.quality_score)
                self.state.money += val
                print(f"Sold {entity.get_component(Identity).name} for ${val}")
                entity.marked_for_destruction = True
                self.state.selected_entity_id = None

    def train_selected(self):
        if not self.state.selected_entity_id: return
        entity = next((e for e in self.ecs.entities if e.id == self.state.selected_entity_id), None)
        if entity and entity.get_component(Stats):
            # MVP stub: Costs $10, adds 1 badge
            if self.state.money >= 10:
                self.state.money -= 10
                entity.get_component(Stats).badges += 1
                print(f"Trained {entity.get_component(Identity).name}. Badges: {entity.get_component(Stats).badges}")

    def update(self):
        dt = self.clock.tick(self.target_fps) / 1000.0

        # Handle simulation speed
        sim_dt = dt * self.state.simulation_speed

        # Update Game State
        self.state.time_elapsed += sim_dt
        day_length = self.config["simulation"]["day_length_seconds"]
        self.state.day_count = 1 + int(self.state.time_elapsed / day_length)

        # Update ECS
        self.ecs.update(sim_dt, self.state)

    def render(self):
        if not self.screen:
            return

        self.screen.fill((30, 30, 30)) # Background

        if self.renderer:
            self.renderer.render_game(self.ecs, self.state)

        if self.interface:
            self.interface.render_ui(self.state, self.ecs)

        pygame.display.flip()

    def run(self):
        self.initialize()
        while self.running:
            self.handle_input()
            self.update()
            self.render()
        pygame.quit()
