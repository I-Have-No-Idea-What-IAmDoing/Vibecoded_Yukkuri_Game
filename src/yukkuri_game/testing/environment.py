"""
Test Environment Context Manager.
"""
import os
import contextlib

@contextlib.contextmanager
def TestEnvironment():
    """
    Sets up the environment for headless testing.
    Sets SDL_VIDEODRIVER to 'dummy' and SDL_AUDIODRIVER to 'dummy' or 'disk'.
    Restores original environment variables on exit.
    """
    old_video = os.environ.get("SDL_VIDEODRIVER")
    old_audio = os.environ.get("SDL_AUDIODRIVER")

    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"

    try:
        yield
    finally:
        if old_video is None:
            del os.environ["SDL_VIDEODRIVER"]
        else:
            os.environ["SDL_VIDEODRIVER"] = old_video

        if old_audio is None:
            del os.environ["SDL_AUDIODRIVER"]
        else:
            os.environ["SDL_AUDIODRIVER"] = old_audio
