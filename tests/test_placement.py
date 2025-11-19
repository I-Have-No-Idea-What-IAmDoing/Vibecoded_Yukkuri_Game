import pytest
from simulation.world import World
from game.data_loader import DataLoader

@pytest.fixture
def test_world():
    data_loader = DataLoader()
    return World(data_loader.room, data_loader.item_definitions)

def test_valid_placement(test_world):
    """Test that a valid placement returns True."""
    item_def = test_world.item_definitions['food_bowl']
    assert test_world.is_valid_placement(item_def, 5, 5) == True

def test_invalid_placement_out_of_bounds(test_world):
    """Test that placing an item out of bounds returns False."""
    item_def = test_world.item_definitions['food_bowl']
    assert test_world.is_valid_placement(item_def, test_world.width, test_world.height) == False

def test_invalid_placement_collision(test_world):
    """Test that placing an item on top of another returns False."""
    item_def = test_world.item_definitions['bed_small'] # 2x1 footprint
    # Place the first item
    assert test_world.place_item(item_def, 5, 5) == True

    # Try to place another item overlapping the first one
    item_def_2 = test_world.item_definitions['food_bowl'] # 1x1 footprint
    assert test_world.is_valid_placement(item_def_2, 5, 5) == False # Direct overlap
    assert test_world.is_valid_placement(item_def_2, 6, 5) == False # Overlap with second tile of bed

def test_placement_success(test_world):
    """Test that a successful placement adds the item to the world."""
    item_def = test_world.item_definitions['food_bowl']
    initial_item_count = len(test_world.placed_items)

    test_world.place_item(item_def, 5, 5)

    assert len(test_world.placed_items) == initial_item_count + 1
    placed_item = test_world.placed_items[-1]
    assert placed_item['id'] == 'food_bowl'
    assert placed_item['x'] == 5 and placed_item['y'] == 5
    assert test_world.grid[5][5] is not None
