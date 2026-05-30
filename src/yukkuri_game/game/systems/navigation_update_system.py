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
    EntityDestroyedEvent,
    WorldClearedEvent,
)
from ...engine.components import PhysicsBody
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
        self._obstacle_entities: set[int] = set()

        self.event_bus.subscribe(ComponentAddedEvent, self.on_component_added)
        self.event_bus.subscribe(ComponentRemovedEvent, self.on_component_removed)
        self.event_bus.subscribe(
            EntityDestroyedEvent, self.on_entity_destroyed
        )
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

    def on_entity_destroyed(self, event: EntityDestroyedEvent) -> None:
        """
        Handles entity destruction to clean up any registered obstacles.

        Args:
            event (EntityDestroyedEvent): The event.
        """
        phys = self.ecs_world.try_get_component(event.entity_id, PhysicsBody)
        if phys:
            self._handle_body_update(
                event.entity_id, phys, added=False
            )

    def on_world_cleared(self, event: WorldClearedEvent) -> None:
        """
        Handles world cleared event.

        Args:
            event (WorldClearedEvent): The event.
        """
        self._obstacle_entities.clear()
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
            self.nav_service = self.ecs_world.services.try_get(
                NavigationService
            )
            if not self.nav_service:
                return

        # Determine if this is a dynamic obstacle item
        is_static = phys.body.body_type == pymunk.Body.STATIC
        is_obs_item = False

        if added:
            from ..components import ItemStats
            stats = self.ecs_world.try_get_component(entity_id, ItemStats)
            if stats:
                from ...engine.resource_manager import ResourceManager
                rm = self.ecs_world.services.try_get(ResourceManager)
                if rm:
                    data = rm.item_types.get(stats.type_id)
                    if data:
                        obs_type = data.obstacle_type
                        if obs_type:
                            is_obs_item = True
                            self._obstacle_entities.add(entity_id)
        else:
            if entity_id in self._obstacle_entities:
                is_obs_item = True
                self._obstacle_entities.discard(entity_id)

        # Only care about STATIC bodies or registered dynamic obstacle items
        if not is_static and not is_obs_item:
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

            # Determine obstacle type (LOW or HIGH)
            obs_type_val = 1  # Default to HIGH
            if is_obs_item:
                from ..components import ItemStats
                stats = self.ecs_world.try_get_component(entity_id, ItemStats)
                if stats:
                    from ...engine.resource_manager import ResourceManager
                    rm = self.ecs_world.services.try_get(ResourceManager)
                    if rm:
                        data = rm.item_types.get(stats.type_id)
                        if data:
                            obs_str = data.obstacle_type
                            if (
                                isinstance(obs_str, str)
                                and obs_str.upper() == "LOW"
                            ):
                                obs_type_val = 0  # LOW

            self.nav_service.update_obstacle_rect(
                x,
                y,
                w,
                h,
                walkable=not added,
                obstacle_type=obs_type_val,
            )
