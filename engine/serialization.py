import json
from simulation.agent import Agent
from simulation.world import World
from simulation.actions import Action
from game.data_loader import DataLoader
from typing import List, Dict, Any

SAVE_VERSION = 3

def save_game(world: World, agents: List[Agent], filepath: str) -> None:
    """Saves the current game state to a JSON file."""

    serialized_agents: List[Dict[str, Any]] = []
    for agent in agents:
        target_coords = None
        if agent.target_item:
            target_coords = {'x': agent.target_item['x'], 'y': agent.target_item['y']}

        serialized_needs = {name: need.value for name, need in agent.needs.items()}
        serialized_agents.append({
            'archetype_id': agent.archetype_id,
            'position': agent.position,
            'needs': serialized_needs,
            'state': agent.state,
            'current_action_name': agent.current_action.name if agent.current_action else None,
            'action_timer': agent.action_timer,
            'target_item_coords': target_coords
        })

    serialized_world: Dict[str, Any] = {
        'placed_items': [{'id': item['id'], 'x': item['x'], 'y': item['y']} for item in world.placed_items],
        'inventory_ids': [item['id'] for item in world.inventory]
    }

    save_data: Dict[str, Any] = {
        'save_version': SAVE_VERSION,
        'world': serialized_world,
        'agents': serialized_agents
    }

    with open(filepath, 'w') as f:
        json.dump(save_data, f, indent=2)
    print(f"Game saved to {filepath}")


def load_game(filepath: str, data_loader: DataLoader) -> tuple[World, List[Agent]]:
    """Loads a game state from a JSON file."""
    with open(filepath, 'r') as f:
        save_data: Dict[str, Any] = json.load(f)

    if save_data['save_version'] != SAVE_VERSION:
        raise ValueError(f"Save file version mismatch! Expected {SAVE_VERSION}, got {save_data['save_version']}")

    world_data: Dict[str, Any] = save_data['world']
    world: World = World(data_loader.room, data_loader.item_definitions)
    world.placed_items = []
    world.grid = [[None for _ in range(world.width)] for _ in range(world.height)]
    for item_data in world_data['placed_items']:
        item_def = data_loader.get_item_definition(item_data['id'])
        world.place_item(item_def, item_data['x'], item_data['y'])
    world.inventory = [data_loader.get_item_definition(item_id) for item_id in world_data['inventory_ids']]

    agents: List[Agent] = []
    action_templates: List[Dict[str, Any]] = data_loader.action_templates
    for agent_data in save_data['agents']:
        archetype = data_loader.get_agent_archetype(agent_data['archetype_id'])
        agent: Agent = Agent(archetype, agent_data['position'], action_templates)

        for name, value in agent_data['needs'].items():
            if name in agent.needs:
                agent.needs[name].value = value

        agent.state = agent_data['state']
        agent.action_timer = agent_data['action_timer']

        if agent_data['current_action_name']:
            action_template = data_loader.get_action_template(agent_data['current_action_name'])
            if action_template:
                agent.current_action = Action(action_template)

        if agent_data['target_item_coords']:
            coords = agent_data['target_item_coords']
            # Find the item at the saved coordinates
            agent.target_item = world.grid[coords['y']][coords['x']]

        agents.append(agent)

    print(f"Game loaded from {filepath}")
    return world, agents
