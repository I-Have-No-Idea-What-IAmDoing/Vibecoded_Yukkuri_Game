"""
Module defining the core GameLoop class.
"""
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

    def __init__(self, width: int = 1280, height: int = 720, title: str = "Yukkuri Raising Game", headless: bool = False):
        """
        Initializes the GameLoop.

        Args:
            width (int, optional): The width of the window. Defaults to 1280.
            height (int, optional): The height of the window. Defaults to 720.
            title (str, optional): The title of the window. Defaults to "Yukkuri Raising Game".
            headless (bool, optional): Whether to run in headless mode. Defaults to False.
        """
        pygame.init()
        self.width = width
        self.height = height
        self.headless = headless

        if self.headless:
            # In headless mode, we rely strictly on SDL_VIDEODRIVER=dummy.
            # This ensures we don't accidentally depend on a window system.
            # The set_mode call creates a surface but no window in dummy mode.
            self.screen = pygame.display.set_mode((width, height))
        else:
            self.screen = pygame.display.set_mode((width, height))
            pygame.display.set_caption(title)

        self.clock = pygame.time.Clock()
        self.running = True

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
        self.is_setup = False

    def setup(self) -> None:
        """
        Sets up the game state.

        Override this method to add systems and initial entities.

        Returns:
            None
        """
        pass

    def handle_events(self) -> None:
        """
        Handles Pygame events.

        Processes quit events, UI events, and calls on_event for custom handling.

        Returns:
            None
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
            event (pygame.event.Event): The Pygame event to handle.

        Returns:
            None
        """
        pass

    def tick(self, dt: float) -> None:
        """
        Advances the game logic by one fixed time step.
        Does NOT perform rendering.

        Args:
            dt (float): The delta time in seconds.

        Returns:
            None
        """
        self.dt = dt
        self.ui_manager.update(dt)

        if not self.paused:
            # Update ECS world
            sim_dt = self.dt * self.time_scale
            self.world.update(sim_dt)

    def update(self) -> None:
        """
        Updates the game state.
        """
        time_delta = self.clock.tick(60) / 1000.0
        self.tick(time_delta)

    def draw(self) -> None:
        """
        Draws the game frame.
        """
        self.render()

    def render(self) -> None:
        """
        Performs rendering operations.
        Separated from update/tick for headless efficiency.
        """
        self.screen.fill((30, 30, 30)) # Dark background
        self.render_world()
        self.ui_manager.draw_ui(self.screen)
        pygame.display.flip()

    def render_world(self) -> None:
        """
        Renders the game entities.

        Override this method to implement custom rendering logic.

        Returns:
            None
        """
        pass

    def quit(self) -> None:
        """
        Stops the game loop and quits Pygame.
        """
        self.running = False
        pygame.quit()

    def run(self) -> None:
        """
        Runs the main game loop.

        Calls setup, then enters the loop calling handle_events, update, and draw until running becomes False.

        Returns:
            None
        """
        self.setup()
        logger.info("Game Loop Started")
        while self.running:
            self.handle_events()
            self.update()
            if not self.headless:
                self.draw()

        self.quit()
        logger.info("Game Loop Ended")

    def set_headless(self, headless: bool) -> None:
        """
        Sets the headless mode.

        Args:
            headless (bool): True to enable headless mode, False otherwise.

        Returns:
            None
        """
        self.headless = headless
