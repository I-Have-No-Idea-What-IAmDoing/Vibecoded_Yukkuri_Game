# Modding Guide

This guide explains how to add new content to the Yukkuri Raising Game. Thanks to its data-driven design, you can add new agents, items, and actions without writing any code.

## Getting Started

All game content is defined in the JSON files located in the `content/data/` directory. To add new content, you simply need to edit these files or add new ones.

## Adding a New Item

1.  **Open `content/data/item_definitions.json`**.
2.  **Copy an existing item's JSON object** to use as a template.
3.  **Change the `"id"`** to something unique.
4.  **Modify the other fields** as you see fit:
    *   `"display_name"`: The name that will appear in the game.
    *   `"footprint"`: The size of the item on the grid.
    *   `"effects"`: Which needs the item restores, and by how much.
    *   `"categories"`: Important for the AI. For example, an item that restores Hunger should have the `"food"` category.

## Adding a New Agent Archetype

1.  **Open `content/data/agent_archetypes.json`**.
2.  **Copy an existing agent's JSON object**.
3.  **Change the `"id"`** to a unique value.
4.  **Customize the agent's properties**:
    *   `"display_name"`: The agent's name.
    *   `"needs"`: You can adjust the initial values, and decay rates of the agent's needs.
    *   `"actions"`: A list of action names (from `action_templates.json`) that this agent can perform.

## Adding a New Action

This is a more advanced form of modding that allows you to change the AI's behavior.

1.  **Open `content/data/action_templates.json`**.
2.  **Copy an existing action object**.
3.  **Change the `"name"`** to something unique.
4.  **Define the action's logic**:
    *   `"preconditions"`: When is this action available? For example, the "Eat" action is only available when the agent's Hunger is below a certain threshold and there is a "food" item nearby.
    *   `"effects"`: What happens when the action is completed? For example, the "Eat" action increases the agent's Hunger.
    *   `"score"`: How does the AI decide to perform this action? The score is typically based on the agent's needs. For example, the score for the "Eat" action is high when the agent's Hunger is low.

## Important Notes

-   **IDs must be unique.** If you have two items with the same `id`, the game will likely misbehave.
-   **Categories are important.** The AI uses item categories to decide which actions to perform. If you create a new food item, make sure to include the `"food"` category.
-   **Backup your files.** Before making any changes, it's always a good idea to make a backup of the original data files.
