"""
Game Driver for automated testing.
"""

import random
import pygame
import os
from typing import Generator, Any, Callable, List, Optional, Type
from dataclasses import dataclass
from collections import deque
from ..engine.application import Application
from ..engine.event_bus import Event

# --- Predicates & Commands ---


@dataclass
class WaitUntil:
    """
    Command to wait until a predicate returns True.

    Attributes:
        predicate (Callable[[], bool]): The condition function to check.
        timeout (float): Max wait time in seconds. Defaults to 10.0.
        description (str): Description of the condition for logging.
    """

    predicate: Callable[[], bool]
    timeout: float = 10.0
    description: str = "condition"


@dataclass
class WaitFrames:
    """
    Command to wait for a specific number of frames.

    Attributes:
        frames (int): Number of frames to wait.
    """

    frames: int


@dataclass
class InjectInput:
    """
    Command to inject a list of input events.

    Attributes:
        events (List[pygame.event.Event]): List of events to inject.
    """

    events: List[pygame.event.Event]


@dataclass
class Screenshot:
    """
    Command to take a screenshot.

    Attributes:
        filename (str): The filename to save the screenshot as.
    """

    filename: str


@dataclass
class WaitUntilScene:
    """
    Command to wait until the current scene is of a specific type.

    Attributes:
        scene_type (Type): The expected scene class.
        timeout (float): Max wait time in seconds. Defaults to 10.0.
    """

    scene_type: Type
    timeout: float = 10.0


# --- Input Helpers ---


def Click(x: int, y: int) -> InjectInput:
    """
    Creates a full click (Down + Up) event at x, y.

    Args:
        x (int): X coordinate.
        y (int): Y coordinate.

    Returns:
        InjectInput: The input injection command.
    """
    return InjectInput(
        [
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (x, y), "button": 1}),
            pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": (x, y), "button": 1}),
        ]
    )


def KeyPress(key: int) -> InjectInput:
    """
    Creates a key press (Down + Up) event.

    Args:
        key (int): The pygame key code.

    Returns:
        InjectInput: The input injection command.
    """
    return InjectInput(
        [
            pygame.event.Event(pygame.KEYDOWN, {"key": key}),
            pygame.event.Event(pygame.KEYUP, {"key": key}),
        ]
    )


# --- Driver ---


