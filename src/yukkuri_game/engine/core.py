"""
Module defining the core GameLoop class.
"""
import os
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
        render_headless (bool): Flag indicating if we should render even in headless mode (for screenshots).
        resources (ResourceManager): The resource manager instance.
        ui_manager (pygame_gui.UIManager): The UI manager instance.
        world (World): The ECS world instance.
        time_scale (float): The scale factor for game time (e.g., 2.0 for 2x speed).
        paused (bool): Flag indicating if the game simulation is paused.
        dt (float): The time elapsed since the last frame in seconds.
    """

    def __init__(self, width: int = 1280, height: int = 720, title: str = "Yukkuri Raising Game", headless: bool = False, render_headless: bool = False):
        """
        Initializes the GameLoop.

        Args:
            width (int, optional): The width of the window. Defaults to 1280.
            height (int, optional): The height of the window. Defaults to 720.
            title (str, optional): The title of the window. Defaults to "Yukkuri Raising Game".
            headless (bool, optional): Whether to run in headless mode. Defaults to False.
            render_headless (bool, optional): Whether to render to a surface in headless mode. Defaults to False.
        """
        self.headless = headless
        self.render_headless = render_headless

        # NOTE: We do not set SDL_VIDEODRIVER here to avoid side effects.
        # It should be set by the caller (main.py or test runner) before init.
        # But for convenience, if we detect we are headless and driver is not set, we warn or set it?
        # Actually, let's just assume the caller handles it.
        # However, to be safe for existing calls, if headless is True and we are about to init pygame,
        # we might need to ensure it's dummy if not set.
        if self.headless and "SDL_VIDEODRIVER" not in os.environ:
             logger.warning("Headless mode requested but SDL_VIDEODRIVER not set. Setting to 'dummy'.")
             os.environ["SDL_VIDEODRIVER"] = "dummy"

        pygame.init()
        self.width = width
        self.height = height

        # When headless with dummy driver, set_mode creates a surface that works for offscreen rendering
        # provided SDL_VIDEODRIVER is dummy.
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

    @property
    def should_render(self) -> bool:
        """
        Returns True if the game should render the frame.
        """
        return not self.headless or self.render_headless

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

    def update(self) -> None:
        """
        Updates the game state.

        Calculates delta time, updates the UI manager, and updates the ECS world.

        Returns:
            None
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

        Returns:
            None
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

        Returns:
            None
        """
        pass

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

            if self.should_render:
                self.draw()

        pygame.quit()
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
