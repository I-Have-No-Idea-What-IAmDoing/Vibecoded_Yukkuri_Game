import pygame
import pygame_gui
from loguru import logger
from .resource_manager import ResourceManager
from .ecs import World

class GameLoop:
    def __init__(self, width=1280, height=720, title="Yukkuri Raising Game"):
        pygame.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption(title)

        self.clock = pygame.time.Clock()
        self.running = True
        self.headless = False

        # Resource Manager
        self.resources = ResourceManager()
        self.resources.load_all_data()

        # UI Manager
        self.ui_manager = pygame_gui.UIManager((width, height))

        # ECS World
        self.world = World()

        # Game State
        self.time_scale = 1.0
        self.paused = False
        self.dt = 0.0

    def setup(self):
        """Override to add systems and initial entities."""
        pass

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            self.ui_manager.process_events(event)
            self.on_event(event)

    def on_event(self, event):
        """Override for specific input handling."""
        pass

    def update(self):
        time_delta = self.clock.tick(60) / 1000.0
        self.dt = time_delta

        self.ui_manager.update(time_delta)

        if not self.paused:
            # Update ECS world
            # In a real game we might separate logic update tick from render tick
            # and use accumulation for fixed time steps, but for MVP simple dt is fine.
            sim_dt = self.dt * self.time_scale
            self.world.update(sim_dt)

    def draw(self):
        self.screen.fill((30, 30, 30)) # Dark background

        # Draw Game World (Placeholder for now, systems should draw)
        # We might need a RenderSystem if we want to be pure ECS,
        # or just call a render method on the world/systems.
        # For now, let's assume we have a render callback or system.
        self.render_world()

        self.ui_manager.draw_ui(self.screen)
        pygame.display.flip()

    def render_world(self):
        """Override to render game entities."""
        pass

    def run(self):
        self.setup()
        logger.info("Game Loop Started")
        while self.running:
            self.handle_events()
            self.update()
            if not self.headless:
                self.draw()

        pygame.quit()
        logger.info("Game Loop Ended")

    def set_headless(self, headless: bool):
        self.headless = headless
