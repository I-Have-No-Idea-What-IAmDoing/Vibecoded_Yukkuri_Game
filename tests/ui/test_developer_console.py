"""
Tests for the Interactive Developer Console.
"""

from unittest.mock import MagicMock
from unittest.mock import patch
import pytest

import pygame_gui
from loguru import logger

from yukkuri_game.engine.ecs import World
from yukkuri_game.game.services import EconomyService
from yukkuri_game.game.ui.developer_console import DeveloperConsole
from yukkuri_game.game.ui.hud import HUD


@pytest.fixture
def ui_manager() -> pygame_gui.UIManager:
    """
    UIManager fixture.

    Returns:
        pygame_gui.UIManager: Headless UI Manager.
    """
    return pygame_gui.UIManager((800, 600))


@pytest.fixture
def world() -> World:
    """
    World fixture with mock economy and other services.

    Returns:
        World: ECS World.
    """
    world = World()
    economy = EconomyService(1000)
    world.services.register(economy, EconomyService)
    return world


@pytest.fixture
def mock_hud() -> MagicMock:
    """
    HUD mock fixture with selected entities.

    Returns:
        MagicMock: HUD Mock.
    """
    hud = MagicMock(spec=HUD)
    hud.selected_entities = []
    hud.scene = MagicMock()
    hud.scene.session_manager = MagicMock()
    hud.scene.session_manager.time_scale = 1.0
    hud.scene.session_manager.paused = False
    return hud


def test_console_toggle(
    ui_manager: pygame_gui.UIManager, world: World, mock_hud: MagicMock
) -> None:
    """
    Verify opening and closing developer console instantiates/kills windows.

    Args:
        ui_manager: UI Manager.
        world: ECS World.
        mock_hud: HUD Mock.
    """
    console = DeveloperConsole(ui_manager, world, mock_hud)
    assert console.is_open() is False

    console.open()
    assert console.is_open() is True
    assert console.window is not None
    assert console.input_line is not None

    console.close()
    assert console.is_open() is False
    assert console.window is None


def test_loguru_sink_captures_logs(
    ui_manager: pygame_gui.UIManager, world: World, mock_hud: MagicMock
) -> None:
    """
    Verify loguru logger info call registers inside output buffer.

    Args:
        ui_manager: UI Manager.
        world: ECS World.
        mock_hud: HUD Mock.
    """
    console = DeveloperConsole(ui_manager, world, mock_hud)
    console.open()

    logger.info("Test console logging message")
    assert "Test console logging message" in console.output_buffer

    console.close()


def test_slash_command_clear(
    ui_manager: pygame_gui.UIManager, world: World, mock_hud: MagicMock
) -> None:
    """
    Verify slash clear command wipes the output buffer.

    Args:
        ui_manager: UI Manager.
        world: ECS World.
        mock_hud: HUD Mock.
    """
    console = DeveloperConsole(ui_manager, world, mock_hud)
    console.open()

    console.execute_command("/clear")
    assert console.output_buffer == ""

    console.close()


def test_slash_command_money(
    ui_manager: pygame_gui.UIManager, world: World, mock_hud: MagicMock
) -> None:
    """
    Verify slash money command adjusts EconomyService money.

    Args:
        ui_manager: UI Manager.
        world: ECS World.
        mock_hud: HUD Mock.
    """
    console = DeveloperConsole(ui_manager, world, mock_hud)
    console.open()

    economy = world.services.get(EconomyService)
    assert economy.money == 1000

    # Set direct value
    console.execute_command("/money 5000")
    assert economy.money == 5000

    # Add relative value
    console.execute_command("/money +1500")
    assert economy.money == 6500

    # Subtract relative value
    console.execute_command("/money -500")
    assert economy.money == 6000

    console.close()


def test_slash_command_speed(
    ui_manager: pygame_gui.UIManager, world: World, mock_hud: MagicMock
) -> None:
    """
    Verify slash speed command adjusts session_manager time scale.

    Args:
        ui_manager: UI Manager.
        world: ECS World.
        mock_hud: HUD Mock.
    """
    console = DeveloperConsole(ui_manager, world, mock_hud)
    console.open()

    assert mock_hud.scene.session_manager.time_scale == 1.0

    console.execute_command("/speed 3.5")
    assert mock_hud.scene.session_manager.time_scale == 3.5

    console.close()


def test_slash_command_pause(
    ui_manager: pygame_gui.UIManager, world: World, mock_hud: MagicMock
) -> None:
    """
    Verify slash pause command toggles paused state in session_manager.

    Args:
        ui_manager: UI Manager.
        world: ECS World.
        mock_hud: HUD Mock.
    """
    console = DeveloperConsole(ui_manager, world, mock_hud)
    console.open()

    # Toggle Pause
    console.execute_command("/pause")
    mock_hud.scene.session_manager.toggle_pause.assert_called_once()

    console.close()


