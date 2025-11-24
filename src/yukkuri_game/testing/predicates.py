from dataclasses import dataclass
from typing import Callable, Optional

@dataclass
class WaitCondition:
    """Base class for wait conditions."""
    pass

@dataclass
class WaitUntil(WaitCondition):
    """
    Command to wait until a predicate function returns True.
    """
    predicate: Callable[[], bool]
    # Default to None so we can inherit the GameDriver's timeout_limit
    timeout: Optional[float] = None
    description: str = "Condition"

@dataclass
class WaitFrames(WaitCondition):
    """
    Command to wait for a specific number of frames.
    """
    frames: int

@dataclass
class Action:
    """Base class for actions."""
    pass

@dataclass
class InjectInput(Action):
    """
    Command to inject input via an InputHelper callable.
    """
    event_injector: Callable[[], None]
