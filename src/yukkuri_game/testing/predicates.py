"""
Predicates for test scenarios.
"""
from typing import Callable, Any

class WaitCondition:
    """Base class for wait conditions."""
    pass

class WaitUntil(WaitCondition):
    """Waits until a predicate returns True."""
    def __init__(self, predicate: Callable[[], bool], timeout: float = 5.0, description: str = "Condition"):
        self.predicate = predicate
        self.timeout = timeout
        self.description = description

class WaitFrames(WaitCondition):
    """Waits for a specific number of frames."""
    def __init__(self, frames: int):
        self.frames = frames

class Action:
    """Base class for actions."""
    pass

class InjectInput(Action):
    """Action to inject an input event."""
    def __init__(self, event_injector: Callable[[], None]):
        self.event_injector = event_injector