def test_slash_command_spawn(
    ui_manager: pygame_gui.UIManager, world: World, mock_hud: MagicMock
) -> None:
    """
    Verify slash spawn command attempts to call prefab spawner.

    Args:
        ui_manager: UI Manager.
        world: ECS World.
        mock_hud: HUD Mock.
    """
    console = DeveloperConsole(ui_manager, world, mock_hud)
    console.open()

    with patch(
        "yukkuri_game.game.prefabs.yukkuri.create_yukkuri"
    ) as mock_create:
        console.execute_command("/spawn reimu 150.0 250.0")
        mock_create.assert_called_once_with(world, "reimu", 150.0, 250.0)

    console.close()


def test_slash_command_kill(
    ui_manager: pygame_gui.UIManager, world: World, mock_hud: MagicMock
) -> None:
    """
    Verify slash kill command destroys active entities.

    Args:
        ui_manager: UI Manager.
        world: ECS World.
        mock_hud: HUD Mock.
    """
    console = DeveloperConsole(ui_manager, world, mock_hud)
    console.open()

    entity_id = world.create_entity()
    assert world.entity_exists(entity_id) is True

    console.execute_command(f"/kill {entity_id}")
    world.commands.apply_all()
    assert world.entity_exists(entity_id) is False

    console.close()


def test_slash_command_set(
    ui_manager: pygame_gui.UIManager, world: World, mock_hud: MagicMock
) -> None:
    """
    Verify slash set command modifies component statistics on selected entities.

    Args:
        ui_manager: UI Manager.
        world: ECS World.
        mock_hud: HUD Mock.
    """
    console = DeveloperConsole(ui_manager, world, mock_hud)
    console.open()

    from yukkuri_game.game.components import YukkuriStats
    stats = YukkuriStats(name="TestReimu", type_id="reimu")
    entity_id = world.create_entity(stats)
    mock_hud.selected_entities = [entity_id]

    assert stats.discipline == 0.0

    console.execute_command("/set discipline 55.5")
    assert stats.discipline == 55.5

    console.close()


def test_raw_python_eval(
    ui_manager: pygame_gui.UIManager, world: World, mock_hud: MagicMock
) -> None:
    """
    Verify raw python expression evaluation returns correct repr.

    Args:
        ui_manager: UI Manager.
        world: ECS World.
        mock_hud: HUD Mock.
    """
    console = DeveloperConsole(ui_manager, world, mock_hud)
    console.open()

    console.execute_command("10 * 10")
    assert "100" in console.output_buffer

    console.close()


def test_python_print_redirection(
    ui_manager: pygame_gui.UIManager, world: World, mock_hud: MagicMock
) -> None:
    """
    Verify python print calls redirect inside the console output box.

    Args:
        ui_manager: UI Manager.
        world: ECS World.
        mock_hud: HUD Mock.
    """
    console = DeveloperConsole(ui_manager, world, mock_hud)
    console.open()

    console.execute_command("print('Hello Console Print!')")
    assert "Hello Console Print!" in console.output_buffer

    console.close()


def test_python_syntax_error_graceful(
    ui_manager: pygame_gui.UIManager, world: World, mock_hud: MagicMock
) -> None:
    """
    Verify syntactically broken code displays exception traceback.

    Args:
        ui_manager: UI Manager.
        world: ECS World.
        mock_hud: HUD Mock.
    """
    console = DeveloperConsole(ui_manager, world, mock_hud)
    console.open()

    # Syntax Error
    console.execute_command("invalid variable syntax @!*")
    assert "SyntaxError" in console.output_buffer

    console.close()


def test_python_help_override(
    ui_manager: pygame_gui.UIManager, world: World, mock_hud: MagicMock
) -> None:
    """
    Verify entering 'help()' evaluates without locking/blocking.

    Args:
        ui_manager: UI Manager.
        world: ECS World.
        mock_hud: HUD Mock.
    """
    console = DeveloperConsole(ui_manager, world, mock_hud)
    console.open()

    console.execute_command("help()")
    assert "Available Console Commands" in console.output_buffer

    console.close()


def test_input_manager_clear_pressed_states(
    ui_manager: pygame_gui.UIManager, world: World, mock_hud: MagicMock
) -> None:
    """
    Verify that InputManager's clear_pressed_states clears active states.

    Args:
        ui_manager: UI Manager.
        world: ECS World.
        mock_hud: HUD Mock.
    """
    from yukkuri_game.engine.input_manager import InputManager
    import pygame

    im = InputManager()
    world.services.register(im, InputManager)

    # Mock some pressed states
    im._keys_pressed.add(pygame.K_w)
    im._keys_down.add(pygame.K_w)
    im._mouse_wheel = 1.0

    assert pygame.K_w in im._keys_pressed
    assert im._mouse_wheel == 1.0

    im.clear_pressed_states()

    assert not im._keys_pressed
    assert not im._keys_down
    assert im._mouse_wheel == 0.0

    world.services.unregister(InputManager)
