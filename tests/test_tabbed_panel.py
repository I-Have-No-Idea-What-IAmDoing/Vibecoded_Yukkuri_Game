import pytest
import pygame
import pygame_gui
from yukkuri_game.game.ui.tabbed_panel import TabbedPanel


@pytest.fixture
def ui_manager():
    pygame.init()
    pygame.display.set_mode((800, 600))
    manager = pygame_gui.UIManager((800, 600))
    yield manager
    pygame.quit()


def test_tabbed_panel_offset_positioning(ui_manager):
    """
    Verify that when TabbedPanel is placed at an offset, its children
    (buttons and panels) are also offset correctly in absolute coordinates.
    """
    # Place panel at (100, 100)
    rect = pygame.Rect(100, 100, 400, 300)
    panel = TabbedPanel(
        relative_rect=rect, manager=ui_manager, orientation="horizontal"
    )

    tab1_id = panel.add_tab("Tab 1")
    panel.rebuild()

    tab1_data = panel.get_tab(tab1_id)
    btn1 = tab1_data["button"]
    container1 = tab1_data["container"]

    # Relative positions (relative to panel) should be small/zero
    assert btn1.relative_rect.top == 0
    assert btn1.relative_rect.left == 0

    # Absolute positions (screen coordinates) should reflect the panel offset
    # The button rect in screen space should be (100, 100, width, height)
    # because it is at (0,0) relative to the panel which is at (100, 100).

    # Note: pygame_gui elements usually have 'rect' as absolute screen position
    # and 'relative_rect' as relative to container.

    print(f"Panel Rect: {panel.rect}")
    print(f"Button Absolute Rect: {btn1.rect}")
    print(f"Button Relative Rect: {btn1.relative_rect}")
    print(f"Panel _root_container Rect: {panel._root_container.rect}")

    assert btn1.rect.x == 100
    assert btn1.rect.y == 100

    # Check container content
    # Container relative top is button height (e.g. 30)
    # So absolute top should be 100 + 30 = 130
    assert container1.rect.x == 100
    assert container1.rect.y == 100 + panel.button_height


def test_tabbed_panel_initialization(ui_manager):
    rect = pygame.Rect(10, 10, 400, 300)
    panel = TabbedPanel(
        relative_rect=rect, manager=ui_manager, orientation="horizontal"
    )

    assert panel.rect == rect
    assert panel.orientation == "horizontal"
    assert panel.tab_count == 0


def test_horizontal_layout(ui_manager):
    rect = pygame.Rect(0, 0, 400, 300)
    button_size = (100, 30)
    panel = TabbedPanel(
        relative_rect=rect,
        manager=ui_manager,
        orientation="horizontal",
        tab_button_size=button_size,
    )

    tab1_id = panel.add_tab("Tab 1")
    tab2_id = panel.add_tab("Tab 2")

    panel.rebuild()

    tab1_data = panel.get_tab(tab1_id)
    tab2_data = panel.get_tab(tab2_id)

    btn1 = tab1_data["button"]
    btn2 = tab2_data["button"]

    assert btn1.relative_rect.top == 0
    assert btn2.relative_rect.top == 0
    assert btn2.relative_rect.left >= btn1.relative_rect.right

    container1 = tab1_data["container"]
    assert container1.relative_rect.top == button_size[1]
    assert container1.relative_rect.left == 0
    assert container1.relative_rect.width == rect.width
    assert container1.relative_rect.height == rect.height - button_size[1]


def test_vertical_layout(ui_manager):
    rect = pygame.Rect(0, 0, 400, 300)
    button_size = (100, 30)
    panel = TabbedPanel(
        relative_rect=rect,
        manager=ui_manager,
        orientation="vertical",
        tab_button_size=button_size,
    )

    tab1_id = panel.add_tab("Tab 1")
    tab2_id = panel.add_tab("Tab 2")

    panel.rebuild()

    tab1_data = panel.get_tab(tab1_id)
    tab2_data = panel.get_tab(tab2_id)

    btn1 = tab1_data["button"]
    btn2 = tab2_data["button"]

    assert btn1.relative_rect.left == 0
    assert btn2.relative_rect.left == 0
    assert btn1.relative_rect.top == 0
    assert btn2.relative_rect.top == btn1.relative_rect.height

    container1 = tab1_data["container"]
    assert container1.relative_rect.left == button_size[0]
    assert container1.relative_rect.top == 0
    assert container1.relative_rect.width == rect.width - button_size[0]
    assert container1.relative_rect.height == rect.height


def test_tab_switching(ui_manager):
    rect = pygame.Rect(0, 0, 400, 300)
    panel = TabbedPanel(relative_rect=rect, manager=ui_manager)

    tab1_id = panel.add_tab("Tab 1")
    tab2_id = panel.add_tab("Tab 2")

    tab1_container = panel.get_tab_container(tab1_id)
    tab2_container = panel.get_tab_container(tab2_id)

    assert panel.current_container_index == tab1_id
    assert tab1_container.visible == 1
    assert tab2_container.visible == 0

    panel.switch_current_container(tab2_id)

    assert panel.current_container_index == tab2_id
    assert tab1_container.visible == 0
    assert tab2_container.visible == 1
