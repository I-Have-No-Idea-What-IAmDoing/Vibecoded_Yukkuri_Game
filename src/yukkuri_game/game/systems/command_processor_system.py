"""
Command Processor System Module.

Drains the InputBufferService each frame and executes all pending
GameCommand objects in FIFO order.  This system must be registered
*first* in the ECS pipeline so that input-driven state changes are
visible to all other systems within the same tick.
"""

from ...engine.ecs import System, World
from ..services import InputBufferService


class CommandProcessorSystem(System):
    """
    ECS system that executes buffered game commands.

    Each frame this system pops every command from the
    ``InputBufferService`` and calls its ``execute(world)`` method.
    Running first in the pipeline guarantees that all downstream systems
    (physics, AI, animation …) observe the results of player input in the
    same tick.

    Attributes:
        _buffer: Cached reference to the InputBufferService.
    """

    def __init__(self) -> None:
        """Initialises the CommandProcessorSystem."""
        self._buffer: InputBufferService | None = None

    def initialize(self) -> None:
        """
        Lifecycle hook: resolve the InputBufferService from the service locator.
        """
        self._buffer = self.ecs_world.services.try_get(InputBufferService)

    def update(self, world: World, dt: float) -> None:
        """
        Drains and executes all pending commands.

        Args:
            world: The active ECS World instance.
            dt: Delta time in seconds (unused; present for API compatibility).
        """
        if self._buffer is None:
            self._buffer = world.services.try_get(InputBufferService)

        if self._buffer is None:
            return

        for command in self._buffer.pop_all():
            if hasattr(command, "execute"):
                command.execute(world)
