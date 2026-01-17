from typing import TYPE_CHECKING, cast
import pymunk
from ...engine.ecs import System, World
from ...engine.event_bus import EventBus
from ...engine.events import (
    ComponentAddedEvent,
    ComponentRemovedEvent,
    WorldClearedEvent,
)
from ..components import PhysicsBody
from ..ai.navigation_service import NavigationService

if TYPE_CHECKING:
    pass


class NavigationUpdateSystem(System):
    """
    System responsible for updating the NavigationGrid when obstacles change.
    Listens for PhysicsBody additions/removals.
    """

    def initialize(self) -> None:
        self.event_bus = self.ecs_world.services.get(EventBus)
        self.nav_service = self.ecs_world.services.try_get(NavigationService)

        self.event_bus.subscribe(ComponentAddedEvent, self.on_component_added)
        self.event_bus.subscribe(ComponentRemovedEvent, self.on_component_removed)
        self.event_bus.subscribe(WorldClearedEvent, self.on_world_cleared)

    def update(self, world: World, dt: float) -> None:
        # Passive system, reacts to events.
        pass

    def on_component_added(self, event: ComponentAddedEvent) -> None:
        if event.component_type is PhysicsBody:
            self._handle_body_update(
                event.entity_id, cast(PhysicsBody, event.component), added=True
            )

    def on_component_removed(self, event: ComponentRemovedEvent) -> None:
        if event.component_type is PhysicsBody:
            self._handle_body_update(
                event.entity_id, cast(PhysicsBody, event.component), added=False
            )

    def on_world_cleared(self, event: WorldClearedEvent) -> None:
        if self.nav_service:
            self.nav_service.reset()  # We need to implement reset() in NavigationService

    def _handle_body_update(
        self, entity_id: int, phys: PhysicsBody, added: bool
    ) -> None:
        if not self.nav_service:
            # Try getting it again (might be registered late? unlikely given SystemRegistry order)
            self.nav_service = self.ecs_world.services.try_get(NavigationService)
            if not self.nav_service:
                return

        # Only care about STATIC bodies (Walls, etc)
        # Dynamic bodies (Yukkuris) are handled via steering/local avoidance, not grid blocking usually.
        if phys.body.body_type != pymunk.Body.STATIC:
            return

        # We need the Transform to know where it is.
        # PhysicsBody has position in body, but simpler to use component if available/synced.
        # But body.position is authoritative.

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
            # NavigationGrid.update_obstacle_rect(x, y, w, h...)
            # Grid assumes standard coordinates.

            # Map collision mask to capability?
            # If it blocks everything, it blocks WALK|FLY|SWIM.
            # Usually static walls block everything.
            # We can check shape.filter if needed.

            self.nav_service.update_obstacle_rect(
                x,
                y,
                w,
                h,
                walkable=not added,
                obstacle_type=1,  # HIGH (Blocks all)
            )
