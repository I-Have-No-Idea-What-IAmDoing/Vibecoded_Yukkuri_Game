"""
Rendering Pipeline.
"""

from typing import Any, Protocol, Type, TypeVar

from .context import RenderContext

T = TypeVar("T", bound="RenderPass")


class RenderPass(Protocol):
    """Protocol for a single stage in the rendering pipeline."""

    def execute(self, context: RenderContext) -> None:
        """Executes the rendering pass."""
        ...


class RenderPipeline:
    """Manages and executes a sequence of rendering passes.

    Passes may be engine-level or game-level implementations. Both are
    accepted because the two ``RenderContext`` dataclasses (engine vs.
    game) are structurally identical at runtime even though the type
    checker sees them as different types.
    """

    def __init__(self, passes: list[Any]) -> None:
        """Initialises the pipeline.

        Args:
            passes: Ordered list of render pass instances. Each must
                implement ``execute(context) -> None``.
        """
        self.passes: list[Any] = passes

    def execute(self, context: RenderContext) -> None:
        """Executes all passes in order.

        Args:
            context: The shared render context for this frame.
        """
        for p in self.passes:
            p.execute(context)

    def get_pass(self, pass_type: Type[T]) -> T | None:
        """Retrieves a specific pass instance from the pipeline, if it exists.

        Args:
            pass_type: The class of the pass to retrieve.

        Returns:
            The matching pass instance, or None if not found.
        """
        for p in self.passes:
            if isinstance(p, pass_type):
                return p
        return None

