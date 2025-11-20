import pygame
import pygame_gui
from loguru import logger
from .resource_manager import ResourceManager
from .ecs import World

class GameLoop:
    """
    The main game loop class.

    Handles initialization, the main loop, event handling, updating, and drawing.

    Attributes:
        width (int): The width of the game window.
        height (int): The height of the game window.
        screen (pygame.Surface): The main display surface.
        clock (pygame.time.Clock): The game clock for managing frame rate.
        running (bool): Flag indicating if the game loop is running.
        headless (bool): Flag indicating if the game is running in headless mode (no window).
        resources (ResourceManager): The resource manager instance.
        ui_manager (pygame_gui.UIManager): The UI manager instance.
        world (World): The ECS world instance.
        time_scale (float): The scale factor for game time (e.g., 2.0 for 2x speed).
        paused (bool): Flag indicating if the game simulation is paused.
        dt (float): The time elapsed since the last frame in seconds.
    """

    def __init__(self, width: int = 1280, height: int = 720, title: str = "Yukkuri Raising Game"):
        """
        Initializes the GameLoop.

        Args:
            width: The width of the window. Defaults to 1280.
            height: The height of the window. Defaults to 720.
            title: The title of the window. Defaults to "Yukkuri Raising Game".
        """
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

    def setup(self) -> None:
        """
        Sets up the game state.

        Override this method to add systems and initial entities.
        """
        pass

    def handle_events(self) -> None:
        """
        Handles Pygame events.

        Processes quit events, UI events, and calls on_event for custom handling.
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            self.ui_manager.process_events(event)
            self.on_event(event)

    def on_event(self, event: pygame.event.Event) -> None:
        """
        Callback for handling specific input events.

        Override this method to implement custom input handling.

        Args:
            event: The Pygame event to handle.
        """
        pass

    def update(self) -> None:
        """
        Updates the game state.

        Calculates delta time, updates the UI manager, and updates the ECS world.
        """
        time_delta = self.clock.tick(60) / 1000.0
        self.dt = time_delta

        self.ui_manager.update(time_delta)

        if not self.paused:
            # Update ECS world
            # In a real game we might separate logic update tick from render tick
            # and use accumulation for fixed time steps, but for MVP simple dt is fine.
            sim_dt = self.dt * self.time_scale
            self.world.update(sim_dt)

    def draw(self) -> None:
        """
        Draws the game frame.

        Clears the screen, renders the world, draws the UI, and flips the display.
        """
        self.screen.fill((30, 30, 30)) # Dark background

        # Draw Game World (Placeholder for now, systems should draw)
        # We might need a RenderSystem if we want to be pure ECS,
        # or just call a render method on the world/systems.
        # For now, let's assume we have a render callback or system.
        self.render_world()

        self.ui_manager.draw_ui(self.screen)
        pygame.display.flip()

    def render_world(self) -> None:
        """
        Renders the game entities.

        Override this method to implement custom rendering logic.
        """
        pass

    def run(self) -> None:
        """
        Runs the main game loop.

        Calls setup, then enters the loop calling handle_events, update, and draw until running becomes False.
        """
        self.setup()
        logger.info("Game Loop Started")
        while self.running:
            self.handle_events()
            self.update()
            if not self.headless:
                self.draw()

        pygame.quit()
        logger.info("Game Loop Ended")

    def set_headless(self, headless: bool) -> None:
        """
        Sets the headless mode.

        Args:
            headless: True to enable headless mode, False otherwise.
        """
        self.headless = headless
