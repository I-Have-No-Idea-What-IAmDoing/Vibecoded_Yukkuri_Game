"""
Inventory components.
"""

import math
from typing import Any
from dataclasses import dataclass, field
import msgspec
from ...engine.types import EntityID
from ...engine.persistence_registry import persistent


class ItemStack(msgspec.Struct):
    """
    Represents a stack of items in an inventory.
    """
    item_type_id: str
    quantity: int = 1
    custom_data: dict[str, Any] = msgspec.field(default_factory=dict)


@persistent
@dataclass
class InventoryComponent:
    """
    Component storage for items.
    """
    capacity: int = 20
    items: list[ItemStack] = field(default_factory=list)

    def can_add(self, item_type_id: str, count: int = 1, stack_limit: int = 99) -> bool:
        remaining = count
        for item in self.items:
            if item.item_type_id == item_type_id:
                space = stack_limit - item.quantity
                if space > 0:
                    taken = min(remaining, space)
                    remaining -= taken
                if remaining <= 0:
                    return True
        if remaining > 0:
            new_stacks_needed = math.ceil(remaining / stack_limit)
            available_slots = self.capacity - len(self.items)
            return new_stacks_needed <= available_slots
        return True

    def add(self, item_type_id: str, count: int = 1, stack_limit: int = 99) -> int:
        remaining = count
        for item in self.items:
            if item.item_type_id == item_type_id:
                space = stack_limit - item.quantity
                if space > 0:
                    taken = min(remaining, space)
                    item.quantity += taken
                    remaining -= taken
                if remaining <= 0:
                    return count
        while remaining > 0 and len(self.items) < self.capacity:
            take_for_new_stack = min(remaining, stack_limit)
            self.items.append(
                ItemStack(item_type_id=item_type_id, quantity=take_for_new_stack)
            )
            remaining -= take_for_new_stack
        return count - remaining

    def remove(self, item_type_id: str, count: int = 1) -> int:
        remaining_to_remove = count
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
        total = 0
        for item in self.items:
            if item.item_type_id == item_type_id:
                total += item.quantity
                if total >= count:
                    return True
        return False

    def get_total(self, item_type_id: str) -> int:
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
