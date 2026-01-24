import random
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    pass


class RNG:
    """
    Centralized Random Number Generator for deterministic behavior.
    Wraps standard random functions.
    """

    _instance: "RNG | None" = None
    _seed: int | float | str | bytes | bytearray | None = None

    @classmethod
    def get_instance(cls) -> "RNG":
        """
        Gets the singleton instance of the RNG.

        Returns:
            RNG: The singleton instance.
        """
        if cls._instance is None:
            cls._instance = RNG()
        return cls._instance

    def set_seed(self, seed: int | float | str | bytes | bytearray | None) -> None:
        """
        Sets the seed for random number generation.

        Args:
            seed (int | float | str | bytes | bytearray | None): The seed value.
        """
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
        """
        Returns a random float in range [0.0, 1.0).

        Returns:
            float: Random float.
        """
        return random.random()

    def uniform(self, a: float, b: float) -> float:
        """
        Returns a random float in range [a, b].

        Args:
            a (float): Lower bound.
            b (float): Upper bound.

        Returns:
            float: Random float.
        """
        return random.uniform(a, b)

    def randint(self, a: int, b: int) -> int:
        """
        Returns a random integer in range [a, b] (inclusive).

        Args:
            a (int): Lower bound.
            b (int): Upper bound.

        Returns:
            int: Random integer.
        """
        return random.randint(a, b)

    def choice(self, seq: Any) -> Any:
        """
        Returns a random element from a sequence.

        Args:
            seq (Any): The sequence to choose from.

        Returns:
            Any: The selected element.
        """
        return random.choice(seq)

    def shuffle(self, x: Any) -> None:
        """
        Shuffles a sequence in place.

        Args:
            x (Any): The sequence to shuffle.
        """
        random.shuffle(x)

    def gauss(self, mu: float, sigma: float) -> float:
        """
        Returns a random float from a Gaussian distribution.

        Args:
            mu (float): The mean.
            sigma (float): The standard deviation.

        Returns:
            float: Random float.
        """
        return random.gauss(mu, sigma)

    def getrandbits(self, k: int) -> int:
        """
        Returns an integer with k random bits.

        Args:
            k (int): Number of bits.

        Returns:
            int: Random integer.
        """
        return random.getrandbits(k)


# Global helper
_rng = RNG.get_instance()


def seed(a: int | float | str | bytes | bytearray | None = None) -> None:
    """Sets the seed for the global RNG."""
    _rng.set_seed(a)


def random_float() -> float:
    """Returns a random float in [0.0, 1.0)."""
    return _rng.random()


def uniform(a: float, b: float) -> float:
    """Returns a random float in [a, b]."""
    return _rng.uniform(a, b)


def randint(a: int, b: int) -> int:
    """Returns a random integer in [a, b]."""
    return _rng.randint(a, b)


def choice(seq: Any) -> Any:
    """Returns a random element from seq."""
    return _rng.choice(seq)


def shuffle(x: Any) -> None:
    """Shuffles x in place."""
    _rng.shuffle(x)


def gauss(mu: float, sigma: float) -> float:
    """Returns a Gaussian random float."""
    return _rng.gauss(mu, sigma)


def getrandbits(k: int) -> int:
    """Returns an integer with k random bits."""
    return _rng.getrandbits(k)
