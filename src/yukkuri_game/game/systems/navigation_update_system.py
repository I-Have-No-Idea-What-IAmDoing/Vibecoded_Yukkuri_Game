"""
Navigation Update System - Dynamic Obstacle Tracker.
"""

from typing import cast
import pymunk

from ...engine.ecs import System, World
from ...engine.event_bus import EventBus
from ...engine.events import (
    ComponentAddedEvent,
    ComponentRemovedEvent,
    WorldClearedEvent,
)
from yukkuri_game.engine.components import PhysicsBody
from ..ai.navigation_service import NavigationService


class NavigationUpdateSystem(System):
    """
    System responsible for updating the NavigationGrid when obstacles change.

    Listens for PhysicsBody additions/removals and updates the grid accordingly.
    Only tracks STATIC bodies (Walls, etc) as dynamic bodies use local avoidance.

    Attributes:
        event_bus (Optional[EventBus]): The event bus.
        nav_service (Optional[NavigationService]): The navigation service.
    """

    def initialize(self) -> None:
        """Initializes system and subscriptions."""
        self.event_bus = self.ecs_world.services.get(EventBus)
        self.nav_service = self.ecs_world.services.try_get(NavigationService)

        self.event_bus.subscribe(ComponentAddedEvent, self.on_component_added)
        self.event_bus.subscribe(ComponentRemovedEvent, self.on_component_removed)
        self.event_bus.subscribe(WorldClearedEvent, self.on_world_cleared)

    def update(self, world: World, dt: float) -> None:
        """
        Passive system, only reacts to events.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.
        """
        pass

    def on_component_added(self, event: ComponentAddedEvent) -> None:
        """
        Handles PhysicsBody component addition.

        Args:
            event (ComponentAddedEvent): The event.
        """
        if event.component_type is PhysicsBody:
            self._handle_body_update(
                event.entity_id, cast(PhysicsBody, event.component), added=True
            )

    def on_component_removed(self, event: ComponentRemovedEvent) -> None:
        """
        Handles PhysicsBody component removal.

        Args:
            event (ComponentRemovedEvent): The event.
        """
        if event.component_type is PhysicsBody:
            self._handle_body_update(
                event.entity_id, cast(PhysicsBody, event.component), added=False
            )

    def on_world_cleared(self, event: WorldClearedEvent) -> None:
        """
        Handles world cleared event.

        Args:
            event (WorldClearedEvent): The event.
        """
        if self.nav_service:
            self.nav_service.reset()

    def _handle_body_update(
        self, entity_id: int, phys: PhysicsBody, added: bool
    ) -> None:
        """
        Updates the navigation grid based on physics body changes.

        Args:
            entity_id (int): Entity ID.
            phys (PhysicsBody): The physics component.
            added (bool): True if added, False if removed.
        """
        if not self.nav_service:
            self.nav_service = self.ecs_world.services.try_get(NavigationService)
            if not self.nav_service:
                return

        # Only care about STATIC bodies (Walls, etc)
        # Dynamic bodies (Yukkuris) are handled via steering/local avoidance.
        if phys.body.body_type != pymunk.Body.STATIC:
            return

        # Get AABB of the shapes
        for shape in phys.body.shapes:
            # Calculate bounding box
            bb = shape.cache_bb()

            # Update Grid
            # If added=True, we BLOCK (walkable=False).
            # If added=False, we CLEAR (walkable=True).

            # width/height from bb
            w = bb.right - bb.left
            h = bb.top - bb.bottom
            x = bb.left + w / 2
            y = bb.bottom + h / 2

            self.nav_service.update_obstacle_rect(
                x,
                y,
                w,
                h,
                walkable=not added,
                obstacle_type=1,  # HIGH (Blocks all)
            )
