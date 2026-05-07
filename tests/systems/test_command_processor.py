"""
Tests for CommandProcessorSystem and concrete GameCommand classes.

All tests run headlessly — no pygame display, no audio.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from yukkuri_game.engine.ecs import World
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.game.services import InputBufferService
from yukkuri_game.game.systems.command_processor_system import CommandProcessorSystem
from yukkuri_game.game.commands import (
    CameraAxisCommand,
    CameraZoomAxisCommand,
    CameraZoomCommand,
    CameraPanCommand,
    CancelPlacementCommand,
    CleanEntityCommand,
    SelectEntitiesCommand,
    TimeSpeedCommand,
)
from yukkuri_game.game.components import Transform, Selectable
from yukkuri_game.game.yukkuri_components import Poop
from yukkuri_game.game.services import InputService, TimeService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_world() -> World:
    """Creates a minimal World with EventBus and InputBufferService."""
    world = World()
    mock_bus = MagicMock(spec=EventBus)
    world.services.register(mock_bus, EventBus)
    buf = InputBufferService()
    world.services.register(buf, InputBufferService)
    return world


# ---------------------------------------------------------------------------
# CommandProcessorSystem tests
# ---------------------------------------------------------------------------


class TestCommandProcessorSystem:
    """Tests that CommandProcessorSystem drains and executes commands."""

    def test_executes_commands_in_order(self) -> None:
        """Commands are executed FIFO in a single frame."""
        world = _make_world()
        buf = world.services.get(InputBufferService)

        executed: list[int] = []

        class _Cmd:
            def __init__(self, n: int) -> None:
                self.n = n

            def execute(self, w: World) -> None:
                executed.append(self.n)

        buf.add_command(_Cmd(1))
        buf.add_command(_Cmd(2))
        buf.add_command(_Cmd(3))

        proc = CommandProcessorSystem()
        world.add_system(proc)
        world.update(0.016)

        assert executed == [1, 2, 3]

    def test_queue_is_empty_after_frame(self) -> None:
        """All commands are consumed within a single frame."""
        world = _make_world()
        buf = world.services.get(InputBufferService)

        class _NoOp:
            def execute(self, w: World) -> None:
                pass

        buf.add_command(_NoOp())
        buf.add_command(_NoOp())

        proc = CommandProcessorSystem()
        world.add_system(proc)
        world.update(0.016)

        assert buf.pop_all() == []

    def test_commands_added_during_execution_deferred(self) -> None:
        """Commands enqueued during execute() run in the *next* frame."""
        world = _make_world()
        buf = world.services.get(InputBufferService)

        secondary_ran = [False]

        class _Secondary:
            def execute(self, w: World) -> None:
                secondary_ran[0] = True

        class _Primary:
            def __init__(self, b: InputBufferService) -> None:
                self._b = b

            def execute(self, w: World) -> None:
                self._b.add_command(_Secondary())

        buf.add_command(_Primary(buf))

        proc = CommandProcessorSystem()
        world.add_system(proc)
        world.update(0.016)

        # Secondary should not yet have run
        assert secondary_ran[0] is False

        # Second frame executes it
        world.update(0.016)
        assert secondary_ran[0] is True


# ---------------------------------------------------------------------------
# CleanEntityCommand tests
# ---------------------------------------------------------------------------


class TestCleanEntityCommand:
    """Tests that CleanEntityCommand destroys poop entities in radius."""

    def test_destroys_poop_in_radius(self) -> None:
        """Poop within click_radius is destroyed."""
        world = _make_world()

        poop_id = world.create_entity(Poop(), Transform(x=10.0, y=10.0))

        cmd = CleanEntityCommand(wx=10.0, wy=10.0)
        cmd.execute(world)

        assert not world.entity_exists(poop_id)

    def test_does_not_destroy_out_of_radius(self) -> None:
        """Poop outside click_radius is left intact."""
        world = _make_world()

        poop_id = world.create_entity(Poop(), Transform(x=200.0, y=200.0))

        cmd = CleanEntityCommand(wx=10.0, wy=10.0)
        cmd.execute(world)

        assert world.entity_exists(poop_id)

    def test_destroys_multiple_poop_in_radius(self) -> None:
        """Multiple poop entities in radius are all destroyed."""
        world = _make_world()

        ids = [
            world.create_entity(Poop(), Transform(x=5.0, y=5.0)),
            world.create_entity(Poop(), Transform(x=15.0, y=15.0)),
        ]

        cmd = CleanEntityCommand(wx=10.0, wy=10.0)
        cmd.execute(world)

        for eid in ids:
            assert not world.entity_exists(eid)


# ---------------------------------------------------------------------------
# Camera command tests
# ---------------------------------------------------------------------------


class TestCameraCommands:
    """Tests that Camera commands update axis state on the Camera service."""

    def test_camera_axis_command(self) -> None:
        """CameraAxisCommand sets x/y axis on camera."""
        from yukkuri_game.game.camera import Camera

        world = _make_world()
        camera = Camera()
        world.services.register(camera, Camera)

        cmd = CameraAxisCommand(1.0, -1.0)
        cmd.execute(world)

        assert camera.input_axis_x == 1.0
        assert camera.input_axis_y == -1.0

    def test_camera_zoom_axis_command(self) -> None:
        """CameraZoomAxisCommand sets zoom_axis on camera."""
        from yukkuri_game.game.camera import Camera

        world = _make_world()
        camera = Camera()
        world.services.register(camera, Camera)

        cmd = CameraZoomAxisCommand(1.0)
        cmd.execute(world)

        assert camera.zoom_axis == 1.0

    def test_camera_zoom_command_clamps(self) -> None:
        """CameraZoomCommand clamps target zoom to valid bounds."""
        from yukkuri_game.game.camera import Camera

        world = _make_world()
        camera = Camera()
        world.services.register(camera, Camera)

        # Push target zoom way beyond max
        for _ in range(50):
            CameraZoomCommand(0.5).execute(world)

        assert camera.target_zoom <= camera.max_zoom

    def test_camera_pan_command(self) -> None:
        """CameraPanCommand moves camera_x and camera_y by delta/zoom."""
        from yukkuri_game.game.camera import Camera

        world = _make_world()
        camera = Camera()
        camera.zoom = 1.0
        world.services.register(camera, Camera)

        CameraPanCommand(dx=100, dy=50).execute(world)

        assert camera.camera_x == pytest.approx(-100.0)
        assert camera.camera_y == pytest.approx(-50.0)


# ---------------------------------------------------------------------------
# TimeSpeedCommand tests
# ---------------------------------------------------------------------------


class TestTimeSpeedCommand:
    """Tests that TimeSpeedCommand updates TimeService.game_speed."""

    def test_sets_game_speed(self) -> None:
        """TimeSpeedCommand correctly sets game speed."""
        world = _make_world()
        ts = TimeService()
        world.services.register(ts, TimeService)

        cmd = TimeSpeedCommand(2.0)
        cmd.execute(world)

        assert ts.game_speed == 2.0


# ---------------------------------------------------------------------------
# InputBufferService tests
# ---------------------------------------------------------------------------


class TestInputBufferService:
    """Unit tests for the InputBufferService queue mechanics."""

    def test_add_and_pop_all(self) -> None:
        """pop_all returns all added commands."""

        class _Cmd:
            def execute(self, w: World) -> None:
                pass

        buf = InputBufferService()
        c1, c2 = _Cmd(), _Cmd()
        buf.add_command(c1)
        buf.add_command(c2)

        result = buf.pop_all()
        assert result == [c1, c2]

    def test_pop_all_clears_queue(self) -> None:
        """After pop_all the buffer is empty."""

        class _Cmd:
            def execute(self, w: World) -> None:
                pass

        buf = InputBufferService()
        buf.add_command(_Cmd())
        buf.pop_all()

        assert buf.pop_all() == []
