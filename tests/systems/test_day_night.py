"""
Unit tests for the DayNightSystem.
"""

import pytest
from unittest.mock import MagicMock, patch

from yukkuri_game.engine.ecs import World
from yukkuri_game.game.systems.day_night import DayNightSystem
from yukkuri_game.game.services import TimeService


class TestDayNightSystemInitialization:
    """Tests for DayNightSystem initialization."""

    def test_initialization(self) -> None:
        """DayNightSystem initializes with renderer and time service."""
        world = World()
        time_service = TimeService()
        world.services.register(time_service, TimeService)

        mock_renderer = MagicMock()
        system = DayNightSystem(world, mock_renderer)

        assert system.render_system == mock_renderer
        assert system.time_service == time_service


class TestColorInterpolation:
    """Tests for color interpolation logic."""

    def test_interpolate_color_no_change(self) -> None:
        """Interpolation at t=0 returns first color."""
        world = World()
        time_service = TimeService()
        world.services.register(time_service, TimeService)
        mock_renderer = MagicMock()
        system = DayNightSystem(world, mock_renderer)

        c1 = (100, 100, 100)
        c2 = (200, 200, 200)
        result = system._interpolate_color(c1, c2, 0.0)

        assert result == (100, 100, 100, 255)

    def test_interpolate_color_full_transition(self) -> None:
        """Interpolation at t=1 returns second color."""
        world = World()
        time_service = TimeService()
        world.services.register(time_service, TimeService)
        mock_renderer = MagicMock()
        system = DayNightSystem(world, mock_renderer)

        c1 = (100, 100, 100)
        c2 = (200, 200, 200)
        result = system._interpolate_color(c1, c2, 1.0)

        assert result == (200, 200, 200, 255)

    def test_interpolate_color_midpoint(self) -> None:
        """Interpolation at t=0.5 returns midpoint color."""
        world = World()
        time_service = TimeService()
        world.services.register(time_service, TimeService)
        mock_renderer = MagicMock()
        system = DayNightSystem(world, mock_renderer)

        c1 = (100, 100, 100)
        c2 = (200, 200, 200)
        result = system._interpolate_color(c1, c2, 0.5)

        assert result == (150, 150, 150, 255)


class TestAmbientColorCalculation:
    """Tests for ambient color based on time of day."""

    def test_midnight_color(self) -> None:
        """Midnight (0.0) returns dark blue color."""
        world = World()
        time_service = TimeService()
        world.services.register(time_service, TimeService)
        mock_renderer = MagicMock()
        system = DayNightSystem(world, mock_renderer)

        color = system._get_ambient_color(0.0)
        # Midnight is (40, 40, 70)
        assert color[:3] == (40, 40, 70)

    def test_noon_color(self) -> None:
        """Noon (12.0) returns full brightness."""
        world = World()
        time_service = TimeService()
        world.services.register(time_service, TimeService)
        mock_renderer = MagicMock()
        system = DayNightSystem(world, mock_renderer)

        color = system._get_ambient_color(12.0)
        # During day (8-17) is (255, 255, 255)
        assert color[:3] == (255, 255, 255)

    def test_morning_color(self) -> None:
        """Morning (8.0) returns full brightness."""
        world = World()
        time_service = TimeService()
        world.services.register(time_service, TimeService)
        mock_renderer = MagicMock()
        system = DayNightSystem(world, mock_renderer)

        color = system._get_ambient_color(8.0)
        assert color[:3] == (255, 255, 255)

    def test_dawn_transition(self) -> None:
        """Dawn (6.0) is transitioning from dark to light."""
        world = World()
        time_service = TimeService()
        world.services.register(time_service, TimeService)
        mock_renderer = MagicMock()
        system = DayNightSystem(world, mock_renderer)

        color = system._get_ambient_color(6.0)
        # 6.0 is (100, 100, 120)
        assert color[:3] == (100, 100, 120)

    def test_dusk_color(self) -> None:
        """Dusk (19.0) has reddish tint."""
        world = World()
        time_service = TimeService()
        world.services.register(time_service, TimeService)
        mock_renderer = MagicMock()
        system = DayNightSystem(world, mock_renderer)

        color = system._get_ambient_color(19.0)
        # 19.0 is (150, 100, 100)
        assert color[:3] == (150, 100, 100)

    def test_time_wrapping(self) -> None:
        """Time wraps correctly over 24 hours."""
        world = World()
        time_service = TimeService()
        world.services.register(time_service, TimeService)
        mock_renderer = MagicMock()
        system = DayNightSystem(world, mock_renderer)

        color_0 = system._get_ambient_color(0.0)
        color_24 = system._get_ambient_color(24.0)
        color_48 = system._get_ambient_color(48.0)

        # All should be midnight color
        assert color_0[:3] == color_24[:3] == color_48[:3]


class TestDayNightUpdate:
    """Tests for DayNightSystem update method."""

    def test_update_sets_ambient_light(self) -> None:
        """update() calls set_ambient_light on renderer."""
        world = World()
        time_service = TimeService()
        time_service.time_elapsed = 12.0 * 3600  # 12:00 noon in seconds
        world.services.register(time_service, TimeService)

        mock_renderer = MagicMock()
        mock_renderer.set_ambient_light = MagicMock()
        system = DayNightSystem(world, mock_renderer)

        system.update(world, 0.016)

        mock_renderer.set_ambient_light.assert_called_once()
        called_color = mock_renderer.set_ambient_light.call_args[0][0]
        # Should be full brightness at noon
        assert called_color[:3] == (255, 255, 255)

    def test_update_reads_time_service(self) -> None:
        """update() uses TimeService for current time."""
        world = World()
        time_service = TimeService()
        time_service.time_elapsed = 0.0  # Midnight (0:00)
        world.services.register(time_service, TimeService)

        mock_renderer = MagicMock()
        mock_renderer.set_ambient_light = MagicMock()
        system = DayNightSystem(world, mock_renderer)

        system.update(world, 0.016)

        called_color = mock_renderer.set_ambient_light.call_args[0][0]
        # Should be midnight color
        assert called_color[:3] == (40, 40, 70)

    def test_update_handles_missing_set_ambient_light(self) -> None:
        """update() doesn't crash if renderer lacks set_ambient_light."""
        world = World()
        time_service = TimeService()
        world.services.register(time_service, TimeService)

        # Renderer without set_ambient_light
        mock_renderer = MagicMock(spec=[])
        del mock_renderer.set_ambient_light
        system = DayNightSystem(world, mock_renderer)

        # Should not raise
        system.update(world, 0.016)
