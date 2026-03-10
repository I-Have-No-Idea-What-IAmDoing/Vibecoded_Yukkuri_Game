"""
Lazy Loader Module.

This module provides the `LazyLoader` class, a specialized dictionary-like structure
that defers the loading of its values until they are explicitly accessed. This is
particularly useful for managing large sets of game resources or data that may not
all be needed immediately upon startup.
"""

import threading
from collections.abc import Iterator, MutableMapping
from typing import Callable, TypeVar

from loguru import logger

T = TypeVar("T")


class LazyLoader(MutableMapping[str, T]):
    """
    A dictionary-like object that defers loading of values until they are accessed.

    This is useful for loading large datasets (like thousands of item definitions)
    only when the game actually needs them.

    Attributes:
        _load_func (Callable[[str], T | None]): Function to load a value given a key.
        _cache (dict[str, T]): Internal cache of loaded values.
        _known_keys (set[str]): Set of keys known to exist (but potentially not loaded).
        _initializer (Callable[[], None] | None): Optional function to initialize the loader (e.g. monolithic load).
        _initialized (bool): Whether the initializer has been run.
        _lock (threading.RLock): Lock for thread safety.
    """

    def __init__(
        self,
        load_function: Callable[[str], T | None],
        keys: Iterator[str] | None = None,
        initializer: Callable[[], None] | None = None,
    ) -> None:
        """
        Initializes the LazyLoader.

        Args:
            load_function (Callable[[str], T | None]): A function that takes a key and returns the value.
            keys (Iterator[str] | None): Optional initial set of keys that exist (but aren't loaded).
            initializer (Callable[[], None] | None): Optional function to call before iteration or counting.
        """
        self._load_func = load_function
        self._cache: dict[str, T] = {}
        # We can maintain a set of 'known' keys if we scan directories,
        # otherwise we just attempt load on miss.
        self._known_keys: set[str] = set(keys) if keys else set()
        self._initializer = initializer
        self._initialized = False
        self._lock = threading.RLock()

    def _ensure_initialized(self) -> None:
        """
        Ensures that the initializer has been called.
        """
        with self._lock:
            if not self._initialized and self._initializer:
                logger.info("Triggering LazyLoader initialization...")
                self._initializer()
                self._initialized = True

    def __getitem__(self, key: str) -> T:
        """
        Retrieves the value for the given key, loading it if necessary.

        Args:
            key (str): The key to look up.

        Returns:
            T: The loaded value.

        Raises:
            KeyError: If the key cannot be found or loaded.
        """
        # Check cache first (quick read lock check)
        with self._lock:
            if key in self._cache:
                return self._cache[key]

        # Prioritize single item load if possible
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

    def __setitem__(self, key: str, value: T) -> None:
        """
        Sets the value for the given key.

        Args:
            key (str): The key to set.
            value (T): The value to store.
        """
        with self._lock:
            self._cache[key] = value
            self._known_keys.add(key)

    def __delitem__(self, key: str) -> None:
        """
        Deletes the value associated with the given key.

        Args:
            key (str): The key to delete.
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
            if key in self._known_keys:
                self._known_keys.remove(key)

    def __iter__(self) -> Iterator[str]:
        """
        Returns an iterator over the keys.

        Triggers initialization to ensure all keys are known.

        Returns:
            Iterator[str]: An iterator over the keys.
        """
        self._ensure_initialized()
        with self._lock:
            # Return a list copy so iteration is safe from modification
            return iter(list(self._known_keys.union(self._cache.keys())))

    def __len__(self) -> int:
        """
        Returns the number of items.

        Triggers initialization to ensure the count is accurate.

        Returns:
            int: The number of items.
        """
        self._ensure_initialized()
        with self._lock:
            return len(self._known_keys.union(self._cache.keys()))

    def __repr__(self) -> str:
        """
        Returns a string representation of the LazyLoader.

        Returns:
            str: String representation.
        """
        with self._lock:
            return f"LazyLoader(cached={len(self._cache)}, total={len(self)})"
