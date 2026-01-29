from typing import TypeVar, Callable, Any, Iterator, MutableMapping
from loguru import logger

T = TypeVar("T")


class LazyLoader(MutableMapping):
    """
    A dictionary-like object that defers loading of values until they are accessed.

    This is useful for loading large datasets (like thousands of item definitions)
    only when the game actually needs them.
    """

    def __init__(
        self,
        load_function: Callable[[str], Any],
        keys: Iterator[str] | None = None,
        initializer: Callable[[], None] | None = None,
    ):
        """
        Args:
            load_function: A function that takes a key and returns the value.
            keys: Optional initial set of keys that exist (but aren't loaded).
            initializer: Optional function to call before iteration or counting (e.g. to load all keys).
        """
        import threading

        self._load_func = load_function
        self._cache: dict[str, Any] = {}
        # We can maintain a set of 'known' keys if we scan directories,
        # otherwise we just attempt load on miss.
        self._known_keys: set[str] = set(keys) if keys else set()
        self._initializer = initializer
        self._initialized = False
        self._lock = threading.RLock()

    def _ensure_initialized(self) -> None:
        """Call the initializer if it hasn't been called yet."""
        with self._lock:
            if not self._initialized and self._initializer:
                logger.info("Triggering LazyLoader initialization...")
                self._initializer()
                self._initialized = True

    def __getitem__(self, key: str) -> Any:
        # Check cache first (quick read lock check)
        with self._lock:
            if key in self._cache:
                return self._cache[key]

        # Prioritize single item load if possible (outside lock if it's slow IO? No, cache update needs lock)
        # Actually, self._load_func might be slow IO.
        # But if we don't lock, two threads might load same thing.
        # Given it's a lazy loader, double loading is better than corruption, but dict access must be locked.

        try:
            val = self._load_func(key)
            if val is not None:
                with self._lock:
                    self._cache[key] = val
                return val
        except (KeyError, FileNotFoundError):
            # Single-item load not supported for this key, try monolithic initialization
            pass
        except (ValueError, TypeError) as e:
            # Data parsing error - log and try fallback
            logger.debug(f"LazyLoader load failed for '{key}': {e}")

        # Fallback: try initializing monolithic file then checking cache
        self._ensure_initialized()
        with self._lock:
            if key in self._cache:
                return self._cache[key]

        raise KeyError(key)

    def __setitem__(self, key: str, value: Any) -> None:
        with self._lock:
            self._cache[key] = value
            self._known_keys.add(key)

    def __delitem__(self, key: str) -> None:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
            if key in self._known_keys:
                self._known_keys.remove(key)

    def __iter__(self) -> Iterator[str]:
        self._ensure_initialized()
        with self._lock:
            # Return a list copy so iteration is safe from modification
            return iter(list(self._known_keys.union(self._cache.keys())))

    def __len__(self) -> int:
        self._ensure_initialized()
        with self._lock:
            return len(self._known_keys.union(self._cache.keys()))

    def __repr__(self) -> str:
        with self._lock:
            return f"LazyLoader(cached={len(self._cache)}, total={len(self)})"
