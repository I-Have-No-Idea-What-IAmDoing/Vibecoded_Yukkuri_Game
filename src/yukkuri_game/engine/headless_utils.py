import contextlib
import pygame
import moderngl
from loguru import logger

@contextlib.contextmanager
def patch_headless_lighting():
    """
    Context manager to patch moderngl and pygame for headless lighting initialization.
    This allows pygame-light2d (and pygame-render) to work with a standalone EGL context
    instead of failing to create a context from a dummy SDL window.
    """
    # Capture the original function
    _original_create_context = moderngl.create_context

    # Check if we are already patched to avoid recursion or double patching
    if hasattr(pygame.display.set_mode, "_is_mock"):
        _real_pygame_set_mode = pygame.display.set_mode._original
    else:
        _real_pygame_set_mode = pygame.display.set_mode

    # Use default argument to bind the variable, avoiding UnboundLocalError
    def mocked_create_context(*args, real_ctx=_original_create_context, **kwargs):
        # Force standalone EGL context
        return real_ctx(standalone=True, backend="egl")

    def mocked_set_mode(size, flags=0, depth=0, display=0, vsync=0):
        # Remove OPENGL and DOUBLEBUF flags to prevent SDL error with dummy driver
        flags = flags & ~pygame.OPENGL
        flags = flags & ~pygame.DOUBLEBUF
        return _real_pygame_set_mode(size, flags, depth, display, vsync)

    # Apply patches
    moderngl.create_context = mocked_create_context

    # Store original reference to prevent recursion in mock
    mocked_set_mode._is_mock = True
    mocked_set_mode._original = _real_pygame_set_mode
    pygame.display.set_mode = mocked_set_mode

    try:
        yield
    finally:
        # Restore originals
        moderngl.create_context = _original_create_context
        pygame.display.set_mode = _real_pygame_set_mode
