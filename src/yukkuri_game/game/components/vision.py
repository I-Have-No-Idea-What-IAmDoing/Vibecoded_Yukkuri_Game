"""
Vision and perception components.
"""

from dataclasses import dataclass

from ...engine.persistence_registry import persistent


@persistent
@dataclass(slots=True)
class Vision:
    """
    Component defining an entity's perception capabilities.
    """
    range: float = 200.0
    fov: float = 360.0
