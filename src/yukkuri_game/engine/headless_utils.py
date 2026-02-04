"""
Headless Utilities Module.

This module provides utilities for running the game in headless mode (no window),
particularly for testing and server-side simulation. It includes patches for
rendering libraries to function without a display context.
"""

from typing import Any
from collections.abc import Iterator
import contextlib
import pygame
import moderngl


@contextlib.contextmanager
def patch_headless_lighting() -> Iterator[None]:
    """
    Context manager to patch moderngl and pygame for headless lighting initialization.
    This allows pygame-light2d (and pygame-render) to work with a standalone EGL context
    instead of failing to create a context from a dummy SDL window.

    Yields:
        None
    """
    original_create_context = moderngl.create_context

    # Check if we are already patched to avoid recursion or double patching
    set_mode_any: Any = pygame.display.set_mode
    if hasattr(set_mode_any, "_is_mock"):
        _real_pygame_set_mode = set_mode_any._original
    else:
        _real_pygame_set_mode = pygame.display.set_mode

    def mocked_create_context(*args: Any, **kwargs: Any) -> moderngl.Context:
        """
        Mocked create_context that forces standalone EGL backend.

        Args:
            *args (Any): Positional arguments.
            **kwargs (Any): Keyword arguments.

        Returns:
            moderngl.Context: The created context.
        """
        # Force standalone EGL context
        return original_create_context(standalone=True, backend="egl")  # type: ignore[arg-type]

    def mocked_set_mode(
        size: tuple[int, int],
        flags: int = 0,
        depth: int = 0,
        display: int = 0,
        vsync: int = 0,
    ) -> pygame.Surface:
        """
        Mocked pygame.display.set_mode that removes incompatible flags.

        Args:
            size (tuple[int, int]): Window size.
            flags (int): Display flags.
            depth (int): Color depth.
            display (int): Display index.
            vsync (int): Vsync setting.

        Returns:
            pygame.Surface: The display surface.
        """
        # Remove OPENGL and DOUBLEBUF flags to prevent SDL error with dummy driver
        flags = flags & ~pygame.OPENGL
        flags = flags & ~pygame.DOUBLEBUF
        return _real_pygame_set_mode(size, flags, depth, display, vsync)

    # Apply patches
    # Dynamic patching
    from typing import cast

    moderngl.create_context = cast(Any, mocked_create_context)

    # Store original reference to prevent recursion in mock
    mocked_set_mode_any: Any = cast(Any, mocked_set_mode)
    mocked_set_mode_any._is_mock = True
    mocked_set_mode_any._original = _real_pygame_set_mode
    pygame.display.set_mode = mocked_set_mode_any

    try:
        yield
    finally:
        # Restore originals
        moderngl.create_context = original_create_context
        pygame.display.set_mode = _real_pygame_set_mode
