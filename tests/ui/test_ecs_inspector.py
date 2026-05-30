"""
Tests for the ECS Entity Inspector & Query Tool.
"""

import pygame
import pygame_gui
import pymunk
import pytest

from yukkuri_game.engine.components import PhysicsBody
from yukkuri_game.engine.components import Transform
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.ui.ecs_inspector import ECSInspector


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
    World fixture.

    Returns:
        World: ECS World.
    """
    world = World()
    return world


def test_ecs_inspector_query_filtering(
    ui_manager: pygame_gui.UIManager, ecs_world: World
) -> None:
    """
    Verify that query filtering by component presence works correctly.

    Args:
        ui_manager: Pygame GUI UI Manager.
        ecs_world: ECS World.
    """
    # Create test entities
    entity_1 = ecs_world.create_entity(
        Transform(x=100.0, y=200.0),
        PhysicsBody(body=pymunk.Body(), shape=pymunk.Circle(pymunk.Body(), 10)),
    )
    ecs_world.create_entity(Transform(x=300.0, y=400.0))

    container = pygame_gui.elements.UIPanel(
        relative_rect=pygame.Rect(0, 0, 450, 410),
        manager=ui_manager,
    )

    inspector = ECSInspector(
        manager=ui_manager,
        container=container,
        world=ecs_world,
    )

    # Initial query matches both entities
    assert len(inspector.entity_buttons) == 2

    # Query for 'physics'
    inspector.search_query = "physics"
    inspector._refresh_entity_list()
    # Should only match entity 1
    assert len(inspector.entity_buttons) == 1
    assert list(inspector.entity_buttons.values()) == [entity_1]

    # Query for 'transform'
    inspector.search_query = "transform"
    inspector._refresh_entity_list()
    assert len(inspector.entity_buttons) == 2

    # Query for 'transform, physics'
    inspector.search_query = "transform, physics"
    inspector._refresh_entity_list()
    assert len(inspector.entity_buttons) == 1
    assert list(inspector.entity_buttons.values()) == [entity_1]


def test_ecs_inspector_entity_selection(
    ui_manager: pygame_gui.UIManager, ecs_world: World
) -> None:
    """
    Verify entity selection updates inspector view details.

    Args:
        ui_manager: Pygame GUI UI Manager.
        ecs_world: ECS World.
    """
    entity_1 = ecs_world.create_entity(Transform(x=10.0, y=20.0))

    container = pygame_gui.elements.UIPanel(
        relative_rect=pygame.Rect(0, 0, 450, 410),
        manager=ui_manager,
    )

    inspector = ECSInspector(
        manager=ui_manager,
        container=container,
        world=ecs_world,
    )

    # Initially none selected
    assert inspector.selected_entity_id is None

    # Select entity 1
    inspector.selected_entity_id = entity_1
    inspector._refresh_editor_panel()

    assert inspector.selected_entity_id == entity_1
    assert inspector.title_label.text == f"Inspecting Entity {entity_1}"

    # Verify field editors were generated for Transform
    assert len(inspector.field_editors) > 0


def test_ecs_inspector_live_editing_and_physics_sync(
    ui_manager: pygame_gui.UIManager, ecs_world: World
) -> None:
    """
    Verify live component field editing parses and syncs with PhysicsBody.

    Args:
        ui_manager: Pygame GUI UI Manager.
        ecs_world: ECS World.
    """
    # Create physics body
    body = pymunk.Body()
    body.position = (100.0, 200.0)

    transform = Transform(x=100.0, y=200.0)
    phys_body = PhysicsBody(body=body, shape=pymunk.Circle(body, 10))
    entity = ecs_world.create_entity(transform, phys_body)

    container = pygame_gui.elements.UIPanel(
        relative_rect=pygame.Rect(0, 0, 450, 410),
        manager=ui_manager,
    )

    inspector = ECSInspector(
        manager=ui_manager,
        container=container,
        world=ecs_world,
    )

    inspector.selected_entity_id = entity
    inspector._refresh_editor_panel()

    # Find the editor for Transform 'x'
    x_editor = None
    for widget, (ent, comp, field, f_type) in inspector.field_editors.items():
        if isinstance(comp, Transform) and field == "x":
            x_editor = widget
            break

    assert x_editor is not None

    # Simulate entering "550.0" and completing text entry
    event = pygame.event.Event(
        pygame_gui.UI_TEXT_ENTRY_FINISHED,
        {"text": "550.0", "ui_element": x_editor},
    )
    consumed = inspector.process_event(event)

    assert consumed is True
    # Verify transform coordinates were updated
    assert transform.x == 550.0
    # Verify underlying Pymunk Physics Body coordinate was synchronized
    assert body.position.x == 550.0


def test_ecs_inspector_destruction(
    ui_manager: pygame_gui.UIManager, ecs_world: World
) -> None:
    """
    Verify that the Destroy action cleanly removes entity from ECS database.

    Args:
        ui_manager: Pygame GUI UI Manager.
        ecs_world: ECS World.
    """
    entity = ecs_world.create_entity(Transform(x=10.0, y=20.0))

    container = pygame_gui.elements.UIPanel(
        relative_rect=pygame.Rect(0, 0, 450, 410),
        manager=ui_manager,
    )

    inspector = ECSInspector(
        manager=ui_manager,
        container=container,
        world=ecs_world,
    )

    inspector.selected_entity_id = entity
    inspector._refresh_editor_panel()

    # Verify entity exists
    assert ecs_world.entity_exists(entity) is True

    # Click the destroy button
    event = pygame.event.Event(
        pygame_gui.UI_BUTTON_PRESSED,
        {"ui_element": inspector.destroy_btn},
    )
    consumed = inspector.process_event(event)

    assert consumed is True
    # Apply deferred destruction
    ecs_world.commands.apply_all()
    # Verify entity is destroyed
    assert ecs_world.entity_exists(entity) is False
    assert inspector.selected_entity_id is None


def test_ecs_inspector_quick_filters(
    ui_manager: pygame_gui.UIManager, ecs_world: World
) -> None:
    """
    Verify that quick filter pills properly update search text and filter.

    Args:
        ui_manager: Pygame GUI UI Manager.
        ecs_world: ECS World.
    """
    ecs_world.create_entity(Transform(x=10.0, y=20.0))

    container = pygame_gui.elements.UIPanel(
        relative_rect=pygame.Rect(0, 0, 650, 500),
        manager=ui_manager,
    )

    inspector = ECSInspector(
        manager=ui_manager,
        container=container,
        world=ecs_world,
    )

    # Initial: no filter
    assert inspector.search_query == ""

    # Find the filter pill for 'Yukkuri' (sets query to 'stats')
    yukkuri_pill = None
    for btn, query in inspector.filter_buttons.items():
        if query == "stats":
            yukkuri_pill = btn
            break

    assert yukkuri_pill is not None

    # Click the Yukkuri pill
    event = pygame.event.Event(
        pygame_gui.UI_BUTTON_PRESSED,
        {"ui_element": yukkuri_pill},
    )
    consumed = inspector.process_event(event)

    assert consumed is True
    assert inspector.search_query == "stats"
    assert inspector.search_box.get_text() == "stats"


def test_ecs_inspector_collapsible_sections(
    ui_manager: pygame_gui.UIManager, ecs_world: World
) -> None:
    """
    Verify that collapsible component sections fold/unfold when clicked.

    Args:
        ui_manager: Pygame GUI UI Manager.
        ecs_world: ECS World.
    """
    entity = ecs_world.create_entity(Transform(x=10.0, y=20.0))

    container = pygame_gui.elements.UIPanel(
        relative_rect=pygame.Rect(0, 0, 650, 500),
        manager=ui_manager,
    )

    inspector = ECSInspector(
        manager=ui_manager,
        container=container,
        world=ecs_world,
    )

    inspector.selected_entity_id = entity
    inspector._refresh_editor_panel()

    # Initial: not collapsed
    assert len(inspector.field_editors) > 0

    # Find the header button for Transform component
    transform_header = None
    for btn, comp_name in inspector.component_headers.items():
        if comp_name == "Transform":
            transform_header = btn
            break

    assert transform_header is not None

    # Click the Transform header to collapse it
    event = pygame.event.Event(
        pygame_gui.UI_BUTTON_PRESSED,
        {"ui_element": transform_header},
    )
    consumed = inspector.process_event(event)

    assert consumed is True
    assert inspector.collapsed_components.get("Transform") is True
    # The fields should now be collapsed (i.e. field_editors is empty)
    assert len(inspector.field_editors) == 0


def test_ecs_inspector_live_tracking(
    ui_manager: pygame_gui.UIManager, ecs_world: World
) -> None:
    """
    Verify that live tracking updates component fields in real-time.

    Args:
        ui_manager: Pygame GUI UI Manager.
        ecs_world: ECS World.
    """
    transform = Transform(x=10.0, y=20.0)
    entity = ecs_world.create_entity(transform)

    container = pygame_gui.elements.UIPanel(
        relative_rect=pygame.Rect(0, 0, 650, 500),
        manager=ui_manager,
    )

    inspector = ECSInspector(
        manager=ui_manager,
        container=container,
        world=ecs_world,
    )

    inspector.selected_entity_id = entity
    inspector._refresh_editor_panel()

    # Toggle live track ON
    event_toggle = pygame.event.Event(
        pygame_gui.UI_BUTTON_PRESSED,
        {"ui_element": inspector.live_track_btn},
    )
    inspector.process_event(event_toggle)
    assert inspector.live_track is True

    # Change component value in world
    transform.x = 999.0

    # Call update
    inspector.update(0.1)

    # Verify UI field reflects updated value
    x_editor = None
    for widget, (ent, comp, field, f_type) in inspector.field_editors.items():
        if isinstance(comp, Transform) and field == "x":
            x_editor = widget
            break

    assert x_editor is not None
    assert x_editor.get_text() == "999.0"


def test_ecs_inspector_validation_errors(
    ui_manager: pygame_gui.UIManager, ecs_world: World
) -> None:
    """
    Verify that invalid inputs display warning messages in status bar.

    Args:
        ui_manager: Pygame GUI UI Manager.
        ecs_world: ECS World.
    """
    transform = Transform(x=10.0, y=20.0)
    entity = ecs_world.create_entity(transform)

    container = pygame_gui.elements.UIPanel(
        relative_rect=pygame.Rect(0, 0, 650, 500),
        manager=ui_manager,
    )

    inspector = ECSInspector(
        manager=ui_manager,
        container=container,
        world=ecs_world,
    )

    inspector.selected_entity_id = entity
    inspector._refresh_editor_panel()

    # Find x editor
    x_editor = None
    for widget, (ent, comp, field, f_type) in inspector.field_editors.items():
        if isinstance(comp, Transform) and field == "x":
            x_editor = widget
            break

    assert x_editor is not None

    # Input an invalid float "abc"
    event = pygame.event.Event(
        pygame_gui.UI_TEXT_ENTRY_FINISHED,
        {"text": "abc", "ui_element": x_editor},
    )
    consumed = inspector.process_event(event)

    assert consumed is True
    # Value in world remains unchanged
    assert transform.x == 10.0
    # Status bar reflects the warning error message
    assert "Error" in inspector.status_label.text
