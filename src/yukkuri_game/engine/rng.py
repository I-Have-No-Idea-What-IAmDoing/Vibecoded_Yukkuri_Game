import random
import numpy as np
from typing import Optional


class RNG:
    """
    Centralized Random Number Generator for deterministic behavior.
    Wraps standard random functions.
    """

    _instance: Optional["RNG"] = None
    _seed: int | float | str | bytes | bytearray | None = None

    @classmethod
    def get_instance(cls) -> "RNG":
        if cls._instance is None:
            cls._instance = RNG()
        return cls._instance

    def set_seed(self, seed: int | float | str | bytes | bytearray | None) -> None:
        self._seed = seed
        random.seed(seed)
        # Handle numpy if installed/used
        try:
            np.random.seed(
                seed if isinstance(seed, int) and seed is not None else 42
            )  # Numpy needs int usually
        except Exception as e:
            # Numpy might be missing or seed invalid
            import logging

            logging.getLogger(__name__).warning(f"Failed to seed numpy: {e}")

    def random(self) -> float:
        return random.random()

    def uniform(self, a: float, b: float) -> float:
        return random.uniform(a, b)

    def randint(self, a: int, b: int) -> int:
        return random.randint(a, b)

    def choice(self, seq):
        return random.choice(seq)

    def shuffle(self, x):
        random.shuffle(x)

    def gauss(self, mu: float, sigma: float) -> float:
        return random.gauss(mu, sigma)

    def getrandbits(self, k: int) -> int:
        return random.getrandbits(k)


# Global helper
_rng = RNG.get_instance()


def seed(a=None):
    _rng.set_seed(a)


def random_float() -> float:
    return _rng.random()


def uniform(a: float, b: float) -> float:
    return _rng.uniform(a, b)


def randint(a: int, b: int) -> int:
    return _rng.randint(a, b)


def choice(seq):
    return _rng.choice(seq)


def shuffle(x):
    _rng.shuffle(x)


def gauss(mu: float, sigma: float) -> float:
    return _rng.gauss(mu, sigma)


def getrandbits(k: int) -> int:
    return _rng.getrandbits(k)
