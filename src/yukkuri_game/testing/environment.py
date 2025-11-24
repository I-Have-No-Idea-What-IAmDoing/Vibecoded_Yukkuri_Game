import os
import contextlib

@contextlib.contextmanager
def TestEnvironment():
    """
    Manages Environment Variables for Headless SDL testing.
    Sets SDL_VIDEODRIVER to 'dummy' and SDL_AUDIODRIVER to 'dummy'.
    Restores original environment variables on exit.
    """
    target_vars = {
        "SDL_VIDEODRIVER": "dummy",
        "SDL_AUDIODRIVER": "dummy" # or disk
    }

    original_environ = {k: os.environ.get(k) for k in target_vars}
    os.environ.update(target_vars)

    try:
        yield
    finally:
        for k, v in original_environ.items():
            if v is None:
                if k in os.environ:
                    del os.environ[k]
            else:
                os.environ[k] = v
