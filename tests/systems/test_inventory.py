import pytest
from yukkuri_game.engine.ecs import World
from yukkuri_game.game.inventory_component import (
    InventoryComponent,
    InventoryPickupRequest,
    InventoryDropRequest,
)
from yukkuri_game.game.systems.inventory_system import InventorySystem
from yukkuri_game.game.components import Transform
from yukkuri_game.game.yukkuri_components import ItemStats
from yukkuri_game.engine.resource_manager import ResourceManager
from yukkuri_game.engine.data_models import ItemType
from yukkuri_game.engine.event_bus import EventBus
from yukkuri_game.engine.events import InventoryChangedEvent
from yukkuri_game.engine.serializer import WorldSerializer
from yukkuri_game.game.entity_factory import EntityFactory


class MockResourceManager:
    def __init__(self):
        self.item_types = {
            "test_item": ItemType(
                name="Test Item",
                image="test.png",
                width=32,
                height=32,
                cost=10,
                is_portable=True,
                stack_size=10,
            ),
            "unstackable_item": ItemType(
                name="Unstackable Item",
                image="unique.png",
                width=32,
                height=32,
                cost=100,
                is_portable=True,
                stack_size=1,
            ),
        }


class MockEntityFactory:
    def __init__(self, world):
        self.world = world
        self.created_items = []

    def create_item(self, type_id, x, y):
        e = self.world.create_entity()
        self.world.add_component(e, Transform(x=x, y=y))
        self.world.add_component(
            e, ItemStats(name="Dropped Item", type_id=type_id, cost=0, is_portable=True)
        )
        self.created_items.append((type_id, x, y))
        return e


@pytest.fixture
def inventory():
    return InventoryComponent(capacity=5)


def test_inventory_add_basic(inventory):
    """Test adding a single item to empty inventory."""
    assert inventory.can_add("test_item", 1, 10)
    added = inventory.add("test_item", 1, 10)
    assert added == 1
    assert len(inventory.items) == 1
    assert inventory.items[0].quantity == 1
    assert inventory.items[0].item_type_id == "test_item"


def test_inventory_stacking(inventory):
    """Test stacking items."""
    inventory.add("test_item", 5, 10)

    # Add more to same stack
    inventory.add("test_item", 3, 10)
    assert len(inventory.items) == 1
    assert inventory.items[0].quantity == 8

    # Overflow stack
    inventory.add("test_item", 5, 10)  # 8 + 5 = 13, limit 10
    assert len(inventory.items) == 2
    assert inventory.items[0].quantity == 10
    assert inventory.items[1].quantity == 3


def test_inventory_capacity(inventory):
    """Test capacity limits."""
    # Fill 5 slots with unique items (or full stacks)
    for i in range(5):
        inventory.add(f"item_{i}", 1, 1)

    assert len(inventory.items) == 5
    assert not inventory.can_add("new_item", 1, 1)

    added = inventory.add("new_item", 1, 1)
    assert added == 0
    assert len(inventory.items) == 5


def test_can_add_multiple_stacks_capacity(inventory):
    """Test can_add correctly handles multiple new stacks requirement.

    This test verifies the bug fix for can_add() which previously
    only checked for one free slot regardless of how many stacks were needed.
    """
    # inventory has capacity=5
    # Fill 4 slots with different item types
    for i in range(4):
        inventory.add(f"unique_item_{i}", 1, 99)

    assert len(inventory.items) == 4

    # 1 slot remaining, but we need 2 stacks for 150 items at stack_limit=99
    # BUG: This would incorrectly return True before the fix
    assert not inventory.can_add("new_item", 150, 99)

    # But 99 items (1 stack) should be fine
    assert inventory.can_add("new_item", 99, 99)

    # And 100 items (2 stacks needed) should fail
    assert not inventory.can_add("new_item", 100, 99)


def test_inventory_remove(inventory):
    """Test removing items."""
    inventory.add("test_item", 10, 10)

    removed = inventory.remove("test_item", 4)
    assert removed == 4
    assert inventory.items[0].quantity == 6

    removed = inventory.remove("test_item", 6)
    assert removed == 6
    assert len(inventory.items) == 0


