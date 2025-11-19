"""
Scoring curves for the Utility AI.

These functions map a raw input value (e.g., a need level) to a score
between 0 and 1. This score is then used by the considerations to
determine the utility of an action.
"""

import math


def linear(x: float) -> float:
    """A linear curve."""
    return max(0.0, min(1.0, x))


def quadratic(x: float) -> float:
    """A quadratic curve (ease-in)."""
    return max(0.0, min(1.0, x * x))


def inverse(x: float) -> float:
    """An inverse curve."""
    return 1.0 - linear(x)


def logistic(x: float, k: float = 10.0, x0: float = 0.5) -> float:
    """A logistic (sigmoid) curve."""
    try:
        return 1.0 / (1.0 + math.exp(-k * (x - x0)))
    except OverflowError:
        return 0.0 if x < x0 else 1.0


CURVE_FUNCTIONS = {
    "linear": linear,
    "quadratic": quadratic,
    "inverse": inverse,
    "logistic": logistic,
}
