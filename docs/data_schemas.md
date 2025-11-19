# Data Schemas

This document describes the structure of the JSON files used to define the game's content. All content data is located in the `content/data/` directory.

## `agent_archetypes.json`

This file defines the different types of agents (Yukkuris) that can exist in the game. Each object in the array represents one archetype.

```json
{
  "id": "basic_yukkuri",
  "display_name": "Yukkuri (Basic)",
  "portrait": "placeholders/images/yukkuri.png",
  "stats": { "speed": 1.0, "interaction_range": 1 },
  "needs": [
    {"name": "Hunger", "min": 0, "max": 100, "initial": 60, "decay_per_min": 6}
  ],
  "actions": ["Eat", "Sleep"],
  "dialogue_tags": ["greeting", "idle"]
}
```

-   `id`: A unique identifier for the archetype.
-   `display_name`: The name displayed in the UI.
-   `portrait`: Path to the portrait image.
-   `stats`: Game-mechanical properties of the agent.
-   `needs`: An array of need objects, defining the agent's needs.
-   `actions`: A list of action names that this agent is capable of performing.
-   `dialogue_tags`: A list of dialogue tags this agent can use.

## `item_definitions.json`

This file defines all the placeable items in the game.

```json
{
  "id": "food_bowl",
  "display_name": "Food Bowl",
  "sprite": "placeholders/images/food_bowl.png",
  "footprint": {"w": 1, "h": 1},
  "walk_blocking": false,
  "interact_slot": {"x": 0, "y": -1},
  "effects": {"Hunger": 35},
  "use_time_secs": 4.0,
  "cooldown_secs": 2.0,
  "categories": ["food"]
}
```

-   `id`: Unique identifier for the item.
-   `display_name`: Name displayed in the UI.
-   `sprite`: Path to the item's sprite.
-   `footprint`: The item's size in grid cells.
-   `walk_blocking`: Whether the item obstructs agent movement.
-   `interact_slot`: The relative position from the item's origin where agents interact with it.
-   `effects`: The changes to an agent's needs when the item is used.
-   `use_time_secs`: How long it takes to use the item.
-   `cooldown_secs`: Cooldown before the item can be used again.
-   `categories`: A list of tags used to categorize the item.

## `action_templates.json`

This file defines the templates for the actions that agents can perform, which are the core of the utility AI's decision-making.

```json
{
  "name": "Eat",
  "preconditions": [
    {"type": "near_item_category", "category": "food", "radius": 3},
    {"type": "need_below", "need": "Hunger", "threshold": 70}
  ],
  "effects": [{"type": "modify_need", "need": "Hunger", "delta": 35}],
  "duration_secs": 4.0,
  "score": {
    "type": "weighted_sum",
    "terms": [{"signal": "need_inverse", "need": "Hunger", "weight": 1.0}]
  },
  "cooldown_secs": 5.0
}
```

-   `name`: The unique name of the action.
-   `preconditions`: A list of conditions that must be met for the action to be available.
-   `effects`: The outcomes of performing the action.
-   `duration_secs`: How long the action takes to complete.
-   `score`: The configuration for the utility AI's scoring function.
-   `cooldown_secs`: Cooldown before the agent can perform this action again.

## `dialogue_lines.json`

This file contains the dialogue lines that agents can speak.

```json
{
  "tag": "greeting",
  "lines": ["Take it easy!", "Hello~!"],
  "cooldown_secs": 10
}
```

-   `tag`: The category of the dialogue lines.
-   `lines`: A list of possible lines to say for this tag.
-   `cooldown_secs`: Cooldown before another line with this tag can be spoken.

## `room.json`

This file defines the properties of the game room.

```json
{
  "id": "starter_tank",
  "width": 20,
  "height": 12,
  "spawn_points": [{"x": 3, "y": 3}],
  "initial_inventory": ["food_bowl", "toy_ball"]
}
```

-   `id`: Unique identifier for the room.
-   `width`, `height`: The dimensions of the room in grid cells.
-   `spawn_points`: A list of possible locations where agents can spawn.
-   `initial_inventory`: A list of item IDs that the player starts with.
