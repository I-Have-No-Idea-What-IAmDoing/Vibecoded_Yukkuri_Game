"""
Predicates for test scenarios.
"""
from dataclasses import dataclass
from typing import Callable, Optional, Any

@dataclass
class WaitUntil:
    """Waits until a predicate returns True."""
    predicate: Callable[[], bool]
    timeout: Optional[float] = None
    description: str = "condition"

@dataclass
class WaitFrames:
    """Waits for a specific number of frames."""
    frames: int

@dataclass
class InjectInput:
    """Wraps an input injection action."""
    event_injector: Callable[[], None]
