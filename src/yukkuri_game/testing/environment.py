"""
Test Environment Module.
"""

import os
import contextlib
from typing import Generator


@contextlib.contextmanager
def TestEnvironment() -> Generator[None, None, None]:
    """
    Context manager that sets up a safe environment for headless testing.
    Sets SDL_VIDEODRIVER to 'dummy' and restores original environment variables afterwards.
    """
    # Cache original values
    original_video = os.environ.get("SDL_VIDEODRIVER")
    original_audio = os.environ.get("SDL_AUDIODRIVER")

    # Set headless drivers
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    # Use 'dummy' or 'disk' for audio to prevent hardware requirement
    os.environ["SDL_AUDIODRIVER"] = "dummy"

    try:
        yield
    finally:
        # Restore video driver
        if original_video is not None:
            os.environ["SDL_VIDEODRIVER"] = original_video
        else:
            # If it wasn't set, unset it
            if "SDL_VIDEODRIVER" in os.environ:
                del os.environ["SDL_VIDEODRIVER"]

        # Restore audio driver
        if original_audio is not None:
            os.environ["SDL_AUDIODRIVER"] = original_audio
        else:
            if "SDL_AUDIODRIVER" in os.environ:
                del os.environ["SDL_AUDIODRIVER"]
