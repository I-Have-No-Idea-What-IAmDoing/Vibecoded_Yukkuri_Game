"""
Rendering Pipeline.
"""

from typing import Protocol, Type, TypeVar

from .context import RenderContext

T = TypeVar("T", bound="RenderPass")


class RenderPass(Protocol):
    """Protocol for a single stage in the rendering pipeline."""

    def execute(self, context: RenderContext) -> None:
        """Executes the rendering pass."""
        ...


class RenderPipeline:
    """Manages and executes a sequence of rendering passes."""

    def __init__(self, passes: list[RenderPass]):
        self.passes = passes

    def execute(self, context: RenderContext) -> None:
        """Executes all passes in order."""
        for p in self.passes:
            p.execute(context)

    def get_pass(self, pass_type: Type[T]) -> T | None:
        """Retrieves a specific pass instance from the pipeline, if it exists."""
        for p in self.passes:
            if isinstance(p, pass_type):
                return p
        return None
