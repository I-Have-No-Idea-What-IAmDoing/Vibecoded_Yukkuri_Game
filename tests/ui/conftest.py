import pytest
import pygame

@pytest.fixture(scope="function", autouse=True)
def init_pygame_ui_test():
    """
    Ensures Pygame is initialized before each UI test.
    This handles cases where other tests (e.g. usage of game_driver) 
    may have called pygame.quit().
    """
    if not pygame.get_init():
        pygame.init()
    
    # Ensure a display surface exists for UI tests to use
    if pygame.display.get_surface() is None:
        pygame.display.set_mode((800, 600))
        
    yield
    
    # We consciously do NOT call pygame.quit() here to avoid thrashing.
    # It will either be reused by the next test or cleaned up by the process.

