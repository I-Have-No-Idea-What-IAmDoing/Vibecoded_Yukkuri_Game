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

        # Fixed Timestep variables
        self.accumulator = 0.0
        self.fixed_dt = 1.0 / 60.0  # 60 updates per second

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
        Updates the game state using a fixed timestep loop.
        """
        # We still limit the loop speed to avoid using 100% CPU in simple scenes,
        # but the physics update will be fixed.
        # Note: tick() returns time since last call in milliseconds.
        # If we want uncapped FPS rendering but fixed physics, we should use get_ticks() diff.
        # For now, we'll keep the 60 FPS cap for rendering but ensure physics is fixed.
        # Actually, "Fix Your Timestep" suggests decoupling.
        # Let's use get_ticks for accurate time tracking.

        # self.clock.tick(60) # Optional: cap frame rate
        pass # The loop is now controlled in run()

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
        Runs the main game loop using "Fix Your Timestep" logic.

        Returns:
            None
        """
        self.setup()
        logger.info("Game Loop Started")

        current_time = pygame.time.get_ticks() / 1000.0

        while self.running:
            new_time = pygame.time.get_ticks() / 1000.0
            frame_time = new_time - current_time
            current_time = new_time

            # Spiral of death protection
            if frame_time > 0.25:
                frame_time = 0.25

            self.accumulator += frame_time

            while self.accumulator >= self.fixed_dt:
                self.handle_events()
                self.tick(self.fixed_dt)
                self.accumulator -= self.fixed_dt

            # Optional: Interpolation could be calculated here
            # alpha = self.accumulator / self.fixed_dt

            if not self.headless:
                self.draw()
                # If we are running faster than display refresh, we might want to sleep?
                # or just let it run as fast as possible (uncapped).
                # Using clock.tick to cap rendering FPS is good practice to save battery/CPU.
                self.clock.tick(60)

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