class GameDriver:
    """
    Controls a YukkuriGame instance for deterministic headless testing.

    Attributes:
        game (Application): The game application instance.
        fixed_dt (float): Fixed time step for simulation ticks.
        simulated_time (float): Total time simulated so far.
        frame_count (int): Total frames simulated.
    """

    def __init__(self, game_instance: Application, fixed_dt: float = 1.0 / 60.0):
        """
        Initializes the GameDriver.

        Args:
            game_instance (Application): The application instance.
            fixed_dt (float): The fixed delta time for simulation updates.
        """
        self.game = game_instance
        self.fixed_dt = fixed_dt
        self.simulated_time = 0.0
        self.frame_count = 0
        self._scenario_deadline: Optional[float] = None
        self.event_history: deque = deque(maxlen=100)

    def seed_rng(self, seed: int = 42) -> None:
        """
        Seeds random number generators for determinism.

        Args:
            seed (int): The seed value.
        """
        random.seed(seed)
        try:
            import numpy as np

            np.random.seed(seed)
        except ImportError:
            pass

    def setup(self) -> None:
        """
        Sets up the game instance.
        Ensures headless mode and active scene.
        """
        self.seed_rng()
        if hasattr(self.game, "set_headless") and not self.game.headless:
            self.game.set_headless(True)

        # Hook event bus for logging
        if isinstance(self.game, Application) and hasattr(self.game, "event_manager"):
            # We want to intercept events to store them in history
            # but we can't easily replace the method on the instance if it's bound.
            # Actually we can replace the instance method.
            original_publish = self.game.event_manager.bus.publish

            def intercepted_publish(event: Event) -> None:
                self.event_history.append(event)
                original_publish(event)

            self.game.event_manager.bus.publish = intercepted_publish

        # Application initializes on creation. Ensure GameplayScene is active.
        if isinstance(self.game, Application):
            from ..scenes.gameplay import GameplayScene

            if not self.game.scene_manager.current_scene:
                self.game.scene_manager.push(GameplayScene(self.game))
        elif hasattr(self.game, "setup"):
            self.game.setup()

    def create_yukkuri(self, type_id: str, x: float, y: float) -> int:
        """
        Creates a Yukkuri entity in the current world.

        Args:
            type_id (str): The Yukkuri type ID.
            x (float): X coordinate.
            y (float): Y coordinate.

        Returns:
            int: The entity ID, or -1 if failed.
        """
        from ..game.entity_factory import EntityFactory

        if not self.world:
            return -1
        factory = self.world.services.try_get(EntityFactory)
        if factory:
            return int(factory.create_yukkuri(type_id, x, y))
        return -1

    def create_item(self, type_id: str, x: float, y: float) -> int:
        """
        Creates an item entity in the current world.

        Args:
            type_id (str): The item type ID.
            x (float): X coordinate.
            y (float): Y coordinate.

        Returns:
            int: The entity ID, or -1 if failed.
        """
        from ..game.entity_factory import EntityFactory

        if not self.world:
            return -1
        factory = self.world.services.try_get(EntityFactory)
        if factory:
            return int(factory.create_item(type_id, x, y))
        return -1

    def set_ai_target_pos(self, entity_id: int, x: float, y: float) -> None:
        """
        Manually sets an AI target position override.

        Args:
            entity_id (int): The entity ID.
            x (float): Target X.
            y (float): Target Y.
        """
        from ..game.yukkuri_components import AIState

        if not self.world:
            return
        ai = self.world.get_component(entity_id, AIState)
        if ai:
            if ai.state_data is None:
                ai.state_data = {}
            ai.state_data["target_x"] = x
            ai.state_data["target_y"] = y
            ai.path = None
            ai.manual_override = True

    def set_ai_action(self, entity_id: int, action: str, target_id: int = -1) -> None:
        """
        Manually forces a specific AI action.

        Args:
            entity_id (int): The entity ID.
            action (str): The action name.
            target_id (int): Optional target entity ID.
        """
        from ..game.yukkuri_components import AIState

        if not self.world:
            return
        ai = self.world.get_component(entity_id, AIState)
        if ai:
            ai.current_action = action
            if target_id != -1:
                ai.current_target_id = target_id
            ai.path = None
            ai.manual_override = True

    def cleanup(self) -> None:
        """Cleans up the game instance."""
        self.game.quit()

    def wait_until_scene(self, scene_type: Type, timeout: float = 10.0) -> None:
        """
        Waits until the current scene is of the specified type.

        Args:
            scene_type (Type): The expected scene class.
            timeout (float): Max wait time in seconds.
        """

        def predicate() -> bool:
            if isinstance(self.game, Application):
                return isinstance(self.game.scene_manager.current_scene, scene_type)
            return False

        self._wait_until(
            WaitUntil(predicate, timeout, f"Scene is {scene_type.__name__}")
        )

    def get_entities_with(self, *components: Type) -> List[int]:
        """
        Returns a list of entity IDs that have all specified components.

        Args:
            *components (Type): Component classes.

        Returns:
            List[int]: List of entity IDs.
        """
        if self.world:
            return self.world.get_entities_with(*components)
        return []

    def assert_entity_count(self, count: int, *components: Type) -> None:
        """
        Asserts that a specific number of entities exist with the given components.

        Args:
            count (int): Expected number of entities.
            *components (Type): Component classes.
        """
        entities = self.get_entities_with(*components)
        assert len(entities) == count, (
            f"Expected {count} entities with components {components}, "
            f"but found {len(entities)}: {entities}"
        )

    def run_scenario(
        self, scenario_gen: Generator[Any, None, None], timeout: float = 10.0
    ) -> None:
        """
        Runs a test scenario generator.

        Args:
            scenario_gen (Generator): The scenario generator yielding commands.
            timeout (float): Max simulated time for the scenario.

        Raises:
            TimeoutError: If the scenario exceeds the timeout.
            Exception: Re-raises any exception from the scenario.
        """
        self.setup()
        start_sim_time = self.simulated_time
        self._scenario_deadline = start_sim_time + timeout

        try:
            iterator = iter(scenario_gen)
            while True:
                try:
                    step = next(iterator)
                except StopIteration:
                    break

                self._check_global_timeout()

                if isinstance(step, WaitUntil):
                    self._wait_until(step)
                elif isinstance(step, WaitFrames):
                    self._wait_frames(step)
                elif isinstance(step, InjectInput):
                    for event in step.events:
                        pygame.event.post(event)
                elif isinstance(step, Screenshot):
                    self.save_screenshot(step.filename)
                elif isinstance(step, WaitUntilScene):
                    self.wait_until_scene(step.scene_type, step.timeout)
                elif callable(step):
                    step()
                else:
                    pass
        except Exception as e:
            self.save_screenshot(f"screenshots/failure_{self.frame_count}.png")
            # Dump logs/events
            log_filename = f"screenshots/failure_{self.frame_count}.log"
            os.makedirs(os.path.dirname(log_filename), exist_ok=True)
            with open(log_filename, "w") as f:
                f.write(f"Exception: {e}\n")
                f.write("Last 100 Events:\n")
                for evt in self.event_history:
                    f.write(f"{evt}\n")
            raise e
        finally:
            self._scenario_deadline = None

    def _tick(self) -> None:
        """Advances the game by one fixed time step."""
        # 0. Check if game is running
        if hasattr(self.game, "running") and not self.game.running:
            return

        # 1. Handle Events
        # Check if handle_events or process_events exists on self.game
        if hasattr(self.game, "handle_events"):
            self.game.handle_events()
        elif hasattr(self.game, "process_events"):
            self.game.process_events()
        else:
            pygame.event.pump()

        # Check again if game stopped running after event processing
        if hasattr(self.game, "running") and not self.game.running:
            return

        # 2. Update Game State
        if hasattr(self.game, "update"):
            self.game.update(self.fixed_dt)
        elif hasattr(self.game, "tick"):
            self.game.tick(self.fixed_dt)

        self.simulated_time += self.fixed_dt
        self.frame_count += 1
        self._check_global_timeout()

    def _check_global_timeout(self) -> None:
        """Checks if the scenario deadline has been exceeded."""
        if (
            self._scenario_deadline is not None
            and self.simulated_time > self._scenario_deadline
        ):
            raise TimeoutError("Scenario exceeded global simulated time limit")

    def _wait_frames(self, condition: WaitFrames) -> None:
        """Waits for a specified number of frames."""
        for _ in range(condition.frames):
            self._tick()

    def _wait_until(self, condition: WaitUntil) -> None:
        """Waits until a predicate is true or timeout."""
        start_time = self.simulated_time
        timeout = condition.timeout

        while not condition.predicate():
            if self.simulated_time - start_time > timeout:
                raise TimeoutError(f"Timed out waiting for: {condition.description}")
            self._tick()

    def run_for(self, seconds: float) -> None:
        """
        Runs the simulation for a specific amount of time.

        Args:
            seconds (float): Duration to run.
        """
        target_time = self.simulated_time + seconds
        # Avoid infinite loop if dt is 0 or something weird
        if self.fixed_dt <= 0:
            return

        while self.simulated_time < target_time:
            self._tick()

    def get_transform(self, entity_id: int) -> Optional[Any]:
        """
        Retrieves the Transform component for an entity.

        Args:
            entity_id (int): The entity ID.

        Returns:
            Optional[Transform]: The transform component.
        """
        from ..game.components import Transform

        if not self.world:
            return None
        return self.world.get_component(entity_id, Transform)

    def reset(self) -> None:
        """
        Resets the simulation state (clears entities).
        """
        if self.world:
            # Clear the ECS world to remove all entities
            self.world.clear_database()

        # Reset game setup flag so setup() runs again if needed (to create initial entities)
        # However, setup() also adds systems. If clear() keeps systems, we shouldn't re-add them.
        # But setup() creates initial entities (like Reimu).
        # We need a way to re-populate initial entities without re-adding systems.
        # Ideally, tests call setup() explicitly.

        # For now, we just clear entities. Tests that use reset() usually create their own entities.
        # If the game relies on singletons created in setup (like managers), they persist.

        self.simulated_time = 0.0
        self.frame_count = 0
        self._scenario_deadline = None

    @property
    def world(self) -> Any:
        """
        Retrieves the active ECS World.

        Returns:
            Any: The ECS World instance, or None.
        """
        if isinstance(self.game, Application):
            if self.game.scene_manager.current_scene:
                return self.game.scene_manager.current_scene.world
        if hasattr(self.game, "world"):
            return self.game.world
        return None

    def save_screenshot(self, filename: str) -> None:
        """
        Saves the current screen state to a file.

        Args:
            filename (str): The path to save the screenshot.
        """
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        if hasattr(self.game, "init_render_system_headless"):
            self.game.init_render_system_headless()

        # Force a render to the surface (logic loop doesn't do it)
        if hasattr(self.game, "render"):
            self.game.render()

        pygame.image.save(self.game.screen, filename)
