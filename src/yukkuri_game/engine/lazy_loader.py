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
        self, load_function: Callable[[str], Any], keys: Iterator[str] | None = None
    ):
        """
        Args:
            load_function: A function that takes a key and returns the value.
            keys: Optional initial set of keys that exist (but aren't loaded).
        """
        self._load_func = load_function
        self._cache: dict[str, Any] = {}
        # We can maintain a set of 'known' keys if we scan directories,
        # otherwise we just attempt load on miss.
        self._known_keys: set[str] = set(keys) if keys else set()

    def __getitem__(self, key: str) -> Any:
        if key in self._cache:
            return self._cache[key]

        # Attempt load
        try:
            val = self._load_func(key)
            if val is not None:
                self._cache[key] = val
                return val
        except Exception as e:
            logger.error(f"LazyLoader failed to load '{key}': {e}")

        raise KeyError(key)

    def __setitem__(self, key: str, value: Any) -> None:
        self._cache[key] = value
        self._known_keys.add(key)

    def __delitem__(self, key: str) -> None:
        if key in self._cache:
            del self._cache[key]
        if key in self._known_keys:
            self._known_keys.remove(key)

    def __iter__(self) -> Iterator[str]:
        # Iterating only yields what is known/cached?
        # Ideally it should yield all possible keys, but that requires scanning.
        # For this implementation, we assume we want to iterate known keys.
        return iter(self._known_keys.union(self._cache.keys()))

    def __len__(self) -> int:
        return len(self._known_keys.union(self._cache.keys()))

    def __repr__(self) -> str:
        return f"LazyLoader(cached={len(self._cache)}, total={len(self)})"
