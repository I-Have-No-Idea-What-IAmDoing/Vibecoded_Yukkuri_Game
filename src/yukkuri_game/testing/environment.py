"""
Test Environment Context Manager.
"""
import os
from contextlib import contextmanager
from typing import Generator

@contextmanager
def TestEnvironment() -> Generator[None, None, None]:
    """
    Context manager that forces SDL to use dummy drivers for headless testing.
    Restores original environment variables upon exit.
    """
    old_video = os.environ.get("SDL_VIDEODRIVER")
    old_audio = os.environ.get("SDL_AUDIODRIVER")

    # Force dummy drivers
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    # Use dummy or disk to avoid audio hardware dependencies
    os.environ["SDL_AUDIODRIVER"] = "dummy"

    try:
        yield
    finally:
        # Restore video driver
        if old_video is None:
            del os.environ["SDL_VIDEODRIVER"]
        else:
            os.environ["SDL_VIDEODRIVER"] = old_video

        # Restore audio driver
        if old_audio is None:
            del os.environ["SDL_AUDIODRIVER"]
        else:
            os.environ["SDL_AUDIODRIVER"] = old_audio
