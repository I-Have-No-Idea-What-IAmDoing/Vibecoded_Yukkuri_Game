"""
Inventory Components Module.
"""

import math
from typing import Any
from dataclasses import dataclass, field
import msgspec
from ..engine.types import EntityID


class ItemStack(msgspec.Struct):
    """
    Represents a stack of items in an inventory.
    """

    item_type_id: str
    quantity: int = 1
    custom_data: dict[str, Any] = msgspec.field(default_factory=dict)


@dataclass
class InventoryComponent:
    """
    Component storage for items.
    """

    capacity: int = 20
    items: list[ItemStack] = field(default_factory=list)

    def can_add(self, item_type_id: str, count: int = 1, stack_limit: int = 99) -> bool:
        """
        Checks if the item(s) can be added to the inventory.
        """
        remaining = count

        # Check existing stacks first
        for item in self.items:
            if item.item_type_id == item_type_id:
                space = stack_limit - item.quantity
                if space > 0:
                    taken = min(remaining, space)
                    remaining -= taken
                if remaining <= 0:
                    return True

        # Need new slots/stacks for remainder
        if remaining > 0:
            # Calculate how many new stacks are needed
            new_stacks_needed = math.ceil(remaining / stack_limit)
            available_slots = self.capacity - len(self.items)
            return new_stacks_needed <= available_slots

        return True

    def add(self, item_type_id: str, count: int = 1, stack_limit: int = 99) -> int:
        """
        Adds item(s) to the inventory.
        Returns the quantity that was successfully added.
        """
        remaining = count

        # Fill existing stacks
        for item in self.items:
            if item.item_type_id == item_type_id:
                space = stack_limit - item.quantity
                if space > 0:
                    taken = min(remaining, space)
                    item.quantity += taken
                    remaining -= taken
                if remaining <= 0:
                    return count - remaining  # should be count

        # Create new stacks if needed and capacity allows
        while remaining > 0 and len(self.items) < self.capacity:
            take_for_new_stack = min(remaining, stack_limit)
            self.items.append(
                ItemStack(item_type_id=item_type_id, quantity=take_for_new_stack)
            )
            remaining -= take_for_new_stack

        return count - remaining

    def remove(self, item_type_id: str, count: int = 1) -> int:
        """
        Removes item(s) from the inventory.
        Returns the quantity actually removed.
        """
        remaining_to_remove = count

        # Iterate backwards to safely remove empty stacks if needed
        # (though we might just decrement quantity and remove later)
        indices_to_remove = []

        for i in range(len(self.items) - 1, -1, -1):
            item = self.items[i]
            if item.item_type_id == item_type_id:
                taken = min(remaining_to_remove, item.quantity)
                item.quantity -= taken
                remaining_to_remove -= taken

                if item.quantity <= 0:
                    indices_to_remove.append(i)

                if remaining_to_remove <= 0:
                    break

        for i in indices_to_remove:
            self.items.pop(i)

        return count - remaining_to_remove

    def has(self, item_type_id: str, count: int = 1) -> bool:
        """
        Checks if the inventory contains at least `count` of the item.
        """
        total = 0
        for item in self.items:
            if item.item_type_id == item_type_id:
                total += item.quantity
                if total >= count:
                    return True
        return False

    def get_total(self, item_type_id: str) -> int:
        """
        Returns the total count of an item type in the inventory.
        """
        return sum(
            item.quantity for item in self.items if item.item_type_id == item_type_id
        )


@dataclass
class InventoryPickupRequest:
    """
    Component requesting to pickup an item entity into an inventory.
    """

    target_entity_id: EntityID


@dataclass
class InventoryDropRequest:
    """
    Component requesting to drop an item from an inventory.
    """

    item_type_id: str
    quantity: int = 1
