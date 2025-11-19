import pytest
from simulation.agent import Agent
from simulation.utility_ai import UtilityAI
from game.data_loader import DataLoader
from simulation.world import World

@pytest.fixture
def data_loader():
    return DataLoader()

@pytest.fixture
def test_agent(data_loader):
    archetype = data_loader.get_agent_archetype("basic_yukkuri")
    action_templates = data_loader.action_templates
    return Agent(archetype, (0, 0), action_templates)

@pytest.fixture
def test_world(data_loader):
    # A minimal world for testing, starting empty
    world = World(data_loader.room, data_loader.item_definitions)
    world.placed_items = []
    world.grid = [[None for _ in range(world.width)] for _ in range(world.height)]
    return world

def test_utility_scoring_hungry(test_agent, test_world, data_loader):
    """Test that 'Eat' is the highest-scoring action when hunger is low."""
    # Manually set needs for a clear test case
    test_agent.needs['Hunger'].value = 10
    test_agent.needs['Energy'].value = 80
    test_agent.needs['Fun'].value = 80
    test_agent.needs['Social'].value = 80
    test_agent.needs['Cleanliness'].value = 80

    # Place a food item in the world
    food_bowl_def = data_loader.get_item_definition('food_bowl')
    test_world.place_item(food_bowl_def, 1, 1)

    chosen_action = test_agent.utility_ai.select_action(test_agent, test_world)
    assert chosen_action is not None
    assert chosen_action.name == 'Eat'

def test_utility_scoring_tired(test_agent, test_world, data_loader):
    """Test that 'Sleep' is the highest-scoring action when energy is low."""
    test_agent.needs['Hunger'].value = 80
    test_agent.needs['Energy'].value = 10
    test_agent.needs['Fun'].value = 80

    # Place a bed in the world
    bed_def = data_loader.get_item_definition('bed_small')
    test_world.place_item(bed_def, 1, 1)

    chosen_action = test_agent.utility_ai.select_action(test_agent, test_world)
    assert chosen_action is not None
    assert chosen_action.name == 'Sleep'

def test_precondition_need_threshold(test_agent, test_world, data_loader):
    """Test that an action is not chosen if its need precondition is not met."""
    # Hunger is high, so the 'Eat' action's precondition (Hunger < 70) should fail
    test_agent.needs['Hunger'].value = 90
    test_agent.needs['Energy'].value = 10 # Sleep is still a valid option

    # Place both items
    food_bowl_def = data_loader.get_item_definition('food_bowl')
    test_world.place_item(food_bowl_def, 1, 1)
    bed_def = data_loader.get_item_definition('bed_small')
    test_world.place_item(bed_def, 2, 2)

    chosen_action = test_agent.utility_ai.select_action(test_agent, test_world)
    assert chosen_action is not None
    assert chosen_action.name != 'Eat'
    assert chosen_action.name == 'Sleep'
