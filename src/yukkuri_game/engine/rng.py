"""
Random Number Generator Module.

This module provides a centralized random number generator wrapper to ensure
deterministic behavior across the game engine. It wraps the standard `random`
module and optionally `numpy.random` if available.
"""

import random
from typing import Any

import numpy as np


class RNG:
    """
    Centralized Random Number Generator for deterministic behavior.

    Wraps standard random functions to allow global seeding and state management.

    Attributes:
        _instance (RNG | None): The singleton instance.
        _seed (int | float | str | bytes | bytearray | None): The current seed value.
    """

    _instance: "RNG | None" = None
    _seed: int | float | str | bytes | bytearray | None = None

    @classmethod
    def get_instance(cls) -> "RNG":
        """
        Retrieves the singleton instance of the RNG.

        Returns:
            RNG: The singleton RNG instance.
        """
        if cls._instance is None:
            cls._instance = RNG()
        return cls._instance

    def set_seed(self, seed: int | float | str | bytes | bytearray | None) -> None:
        """
        Sets the seed for the random number generator.

        Seeds both the standard `random` module and `numpy.random` (if valid).

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
            from loguru import logger

            logger.warning(f"Failed to seed numpy RNG: {e}")

    def random(self) -> float:
        """
        Returns a random float in the range [0.0, 1.0).

        Returns:
            float: A random float.
        """
        return random.random()

    def uniform(self, a: float, b: float) -> float:
        """
        Returns a random float N such that a <= N <= b.

        Args:
            a (float): The lower bound.
            b (float): The upper bound.

        Returns:
            float: A random float between a and b.
        """
        return random.uniform(a, b)

    def randint(self, a: int, b: int) -> int:
        """
        Returns a random integer N such that a <= N <= b.

        Args:
            a (int): The lower bound.
            b (int): The upper bound.

        Returns:
            int: A random integer between a and b.
        """
        return random.randint(a, b)

    def choice(self, seq: Any) -> Any:
        """
        Returns a random element from the non-empty sequence seq.

        Args:
            seq (Any): The sequence to choose from.

        Returns:
            Any: A random element from the sequence.
        """
        return random.choice(seq)

    def shuffle(self, x: list[Any]) -> None:
        """
        Shuffles the sequence x in place.

        Args:
            x (list[Any]): The list to shuffle.
        """
        random.shuffle(x)

    def gauss(self, mu: float, sigma: float) -> float:
        """
        Returns a random float from the Gaussian distribution.

        Args:
            mu (float): The mean.
            sigma (float): The standard deviation.

        Returns:
            float: A random float from the Gaussian distribution.
        """
        return random.gauss(mu, sigma)

    def getrandbits(self, k: int) -> int:
        """
        Returns an integer with k random bits.

        Args:
            k (int): The number of bits.

        Returns:
            int: An integer with k random bits.
        """
        return random.getrandbits(k)


# Global helper
_rng = RNG.get_instance()


def seed(a: int | float | str | bytes | bytearray | None = None) -> None:
    """
    Sets the global random seed.

    Args:
        a (int | float | str | bytes | bytearray | None): The seed value. Defaults to None.
    """
    _rng.set_seed(a)


def random_float() -> float:
    """
    Returns a random float in the range [0.0, 1.0).

    Returns:
        float: A random float.
    """
    return _rng.random()


def uniform(a: float, b: float) -> float:
    """
    Returns a random float N such that a <= N <= b.

    Args:
        a (float): The lower bound.
        b (float): The upper bound.

    Returns:
        float: A random float between a and b.
    """
    return _rng.uniform(a, b)


def randint(a: int, b: int) -> int:
    """
    Returns a random integer N such that a <= N <= b.

    Args:
        a (int): The lower bound.
        b (int): The upper bound.

    Returns:
        int: A random integer between a and b.
    """
    return _rng.randint(a, b)


def choice(seq: Any) -> Any:
    """
    Returns a random element from the non-empty sequence seq.

    Args:
        seq (Any): The sequence to choose from.

        Returns:
            Any: A random element from the sequence.
    """
    return _rng.choice(seq)


def shuffle(x: list[Any]) -> None:
    """
    Shuffles the sequence x in place.

    Args:
        x (list[Any]): The list to shuffle.
    """
    _rng.shuffle(x)


def gauss(mu: float, sigma: float) -> float:
    """
    Returns a random float from the Gaussian distribution.

    Args:
        mu (float): The mean.
        sigma (float): The standard deviation.

    Returns:
        float: A random float from the Gaussian distribution.
    """
    return _rng.gauss(mu, sigma)


def getrandbits(k: int) -> int:
    """
    Returns an integer with k random bits.

    Args:
        k (int): The number of bits.

    Returns:
        int: An integer with k random bits.
    """
    return _rng.getrandbits(k)
