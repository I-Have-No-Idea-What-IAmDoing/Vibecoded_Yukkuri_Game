"""
Game Driver for automated testing.
"""

from ..engine import rng
import pygame
import os
import io
import types
from typing import Any, cast, TypeVar
from collections.abc import Generator, Callable
from dataclasses import dataclass
from collections import deque
from loguru import logger
from ..engine.application import Application
from ..engine.event_bus import Event
from yukkuri_game.engine.services.time_service import TimeService
from yukkuri_game.engine.components import Transform


T = TypeVar("T")
E = TypeVar("E", bound=Event)

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

    events: list[pygame.event.Event]


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

    scene_type: type
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


class LogCapture:
    """
    Captures log records for assertion.
    """

    def __init__(self) -> None:
        """Initializes the log capture."""
        self.records: list[str] = []
        self.handler_id: int | None = None

    def __enter__(self) -> "LogCapture":
        """Starts capturing log records."""
        self.handler_id = logger.add(
            lambda msg: self.records.append(msg), format="{message}"
        )
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Stops capturing log records."""
        if self.handler_id is not None:
            logger.remove(self.handler_id)

    def assert_logged(self, message_substring: str) -> None:
        """Asserts that a message containing the substring was logged."""
        found = any(message_substring in str(record) for record in self.records)
        assert found, (
            f"Expected log containing '{message_substring}' not found. Logs: {self.records}"
        )

    def assert_not_logged(self, message_substring: str) -> None:
        """Asserts that a message containing the substring was NOT logged."""
        found = any(message_substring in str(record) for record in self.records)
        assert not found, (
            f"Expected no log containing '{message_substring}', but found it."
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
        self._scenario_deadline: float | None = None
        self.event_history: deque[Event] = deque(maxlen=100)
        self._original_publish: Callable[[Event], None] | None = None
        self._rng_seeded = False

    def seed_rng(self, seed: int = 42) -> None:
        """
        Seeds random number generators for determinism.

        Args:
            seed (int): The seed value.
        """
        rng.seed(seed)
        self._rng_seeded = True
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
        if not self._rng_seeded:
            self.seed_rng()
        if hasattr(self.game, "set_headless") and not self.game.headless:
            # Cast to Any to allow calling method detected via hasattr
            cast(Any, self.game).set_headless(True)

        # Hook event bus for logging
        if isinstance(self.game, Application) and hasattr(self.game, "event_manager"):
            # Ensure we don't double-patch if setup() is called again (e.g. reload_scene)
            if self._original_publish is None:
                self._original_publish = self.game.event_manager.bus.publish
                original_publish = self._original_publish

                def intercepted_publish(event: Event) -> None:
                    self.event_history.append(event)
                    original_publish(event)

                setattr(self.game.event_manager.bus, "publish", cast(Any, intercepted_publish))

        # Application initializes on creation. Ensure GameplayScene is active.
        if isinstance(self.game, Application):
            from ..scenes.gameplay import GameplayScene

            if not self.game.scene_manager.current_scene:
                self.game.scene_manager.push(GameplayScene(self.game))
        elif hasattr(self.game, "setup"):
            self.game.setup()

    def reload_scene(self, scene_type: type | None = None) -> None:
        """
        Reloads the current scene or switches to a new scene type.
        Ensures a clean state for the scene.

        Args:
            scene_type (Optional[Type]): The scene class to load. If None, reloads current.
        """
        if not isinstance(self.game, Application):
            return

        if scene_type is None:
            if self.game.scene_manager.current_scene:
                scene_type = type(self.game.scene_manager.current_scene)
            else:
                from ..scenes.gameplay import GameplayScene

                scene_type = GameplayScene

        if self.game.scene_manager.current_scene:
            self.game.scene_manager.pop()

        # Create and push new scene
        # We assume scene constructor takes 'game' as first arg
        new_scene = scene_type(self.game)
        self.game.scene_manager.push(new_scene)

        self.setup()

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
            logger.error("create_yukkuri failed: No World")
            return -1
        factory = self.world.services.try_get(EntityFactory)
        if factory:
            try:
                return int(factory.create_yukkuri(type_id, x, y))
            except Exception as e:
                logger.error(f"create_yukkuri failed with exception: {e}")
                return -1

        logger.error("create_yukkuri failed: No EntityFactory in services")
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
        from ..game.components import AIState

        if not self.world:
            return
        ai = self.world.try_get_component(entity_id, AIState)
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
        from ..game.components import AIState

        if not self.world:
            return
        ai = self.world.try_get_component(entity_id, AIState)
        if ai:
            ai.current_action = action
            if target_id != -1:
                ai.current_target_id = target_id
            ai.path = None
            ai.manual_override = True

    def cleanup(self) -> None:
        """Cleans up the game instance."""
        # Restore original event bus publish to break circular reference
        if (
            self._original_publish is not None
            and isinstance(self.game, Application)
            and hasattr(self.game, "event_manager")
        ):
            setattr(self.game.event_manager.bus, "publish", self._original_publish)
            self._original_publish = None

        if hasattr(self.game, "quit"):
            self.game.quit()
        # Break reference cycle to allow garbage collection
        self.game = None  # type: ignore[assignment]

    def wait_until_scene(self, scene_type: type, timeout: float = 10.0) -> None:
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

    def get_entities_with(self, *components: type) -> list[int]:
        """
        Returns a list of entity IDs that have all specified components.

        Args:
            *components (Type): Component classes.

        Returns:
            List[int]: List of entity IDs.
        """
        if self.world:
            return cast(list[int], self.world.get_entities_with(*components))
        return []

    def assert_entity_count(self, count: int, *components: type) -> None:
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

    def get_events(self, event_type: type[E]) -> list[E]:
        """
        Returns all captured events of a specific type.
        
        Args:
            event_type (type[E]): The event class to filter by.
            
        Returns:
            list[E]: A list of matching events.
        """
        return [e for e in self.event_history if isinstance(e, event_type)]

    def assert_event_published(self, event_type: type[E], count: int | None = None) -> None:
        """
        Asserts that an event of the given type was published.
        
        Args:
            event_type (type[E]): The event class to check.
            count (int | None): The exact number of times it should have been published. 
                                Default is None (which means > 0 times).
        """
        events = self.get_events(event_type)
        if count is None:
            assert len(events) > 0, f"Expected event {event_type.__name__} was never published."
        else:
            assert len(events) == count, f"Expected {event_type.__name__} to be published {count} times, but was {len(events)} times."

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

                if hasattr(self.game, "running") and not self.game.running:
                    raise RuntimeError("Game stopped running before step execution")

                if isinstance(step, WaitUntil):
                    self._wait_until(step)
                elif isinstance(step, WaitFrames):
                    self._wait_frames(step)
                elif isinstance(step, InjectInput):
                    # Direct injection for robustness
                    if isinstance(self.game, Application):
                        for event in step.events:
                            self.game.input_manager.process_event(event)
                            self.game.ui_manager.process_events(event)
                            self.game.scene_manager.handle_event(event)
                    else:
                        # Fallback for generic games
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
            try:
                self.save_screenshot(f"screenshots/failure_{self.frame_count}.png")
            except Exception as se:
                logger.warning(f"Could not save failure screenshot: {se}")

            # Dump logs/events
            log_filename = f"screenshots/failure_{self.frame_count}.log"
            os.makedirs(os.path.dirname(log_filename), exist_ok=True)
            with open(log_filename, "w") as f:
                f.write(f"Exception: {e}\n")
                f.write("Last 100 Events:\n")
                for evt in self.event_history:
                    f.write(f"{evt}\n")
                f.write("\nState Dump:\n")
                f.write(self.dump_state())
            raise e
        finally:
            self._scenario_deadline = None

    def _tick(self) -> None:
        """Advances the game by one fixed time step."""
        if hasattr(self.game, "running") and not self.game.running:
            raise RuntimeError("Game stopped running during simulation tick")

        # Process events each tick
        if hasattr(self.game, "handle_events"):
            cast(Any, self.game).handle_events()
        elif hasattr(self.game, "process_events"):
            cast(Any, self.game).process_events()
        else:
            pygame.event.pump()

        # Check again if game stopped running after event processing
        if hasattr(self.game, "running") and not self.game.running:
            raise RuntimeError("Game stopped running after event processing")

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

    def run_until(self, predicate: Callable[[], bool], timeout: float = 10.0, description: str = "condition") -> None:
        """
        Runs the simulation until the predicate returns True or timeout occurs.
        
        Args:
            predicate (Callable[[], bool]): The condition to wait for.
            timeout (float): The maximum simulated time (in seconds) to wait. Defaults to 10.0.
            description (str): A description of the condition for error messages.
        """
        self._wait_until(WaitUntil(predicate, timeout, description))

    def get_transform(self, entity_id: int) -> Any | None:
        """
        Retrieves the Transform component for an entity.

        Args:
            entity_id (int): The entity ID.

        Returns:
            Optional[Transform]: The transform component.
        """

        if not self.world:
            return None
        return self.world.try_get_component(entity_id, Transform)

    def get_component(self, entity_id: int, comp_type: type[T]) -> T | None:
        """
        Retrieves a specific component from an entity.

        Args:
            entity_id (int): The entity ID.
            comp_type (Type[T]): The class of the component.

        Returns:
            Optional[T]: The component, or None if not found.
        """
        if not self.world:
            return None
        return cast(T | None, self.world.try_get_component(entity_id, comp_type))

    def assert_component(self, entity_id: int, comp_type: type[T], predicate: Callable[[T], bool], message: str = "") -> None:
        """
        Asserts that a component satisfies a given condition.

        Args:
            entity_id (int): The entity ID.
            comp_type (Type[T]): The class of the component.
            predicate (Callable[[T], bool]): The condition to check.
            message (str): Optional context message for the assertion error.
        """
        comp = self.get_component(entity_id, comp_type)
        assert comp is not None, f"Entity {entity_id} does not have component {comp_type.__name__}"
        assert predicate(comp), f"Assertion failed for {comp_type.__name__} on entity {entity_id}: {message}"

    def reset(self) -> None:
        """
        Resets the simulation state (clears entities).
        """
        if self.world:
            # Clear the ECS world to remove all entities
            self.world.clear_database()
            # Also reset services that accumulate data if needed
            time_service = self.world.services.try_get(TimeService)
            if time_service:
                time_service.time_elapsed = 0.0

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

        if hasattr(self.game, "scene_manager"):
            _raw = self.game.scene_manager.current_scene
            if _raw and hasattr(_raw, "init_render_system_headless"):
                scene_any: Any = _raw
                scene_any.init_render_system_headless()

        # Force a render to the surface (logic loop doesn't do it)
        # Manually render for screenshots, bypassing Application.render's headless check
        if self.game and self.game.screen:
            self.game.screen.fill((0, 0, 0))
            if hasattr(self.game, "scene_manager"):
                # Pass alpha=1.0 for full interpolation
                try:
                    getattr(self.game.scene_manager, "render")(1.0)
                except TypeError:
                    getattr(self.game.scene_manager, "render")()

        if self.game and hasattr(self.game, "screen") and self.game.screen:
            pygame.image.save(self.game.screen, filename)

    def compare_screenshot(
        self,
        filename: str,
        reference_filename: str,
        tolerance: float = 0.01,
        drift_threshold: int = 5,
    ) -> bool:
        """Compares the current screen against a reference image.

        Saves a screenshot and compares it with a reference image. If the
        comparison fails, it raises an AssertionError containing absolute
        clickable paths for the reference, actual, and diff mask images.

        Args:
            filename: Where to save the current screenshot.
            reference_filename: Path to the reference image.
            tolerance: Percentage of allowed mismatched pixels (0.0 to 1.0).
            drift_threshold: Maximum color channel difference value (0 to 255).

        Returns:
            True if images match within tolerance.

        Raises:
            AssertionError: If images mismatch in dimensions or pixels.
        """
        self.save_screenshot(filename)

        if not os.path.exists(reference_filename):
            logger.warning(
                f"Reference screenshot {reference_filename} not found. "
                "Comparison skipped (assumed new test)."
            )
            return True

        current_img = pygame.image.load(filename)
        ref_img = pygame.image.load(reference_filename)

        curr_abs = os.path.abspath(filename)
        ref_abs = os.path.abspath(reference_filename)

        if current_img.get_size() != ref_img.get_size():
            err_msg = (
                "Visual Regression Dimension Mismatch!\n"
                f"Expected size: {ref_img.get_size()}\n"
                f"Actual size:   {current_img.get_size()}\n"
                "--------------------------------------------------------\n"
                f"Expected (Reference): file:///{ref_abs}\n"
                f"Actual (Failed):      file:///{curr_abs}\n"
                "--------------------------------------------------------"
            )
            logger.error(err_msg)
            raise AssertionError(err_msg)

        width, height = current_img.get_size()
        total_pixels = width * height

        try:
            # Create fresh contiguous software surfaces to guarantee memory layout
            curr_surf = pygame.Surface(current_img.get_size(), depth=32)
            curr_surf.blit(current_img, (0, 0))
            ref_surf = pygame.Surface(ref_img.get_size(), depth=32)
            ref_surf.blit(ref_img, (0, 0))

            curr_view = curr_surf.get_view("2")
            ref_view = ref_surf.get_view("2")

            # Fast check
            if curr_view.raw == ref_view.raw:
                return True

            import numpy as np

            arr1 = pygame.surfarray.array3d(curr_surf)
            arr2 = pygame.surfarray.array3d(ref_surf)

            # Compute pixel mismatches exceeding drift_threshold (using signed ints to prevent uint8 underflow)
            diff = np.abs(arr1.astype(np.int32) - arr2.astype(np.int32))
            mismatched = np.any(diff > drift_threshold, axis=2)
            num_diff = np.count_nonzero(mismatched)

            # Calculate difference ratio
            diff_ratio = num_diff / total_pixels
            logger.info(f"Image comparison diff ratio: {diff_ratio:.4f}")

            if diff_ratio > tolerance:
                # Generate diff mask array
                diff_mask = np.zeros((width, height, 3), dtype=np.uint8)
                diff_mask[mismatched] = [255, 0, 255]

                # Convert to surface and save
                diff_surf = pygame.surfarray.make_surface(diff_mask)
                diff_filename = filename.rsplit(".", 1)[0] + "_diff.png"
                pygame.image.save(diff_surf, diff_filename)
                diff_abs = os.path.abspath(diff_filename)

                err_msg = (
                    "Visual Regression Mismatch Detected!\n"
                    f"Difference Ratio: {diff_ratio:.4%} "
                    f"(Allowed Tolerance: {tolerance:.4%})\n"
                    "--------------------------------------------------------\n"
                    f"Expected (Reference): file:///{ref_abs}\n"
                    f"Actual (Failed):      file:///{curr_abs}\n"
                    f"Difference Mask:      file:///{diff_abs}\n"
                    "--------------------------------------------------------"
                )
                logger.error(err_msg)
                raise AssertionError(err_msg)

            return True

        except ImportError:
            logger.warning(
                "Numpy not found for advanced comparison. "
                "Falling back to strict buffer check."
            )
            # Strict raw check already failed if we reached here
            err_msg = (
                "Visual Regression Mismatch (Strict Buffer Check Failed)!\n"
                "Numpy is not available to compute tolerant differences.\n"
                "--------------------------------------------------------\n"
                f"Expected (Reference): file:///{ref_abs}\n"
                f"Actual (Failed):      file:///{curr_abs}\n"
                "--------------------------------------------------------"
            )
            logger.error(err_msg)
            raise AssertionError(err_msg)

        except Exception as e:
            if isinstance(e, AssertionError):
                raise
            err_msg = f"Comparison failed with error: {e}"
            logger.error(err_msg)
            raise AssertionError(err_msg) from e

    def dump_state(self) -> str:
        """
        Dumps the ECS world state to a string.
        Sanitizes memory addresses for determinism.

        Returns:
            str: The string representation of the world state.
        """
        if not self.world:
            return "No World Active"

        output = io.StringIO()
        output.write(f"Simulated Time: {self.simulated_time:.2f}\n")
        output.write(f"Frame Count: {self.frame_count}\n")
        output.write("Entities:\n")

        for entity_id in self.world.get_all_entities():
            output.write(f"  Entity {entity_id}:\n")

            components_tuple = self.world.get_all_components(entity_id)
            # Sort components by type name for deterministic output
            sorted_components = sorted(components_tuple, key=lambda c: type(c).__name__)
            for comp in sorted_components:
                output.write(f"    {type(comp).__name__}: {comp}\n")

        import re

        # Mask memory addresses like 0x0000012A4AC61F20
        # Pattern: 0x followed by 8-16 hex digits
        cleaned = re.sub(r"0x[0-9a-fA-F]{8,}", "0xMASKED", output.getvalue())
        # Also mask CData object refs if needed: <... object at 0x...>
        cleaned = re.sub(r" at 0x[0-9a-fA-F]+", " at 0xMASKED", cleaned)

        return cleaned

    def capture_logs(self) -> LogCapture:
        """
        Context manager to capture logs for assertions.

        Returns:
            LogCapture: The capture object.
        """
        return LogCapture()
