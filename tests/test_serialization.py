import pytest
import os
from simulation.world import World
from simulation.agent import Agent
from engine.serialization import save_game, load_game
from game.data_loader import DataLoader

@pytest.fixture
def game_state():
    """Sets up a sample game state for testing."""
    data_loader = DataLoader()
    world = World(data_loader.room, data_loader.item_definitions)
    world.place_item(data_loader.get_item_definition('food_bowl'), 3, 4)

    agents = []
    archetype = data_loader.get_agent_archetype("basic_yukkuri")
    action_templates = data_loader.action_templates
    agent = Agent(archetype, (5, 5), action_templates)
    agent.needs['Hunger'].value = 50
    agents.append(agent)

    return world, agents, data_loader

def test_save_load_roundtrip(game_state):
    """Tests that saving and then loading a game returns the same state."""
    world, agents, data_loader = game_state
    save_filepath = "test_save.json"

    # Save the initial state
    save_game(world, agents, save_filepath)

    # Load the state back
    loaded_world, loaded_agents = load_game(save_filepath, data_loader)

    # Clean up the save file
    os.remove(save_filepath)

    # 1. Compare World State
    assert len(loaded_world.placed_items) == len(world.placed_items)
    assert loaded_world.placed_items[0]['id'] == world.placed_items[0]['id']
    assert loaded_world.placed_items[0]['x'] == world.placed_items[0]['x']

    # 2. Compare Agent State
    assert len(loaded_agents) == len(agents)
    original_agent = agents[0]
    loaded_agent = loaded_agents[0]
    assert loaded_agent.archetype_id == original_agent.archetype_id
    assert loaded_agent.position == original_agent.position
    assert pytest.approx(loaded_agent.needs['Hunger'].value) == original_agent.needs['Hunger'].value
