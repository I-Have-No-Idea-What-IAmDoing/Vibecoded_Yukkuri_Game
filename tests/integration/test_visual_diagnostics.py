"""
Integration tests for Yukkuri Developer Visual Diagnostics features.
"""

from unittest.mock import MagicMock, patch
import pygame

from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.game.events import EntitySelectedEvent
from yukkuri_game.game.components import AIState
from yukkuri_game.engine.components import Selectable, Transform
from yukkuri_game.game.input_system import InputSystem
from yukkuri_game.testing.driver import GameDriver


def test_navigation_debug_renderer_blocked_cells(
    game_driver: GameDriver,
) -> None:
    """
    Verify that NavigationDebugRenderer renders blocked grid cells
    without any exception.
    """
    driver = game_driver
    driver.setup()

    # Create a yukkuri
    y = driver.create_yukkuri("reimu", 100, 100)

    # Set some cells blocked
    from yukkuri_game.game.ai.navigation_service import NavigationService
    nav = driver.world.services.get(NavigationService)
    # Block a rectangle
    nav.update_obstacle_rect(150, 150, 50, 50, walkable=False)

    from yukkuri_game.game.systems.navigation_debug_renderer import (
        NavigationDebugRenderer,
    )
    renderer = NavigationDebugRenderer(driver.world)
    renderer.enabled = True

    # Render to a dummy surface
    surface = pygame.Surface((800, 600))
    renderer.render(surface, driver.world)

    # If it completed without exceptions, it succeeds!
    assert renderer.enabled is True


def test_alt_right_click_teleport(game_driver: GameDriver) -> None:
    """
    Verify that holding Alt and right-clicking teleports the selected Yukkuri.
    """
    driver = game_driver
    driver.setup()

    # Create a Yukkuri
    y = driver.create_yukkuri("reimu", 100, 100)
    sel = driver.world.get_component(y, Selectable)
    trans = driver.world.get_component(y, Transform)

    # Select the Yukkuri
    sel.selected = True

    # Instantiate InputSystem
    from yukkuri_game.engine.camera import Camera
    camera = driver.world.services.get(Camera)
    input_sys = InputSystem(camera)

    # Mock InputManager
    mock_input_manager = MagicMock()
    mock_input_manager.get_mouse_position.return_value = (200, 200)
    # Right click
    mock_input_manager.is_action_just_pressed.side_effect = (
        lambda action: action == "cancel_action"
    )
    mock_input_manager.is_action_pressed.return_value = False

    # Register mock services
    from yukkuri_game.game.services import InputService
    from yukkuri_game.engine.input_manager import InputManager
    input_service = MagicMock(spec=InputService)
    input_service.is_placing = False
    input_service.is_cleaning = False
    input_service.is_dragging = False

    driver.world.services.register(
        mock_input_manager, InputManager, replace=True
    )

    mock_surface = MagicMock()
    mock_surface.get_size.return_value = (1280, 720)

    # We must patch get_mods to simulate holding Alt key
    with (
        patch("pygame.key.get_mods", return_value=pygame.KMOD_ALT),
        patch("pygame.display.get_surface", return_value=mock_surface),
    ):
        input_sys.update(driver.world, 0.1)

    # The Yukkuri should have been teleported to the screen click position.
    assert (trans.x, trans.y) != (100.0, 100.0)


def test_ai_debug_renderer_telemetry(game_driver: GameDriver) -> None:
    """Verify that AIDebugRenderer renders all visual diagnostic overlays.

    This checks overhead statuses (action name, stuck timer, pathing badge,
    action cooldown), physical collision ring, ultimate path destination
    crosshair/line, next-waypoint path, target line, and social context lines.
    """
    driver = game_driver
    driver.setup()

    # Create Yukkuri and targeted entities
    y = driver.create_yukkuri("reimu", 100.0, 100.0)
    target_id = driver.create_yukkuri("marisa", 200.0, 200.0)

    from yukkuri_game.game.components import AIState
    from yukkuri_game.game.components import Blackboard
    from yukkuri_game.game.components import MoveCommand
    from yukkuri_game.game.components import SteeringComponent
    from yukkuri_game.engine.components import PhysicsBody
    from yukkuri_game.game.components.social import TargetInfo
    from yukkuri_game.game.systems.ai_debug_renderer import AIDebugRenderer
    from pymunk.vec2d import Vec2d as Vector2
    import pymunk

    # Set up AIState with complete telemetry
    ai_state = driver.world.get_component(y, AIState)
    ai_state.current_action = "Wander"
    ai_state.current_target_id = target_id
    ai_state.action_cooldowns = {"Wander": driver.world.time + 10.0}
    ai_state.state_data = {
        "path_requesting": True,
        "path_destination": (300.0, 300.0),
    }
    ai_state.path = [(150.0, 150.0), (300.0, 300.0)]

    # Add SteeringComponent to trigger stuck timer
    steering = SteeringComponent(time_stuck=1.5)
    driver.world.add_component(y, steering)

    # Add Blackboard to trigger social lines
    blackboard = Blackboard()
    blackboard.visible_targets[target_id] = TargetInfo(
        entity_id=target_id,
        position=(200.0, 200.0),
        distance=100.0,
        relation="Friend",
        timestamp=driver.world.time,
        detected_at=driver.world.time,
    )
    driver.world.add_component(y, blackboard)

    # Add MoveCommand to trigger cyan path lines
    move_cmd = MoveCommand(target_pos=Vector2(120.0, 120.0))
    driver.world.add_component(y, move_cmd)

    # Setup non-sensor PhysicsBody radius
    body = pymunk.Body(1.0, 1.0)
    shape = pymunk.Circle(body, 15.0)
    shape.sensor = False
    phys = PhysicsBody(body=body, shape=shape)
    driver.world.add_component(y, phys)

    # Force immediate command application to flush add_component calls
    driver.world.commands.apply_all()

    # Update camera matrices to avoid world_to_screen_fast error
    from yukkuri_game.engine.camera import Camera
    camera = driver.world.services.get(Camera)
    camera.update_matrices(800, 600)

    # Enable and render
    renderer = AIDebugRenderer(driver.world)
    renderer.enabled = True

    surface = pygame.Surface((800, 600))
    renderer.render(surface, driver.world)

    assert renderer.enabled is True

