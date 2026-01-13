import pygame
from yukkuri_game.game.renderer.commands import TextCommand
from yukkuri_game.game.renderer.renderer import Renderer
from yukkuri_game.game.renderer.pygame_backend import PygameBackend


def test_renderer_initialization():
    pygame.init()
    screen = pygame.Surface((800, 600))
    backend = PygameBackend(screen)
    renderer = Renderer(backend)
    assert renderer is not None
    assert renderer.backend == backend


def test_renderer_submit_and_clear():
    pygame.init()
    screen = pygame.Surface((800, 600))
    backend = PygameBackend(screen)
    renderer = Renderer(backend)

    cmd = TextCommand(
        layer=1,
        z_index=0,
        text="Test",
        position=(100, 100),
        size=12,
        color=(255, 255, 255),
    )
    renderer.submit(cmd)

    assert len(renderer._commands) == 1

    renderer.render()

    assert len(renderer._commands) == 0


if __name__ == "__main__":
    test_renderer_initialization()
    test_renderer_submit_and_clear()
    print("Tests passed!")
