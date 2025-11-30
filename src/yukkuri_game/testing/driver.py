"""
Game Driver for automated testing.
"""
import random
import time
import pygame
import os
from typing import Generator, Any, Callable, Union, List, Optional
from dataclasses import dataclass
from ..engine.application import Application as YukkuriGame
from ..scenes.gameplay import GameplayScene

# --- Predicates & Commands ---

@dataclass
class WaitUntil:
    """Waits until a predicate returns True."""
    predicate: Callable[[], bool]
    timeout: float = 10.0
    description: str = "condition"

@dataclass
class WaitFrames:
    """Waits for a specific number of frames."""
    frames: int

@dataclass
class InjectInput:
    """Wraps a list of input events to inject."""
    events: List[pygame.event.Event]

@dataclass
class Screenshot:
    """Command to take a screenshot."""
    filename: str

# --- Input Helpers ---

def Click(x: int, y: int) -> InjectInput:
    """Creates a full click (Down + Up) event at x, y."""
    return InjectInput([
        pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (x, y), "button": 1}),
        pygame.event.Event(pygame.MOUSEBUTTONUP, {"pos": (x, y), "button": 1})
    ])

def KeyPress(key: int) -> InjectInput:
    """Creates a key press (Down + Up) event."""
    return InjectInput([
        pygame.event.Event(pygame.KEYDOWN, {"key": key}),
        pygame.event.Event(pygame.KEYUP, {"key": key})
    ])

# --- Driver ---

class GameDriver:
    """
    Controls a YukkuriGame instance for deterministic headless testing.
    """
    def __init__(self, game_instance: YukkuriGame, fixed_dt: float = 1.0/60.0):
        self.game = game_instance
        self.fixed_dt = fixed_dt
        self.simulated_time = 0.0
        self.frame_count = 0
        self._scenario_deadline: Optional[float] = None
        self._scene: Optional[GameplayScene] = None

    def seed_rng(self, seed: int = 42) -> None:
        """Seeds random number generators for determinism."""
        random.seed(seed)
        try:
            import numpy as np
            np.random.seed(seed)
        except ImportError:
            pass

    def setup(self) -> None:
        """Sets up the game instance."""
        self.seed_rng()
        # Headless mode is handled in Application.__init__

        # Initialize GameplayScene
        self._scene = GameplayScene(self.game)
        self.game.scene_manager.push(self._scene)

        # Ensure setup is called (SceneManager.push calls on_enter which calls setup)
        # But we want to ensure it's fully ready
        if not self._scene.is_setup:
            self._scene.setup()

    @property
    def world(self) -> Any:
        if self._scene:
            return self._scene.world
        # Fallback if accessed before setup, though unexpected
        return None

    def create_yukkuri(self, type_id: str, x: float, y: float) -> int:
        from ..game.entity_factory import EntityFactory
        if not self.world: return -1
        factory = self.world.services.try_get(EntityFactory)
        if factory:
            return factory.create_yukkuri(type_id, x, y)
        return -1

    def create_item(self, type_id: str, x: float, y: float) -> int:
        from ..game.entity_factory import EntityFactory
        if not self.world: return -1
        factory = self.world.services.try_get(EntityFactory)
        if factory:
            return factory.create_item(type_id, x, y)
        return -1

    def set_ai_target_pos(self, entity_id: int, x: float, y: float) -> None:
        from ..game.yukkuri_components import AIState
        if not self.world: return
        ai = self.world.get_component(entity_id, AIState)
        if ai:
            if ai.state_data is None:
                ai.state_data = {}
            ai.state_data["target_x"] = x
            ai.state_data["target_y"] = y
            ai.path = None
            ai.manual_override = True

    def set_ai_action(self, entity_id: int, action: str, target_id: int = -1) -> None:
        from ..game.yukkuri_components import AIState
        if not self.world: return
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

    def run_scenario(self, scenario_gen: Generator[Any, None, None], timeout: float = 10.0) -> None:
        """
        Runs a test scenario generator.
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
                elif callable(step):
                    step()
                else:
                     pass
        except Exception as e:
            self.save_screenshot(f"screenshots/failure_{self.frame_count}.png")
            raise e
        finally:
            self._scenario_deadline = None

    def _tick(self) -> None:
        """Advances the game by one fixed time step."""
        # 1. Handle Events
        # Application has handle_events
        self.game.handle_events()

        # 2. Update Game State
        self.game.update(self.fixed_dt)

        self.simulated_time += self.fixed_dt
        self.frame_count += 1
        self._check_global_timeout()

    def _check_global_timeout(self) -> None:
        if self._scenario_deadline is not None and self.simulated_time > self._scenario_deadline:
             raise TimeoutError("Scenario exceeded global simulated time limit")

    def _wait_frames(self, condition: WaitFrames) -> None:
        for _ in range(condition.frames):
            self._tick()

    def _wait_until(self, condition: WaitUntil) -> None:
        start_time = self.simulated_time
        timeout = condition.timeout

        while not condition.predicate():
            if self.simulated_time - start_time > timeout:
                raise TimeoutError(f"Timed out waiting for: {condition.description}")
            self._tick()

    def run_for(self, seconds: float) -> None:
        """Runs the simulation for a specific amount of time."""
        target_time = self.simulated_time + seconds
        # Avoid infinite loop if dt is 0 or something weird
        if self.fixed_dt <= 0:
            return

        while self.simulated_time < target_time:
            self._tick()

    def get_transform(self, entity_id: int) -> Optional[Any]:
        from ..game.components import Transform
        if not self.world: return None
        return self.world.get_component(entity_id, Transform)

    def reset(self) -> None:
        # Clear the ECS world to remove all entities
        if self.world:
            self.world.clear()
            # If we need to re-add systems, we might need to call setup again or reload the scene
            # But clearing the world removes entities, systems usually persist in SystemRegistry/World logic
            # (Wait, World.clear() usually clears entities but keeps systems if they are stored separately.
            # Let's check World implementation if possible. Assuming it clears entities.)

            # Re-initialize initial state if needed
            if self._scene:
                # Re-create Reimu?
                # start_x = float(self._scene.yukkurrium.width) / 2.0
                # start_y = float(self._scene.yukkurrium.height) / 2.0
                # self._scene.factory.create_yukkuri("reimu", start_x, start_y)
                pass

        self.simulated_time = 0.0
        self.frame_count = 0
        self._scenario_deadline = None

    def save_screenshot(self, filename: str) -> None:
        """Saves the current screen state to a file."""
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        # Force a render to the surface
        self.game.render()

        pygame.image.save(self.game.screen, filename)
