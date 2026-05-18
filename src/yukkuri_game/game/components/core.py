"""
Core game components.
"""

from dataclasses import dataclass


@dataclass(slots=True)
class Dead:
    """Tag component identifying that the entity is deceased."""
    pass


@dataclass(slots=True)
class Poop:
    """Tag component identifying identifying the entity as excrement."""
    pass
