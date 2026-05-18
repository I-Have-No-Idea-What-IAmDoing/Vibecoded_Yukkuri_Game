"""
Input Buffer Service for command queuing.
"""

import collections

class InputBufferService:
    """
    Service that acts as a FIFO queue of GameCommand objects.

    InputSystem enqueues commands here each frame.
    CommandProcessorSystem drains and executes them at the start of the
    next frame, ensuring all game logic is fully decoupled from raw input.

    Attributes:
        _queue: Internal deque storing pending commands.
    """

    def __init__(self) -> None:
        """Initialises the InputBufferService with an empty command queue."""
        self._queue: collections.deque[object] = collections.deque()

    def add_command(self, command: object) -> None:
        """
        Enqueues a command for deferred execution.

        Args:
            command: Any object satisfying the GameCommand protocol.
        """
        self._queue.append(command)

    def pop_all(self) -> list[object]:
        """
        Drains the queue and returns all pending commands.

        Clears the internal queue in one atomic swap so that commands
        added during execution are deferred to the *next* frame.

        Returns:
            list[object]: All commands that were pending at call time.
        """
        pending = list(self._queue)
        self._queue.clear()
        return pending
