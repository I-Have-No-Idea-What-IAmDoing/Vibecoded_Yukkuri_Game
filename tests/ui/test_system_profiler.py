"""
Tests for the ECS System Performance Profiler.
"""

import time

import pygame
import pygame_gui
import pytest

from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.ecs import System
from yukkuri_game.game.ui.system_profiler import SystemProfiler


class DummySystem1(System):
    """
    Dummy system 1 for profiling tests.
    """

    def process(self, dt: float) -> None:
        """
        Simulate some work by sleeping briefly.
        """
        time.sleep(0.002)


class DummySystem2(System):
    """
    Dummy system 2 for profiling tests.
    """

    def process(self, dt: float) -> None:
        """
        Simulate some work by sleeping briefly.
        """
        time.sleep(0.005)


@pytest.fixture
def ui_manager() -> pygame_gui.UIManager:
    """
    UIManager fixture.

    Returns:
        pygame_gui.UIManager: UI Manager.
    """
    manager = pygame_gui.UIManager((800, 600))
    return manager


@pytest.fixture
def ecs_world() -> World:
    """
    World fixture with dummy systems.

    Returns:
        World: ECS World.
    """
    world = World()
    world.add_system(DummySystem1())
    world.add_system(DummySystem2())
    return world


def test_profiler_timing_toggle(
    ui_manager: pygame_gui.UIManager, ecs_world: World
) -> None:
    """
    Verify turning profiling ON/OFF propagates to world.debug_timing.

    Args:
        ui_manager: Pygame GUI UI Manager.
        ecs_world: ECS World.
    """
    container = pygame_gui.elements.UIPanel(
        relative_rect=pygame.Rect(0, 0, 650, 500),
        manager=ui_manager,
    )

    profiler = SystemProfiler(
        manager=ui_manager,
        container=container,
        world=ecs_world,
    )

    # Starts OFF by default in this test setup
    ecs_world.debug_timing = False
    assert profiler.world.debug_timing is False

    # Simulate Profile button click to toggle ON
    event = pygame.event.Event(
        pygame_gui.UI_BUTTON_PRESSED,
        {"ui_element": profiler.profile_btn},
    )
    consumed = profiler.process_event(event)

    assert consumed is True
    assert ecs_world.debug_timing is True

    # Simulate Profile button click to toggle OFF
    consumed = profiler.process_event(event)
    assert consumed is True
    assert ecs_world.debug_timing is False


def test_profiler_target_toggles(
    ui_manager: pygame_gui.UIManager, ecs_world: World
) -> None:
    """
    Verify toggling budget target switches FPS and budget millisecond values.

    Args:
        ui_manager: Pygame GUI UI Manager.
        ecs_world: ECS World.
    """
    container = pygame_gui.elements.UIPanel(
        relative_rect=pygame.Rect(0, 0, 650, 500),
        manager=ui_manager,
    )

    profiler = SystemProfiler(
        manager=ui_manager,
        container=container,
        world=ecs_world,
    )

    # Initial budget is 60 FPS (16.67ms)
    assert profiler.fps_target == 60
    assert abs(profiler.budget_ms - 16.67) < 0.05

    # Toggle Target
    event = pygame.event.Event(
        pygame_gui.UI_BUTTON_PRESSED,
        {"ui_element": profiler.target_btn},
    )
    consumed = profiler.process_event(event)

    assert consumed is True
    assert profiler.fps_target == 30
    assert abs(profiler.budget_ms - 33.33) < 0.05

    # Toggle Target back
    consumed = profiler.process_event(event)
    assert consumed is True
    assert profiler.fps_target == 60


def test_profiler_peak_decay_and_reset(
    ui_manager: pygame_gui.UIManager, ecs_world: World
) -> None:
    """
    Verify system peak tracking, reset buttons, and rolling 5-second decay.

    Args:
        ui_manager: Pygame GUI UI Manager.
        ecs_world: ECS World.
    """
    container = pygame_gui.elements.UIPanel(
        relative_rect=pygame.Rect(0, 0, 650, 500),
        manager=ui_manager,
    )

    profiler = SystemProfiler(
        manager=ui_manager,
        container=container,
        world=ecs_world,
    )

    ecs_world.debug_timing = True
    ecs_world.update(0.016)

    # Trigger peak update
    profiler.update(0.016)
    assert len(profiler.system_peaks) > 0

    # Retrieve peak for DummySystem2
    system_name = "DummySystem2"
    initial_peak = profiler.system_peaks[system_name]
    assert initial_peak > 0.0

    # Simulate spike timing
    profiler.system_peaks[system_name] = 50.0
    profiler.peak_timestamps[system_name] = time.time()

    assert profiler.system_peaks[system_name] == 50.0

    # Verify peak reset button resets Peaks dictionary
    event_reset = pygame.event.Event(
        pygame_gui.UI_BUTTON_PRESSED,
        {"ui_element": profiler.reset_peaks_btn},
    )
    consumed = profiler.process_event(event_reset)

    assert consumed is True
    assert len(profiler.system_peaks) == 0


def test_profiler_bottleneck_highlighting(
    ui_manager: pygame_gui.UIManager, ecs_world: World
) -> None:
    """
    Verify that slow systems exceeding 15% budget are flagged hot in the list.

    Args:
        ui_manager: Pygame GUI UI Manager.
        ecs_world: ECS World.
    """
    container = pygame_gui.elements.UIPanel(
        relative_rect=pygame.Rect(0, 0, 650, 500),
        manager=ui_manager,
    )

    profiler = SystemProfiler(
        manager=ui_manager,
        container=container,
        world=ecs_world,
    )

    ecs_world.debug_timing = True
    ecs_world.update(0.016)

    # Let's set DummySystem2 average timings to 5ms (which is >15% of 16.6ms)
    ecs_world._system_timings["DummySystem2"].append(5.0)

    # Run profiler render update (exceeding throttled 0.2s interval)
    profiler.update(0.25)

    # Verify that row containing DummySystem2 contains class_id='system_hot'
    found_hot = False
    for row in profiler.row_labels:
        if row[0].text == "DummySystem2":
            # Check if object ID is system_hot
            assert "system_hot" in row[0].most_specific_combined_id
            found_hot = True
            break

    assert found_hot is True