def test_inventory_remove_multiple_stacks(inventory):
    """Test removing across multiple stacks."""
    inventory.add("test_item", 10, 10)
    inventory.add("test_item", 5, 10)
    assert inventory.get_total("test_item") == 15

    removed = inventory.remove("test_item", 12)
    assert removed == 12
    assert inventory.get_total("test_item") == 3
    # Check that one stack is gone and one remains
    assert len(inventory.items) == 1


# --- System Tests ---


@pytest.fixture
def world():
    w = World()
    w.services.register(ResourceManager(), ResourceManager)
    w.services.try_get(ResourceManager).item_types = MockResourceManager().item_types
    w.services.register(EventBus(), EventBus)
    return w


def test_inventory_system_pickup(world):
    system = InventorySystem()
    event_bus = world.services.try_get(EventBus)

    events = []
    event_bus.subscribe(InventoryChangedEvent, lambda e: events.append(e))

    # Player with inventory
    player = world.create_entity()
    world.add_component(player, InventoryComponent(capacity=5))

    # Item in world
    item = world.create_entity()
    world.add_component(
        item,
        ItemStats(name="Test Item", type_id="test_item", cost=10, is_portable=True),
    )

    # Request Pickup
    world.add_component(player, InventoryPickupRequest(target_entity_id=item))

    system.update(world, 0.1)

    # Assertions
    assert not world.entity_exists(item)
    inv = world.get_component(player, InventoryComponent)
    assert inv.items[0].item_type_id == "test_item"
    assert inv.items[0].quantity == 1

    assert len(events) == 1
    assert events[0].entity_id == player
    assert events[0].delta == 1


def test_inventory_system_drop(world):
    system = InventorySystem()
    event_bus = world.services.try_get(EventBus)

    # Mock EntityFactory
    factory = MockEntityFactory(world)
    world.services.register(factory, EntityFactory)

    events = []
    event_bus.subscribe(InventoryChangedEvent, lambda e: events.append(e))

    # Player with inventory
    player = world.create_entity()
    world.add_component(player, Transform(x=100, y=100))
    inv = InventoryComponent(capacity=5)
    inv.add("test_item", 2, 10)
    world.add_component(player, inv)

    # Request Drop
    world.add_component(
        player, InventoryDropRequest(item_type_id="test_item", quantity=1)
    )

    system.update(world, 0.1)

    # Assertions
    assert inv.get_total("test_item") == 1
    assert len(factory.created_items) == 1
    assert factory.created_items[0][0] == "test_item"

    assert len(events) == 1
    assert events[0].delta == -1


from yukkuri_game.game.components_persistence import StableIDComponent, Persistable

# ... (imports)


def test_persistence_inventory():
    """Verify that InventoryComponent serializes correctly."""
    w = World()
    e = w.create_entity()

    # Add persistence components
    w.add_component(e, StableIDComponent(id=100))
    w.add_component(e, Persistable())

    inv = InventoryComponent()
    inv.add("test_item", 5, 10)
    inv.items[0].custom_data = {"quality": "high"}

    w.add_component(e, inv)

    # Minimal serializer setup
    serializer = WorldSerializer(
        w, [InventoryComponent, StableIDComponent, Persistable]
    )
    data = serializer.serialize_entity(e)

    # Deserialize
    w2 = World()
    # serialize_entity returns a dict. load_from_data expects a list of dicts.
    # Deserialize
    w2 = World()
    # serialize_entity returns a dict. load_from_data expects a list of dicts.
    serializer2 = WorldSerializer(
        w2, [InventoryComponent, StableIDComponent, Persistable]
    )
    serializer2.load_from_data([data])

    # Get the loaded entity (should be only one)
    loaded_entities = w2.get_all_entities()
    assert len(loaded_entities) == 1
    e2 = loaded_entities[0]

    inv2 = w2.get_component(e2, InventoryComponent)

    assert inv2 is not None
    assert len(inv2.items) == 1
    assert inv2.items[0].item_type_id == "test_item"
    assert inv2.items[0].quantity == 5
    assert inv2.items[0].custom_data["quality"] == "high"
