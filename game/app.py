import pygame
import time
import os
from datetime import datetime
from typing import Dict, List, Any
from game.data_loader import DataLoader
from simulation.agent import Agent
from simulation.world import World
from game.game_modes import GameMode, LiveMode, PlacementMode
from engine.serialization import save_game, load_game
from game.ui import UI
from simulation.dialogue import DialogueManager
from engine.event_bus import EventBus, AGENT_SPOKE
from game.config import Config

class App:
    def __init__(self) -> None:
        pygame.init()
        self.config = Config()
        self.screen_width: int = self.config.get("screen_width", 800)
        self.screen_height: int = self.config.get("screen_height", 600)
        self.screen: pygame.Surface = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption(self.config.get("caption", "Yukkuri Raising Game MVP"))
        self.clock: pygame.time.Clock = pygame.time.Clock()
        self.is_running: bool = False
        self.dt: float = 1.0 / self.config.get("tick_rate", 60)

        self.event_bus: EventBus = EventBus()
        self.data_loader: DataLoader = DataLoader()
        self.dialogue_manager: DialogueManager = DialogueManager(self.data_loader.dialogue_lines)

        self.world: World = World(self.data_loader.room, self.data_loader.item_definitions)
        self.agents: List[Agent] = []
        self._spawn_initial_agents()
        self.ui: UI = UI(self)

        self.event_bus.subscribe(AGENT_SPOKE, self.ui.speech_bubble_manager.add_bubble)

        self.modes: Dict[str, GameMode] = {
            'live': LiveMode(self),
            'placement': PlacementMode(self)
        }
        self.current_mode: GameMode = self.modes['live']

    def _spawn_initial_agents(self) -> None:
        archetype = self.data_loader.get_agent_archetype("basic_yukkuri")
        action_templates = self.data_loader.action_templates
        if archetype:
            for pos in self.data_loader.room['spawn_points']:
                self.agents.append(Agent(archetype, (pos['x'], pos['y']), action_templates))

    def run(self) -> None:
        self.is_running = True
        last_time = time.time()
        accumulator = 0.0

        while self.is_running:
            current_time = time.time()
            frame_time = current_time - last_time
            last_time = current_time
            accumulator += frame_time

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.is_running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_p:
                        self.current_mode = self.modes['placement'] if self.current_mode == self.modes['live'] else self.modes['live']
                    elif event.key == pygame.K_s:
                        save_game(self.world, self.agents, "savegame.json")
                    elif event.key == pygame.K_l:
                        self.world, self.agents = load_game("savegame.json", self.data_loader)
                    elif event.key == pygame.K_F12:
                        self.take_screenshot()
                self.current_mode.handle_input(event)

            while accumulator >= self.dt:
                self.current_mode.update(self.dt)
                accumulator -= self.dt

            self.screen.fill((0, 0, 0))
            self.current_mode.render(self.screen)
            pygame.display.flip()
            self.clock.tick(60)

        pygame.quit()

    def take_screenshot(self) -> None:
        """Saves the current screen buffer to a timestamped PNG file."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"screenshot_{timestamp}.png"
        filepath = os.path.join("screenshots", filename)
        pygame.image.save(self.screen, filepath)
        print(f"Screenshot saved to {filepath}")
