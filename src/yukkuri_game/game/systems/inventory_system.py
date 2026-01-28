"""
Inventory System - Pickup and Drop Logic.

Manages entity inventory interactions, including picking up items from the world
and dropping items back into the world.
"""

from loguru import logger

from ...engine.ecs import System, World
from ...engine.event_bus import EventBus
from ...engine.events import InventoryChangedEvent
from ...engine.resource_manager import ResourceManager
from ..components import Transform
from ..entity_factory import EntityFactory
from ..inventory_component import (
    InventoryComponent,
    InventoryDropRequest,
    InventoryPickupRequest,
)
from ..yukkuri_components import ItemStats


class InventorySystem(System):
    """
    System responsible for handling inventory interactions (pickup, drop).
    """

    def __init__(self) -> None:
        """Initializes the InventorySystem."""
        super().__init__()
        self.event_bus: EventBus | None = None
        self.resource_manager: ResourceManager | None = None

    def update(self, world: World, dt: float) -> None:
        """
        Updates the inventory system, processing pickup and drop requests.

        Args:
            world (World): The ECS World.
            dt (float): Delta time.
        """
        if self.event_bus is None:
            self.event_bus = world.services.try_get(EventBus)
        if self.resource_manager is None:
            self.resource_manager = world.services.try_get(ResourceManager)

        self._handle_pickups(world)
        self._handle_drops(world)

    def _handle_pickups(self, world: World) -> None:
        """
        Process all pickup requests.

        Args:
            world (World): The ECS World.
        """
        for entity_id, (inventory, request) in world.get_components_tuple(
            InventoryComponent, InventoryPickupRequest
        ):
            target_id = request.target_entity_id

            # Validation: Target exists
            if not world.entity_exists(target_id):
                logger.warning(f"Pickup failed: Entity {target_id} does not exist.")
                world.remove_component(entity_id, InventoryPickupRequest)
                continue

            # Validation: Target is an item (has ItemStats)
            item_stats = world.get_component(target_id, ItemStats)
            if not item_stats:
                logger.warning(f"Pickup failed: Entity {target_id} is not an item.")
                world.remove_component(entity_id, InventoryPickupRequest)
                continue

            # Logic: Try add to inventory
            item_type_id = item_stats.type_id

            # Get stack limit from ResourceManager if possible
            stack_limit = 99
            if self.resource_manager:
                item_data = self.resource_manager.item_types.get(item_type_id)
                if item_data:
                    stack_limit = getattr(item_data, "stack_size", 99)

            if inventory.can_add(item_type_id, count=1, stack_limit=stack_limit):
                added_count = inventory.add(
                    item_type_id, count=1, stack_limit=stack_limit
                )

                if added_count > 0:
                    # Success
                    if self.event_bus:
                        self.event_bus.publish(
                            InventoryChangedEvent(
                                entity_id=entity_id,
                                item_type_id=item_type_id,
                                delta=added_count,
                            )
                        )

                    world.destroy_entity(target_id)

                    logger.info(
                        f"Entity {entity_id} picked up item {item_type_id} (Entity {target_id})."
                    )
                else:
                    logger.debug(
                        f"Entity {entity_id} could not add item {item_type_id} (Inventory full?)"
                    )
            else:
                logger.debug(
                    f"Inventory full for {entity_id}, cannot pickup {item_type_id}."
                )

            # Clean up request
            world.remove_component(entity_id, InventoryPickupRequest)

    def _handle_drops(self, world: World) -> None:
        """
        Process all drop requests.

        Args:
            world (World): The ECS World.
        """
        entity_factory = world.services.try_get(EntityFactory)
        if not entity_factory:
            # Cannot drop if we can't spawn entities
            return

        for entity_id, (inventory, transform, request) in world.get_components_tuple(
            InventoryComponent, Transform, InventoryDropRequest
        ):
            item_type_id = request.item_type_id
            count = request.quantity

            if inventory.has(item_type_id, count):
                removed = inventory.remove(item_type_id, count)

                if removed > 0:
                    spawn_x = transform.x
                    spawn_y = transform.y + 20  # Offset to avoid overlap.

                    try:
                        for _ in range(removed):
                            entity_factory.create_item(item_type_id, spawn_x, spawn_y)

                        if self.event_bus:
                            self.event_bus.publish(
                                InventoryChangedEvent(
                                    entity_id=entity_id,
                                    item_type_id=item_type_id,
                                    delta=-removed,
                                )
                            )
                        logger.info(
                            f"Entity {entity_id} dropped {removed}x {item_type_id}."
                        )

                    except ValueError as e:
                        logger.error(
                            f"Failed to spawn dropped item {item_type_id}: {e}"
                        )
                        stack_limit = 99
                        if self.resource_manager:
                            item_data = self.resource_manager.item_types.get(
                                item_type_id
                            )
                            if item_data:
                                stack_limit = getattr(item_data, "stack_size", 99)
                        inventory.add(item_type_id, removed, stack_limit)

            else:
                logger.debug(
                    f"Entity {entity_id} tried to drop {count}x {item_type_id} but didn't have enough."
                )

            # Clean up request
            world.remove_component(entity_id, InventoryDropRequest)
