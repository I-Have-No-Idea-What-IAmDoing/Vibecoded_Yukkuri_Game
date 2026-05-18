import pytest
import pygame
from yukkuri_game.engine.renderer.commands import TextCommand
from yukkuri_game.engine.renderer.renderer import Renderer
from yukkuri_game.engine.renderer.pygame_backend import PygameBackend


@pytest.fixture
def renderer_backend():
    pygame.init()
    screen = pygame.Surface((800, 600))
    backend = PygameBackend(screen)
    yield backend
    # No explicit quit here if we want to share, but usually for unit tests we should be careful.
    # Letting conftest handle global quit or doing it here if isolated.
    # Given the pollution, let's NOT call quit() here to avoid killing the session for others,
    # but rely on the fact that we just needed init.


def test_renderer_initialization(renderer_backend):
    renderer = Renderer(renderer_backend)
    assert renderer is not None
    assert renderer.backend == renderer_backend


def test_renderer_submit_and_clear(renderer_backend):
    renderer = Renderer(renderer_backend)

    cmd = TextCommand(
        layer=1,
        z_index=0,
        text="Test",
        position=(100, 100),
        size=12,
        color=(255, 255, 255),
    )
    renderer.submit(cmd)

    # Check internal storage structure (updated to use layers)
    assert len(renderer._layers[1]) == 1

    renderer.render()

    assert len(renderer._layers) == 0
