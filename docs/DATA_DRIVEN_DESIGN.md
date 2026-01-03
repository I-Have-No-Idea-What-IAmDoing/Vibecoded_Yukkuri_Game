# Data Driven Design

The Yukkuri Raising Game is designed to be highly customizable through data files. Most game content, including Yukkuri types, items, and AI behaviors, is defined in TOML files located in the `data/` directory.

## TOML Format

TOML (Tom's Obvious, Minimal Language) is a simple configuration file format. It uses key-value pairs and sections.

## Directories

*   `data/yukkuris/`: Yukkuri types and animations.
*   `data/items/`: Item definitions.
*   `data/ai/`: AI actions and interactions.
*   `data/traits/`: Personality traits.
*   `data/`: Global configuration (`config.toml`, `rules.toml`).

## Adding Content

### Adding a New Yukkuri Type

1.  Open `data/yukkuris/types.toml`.
2.  Add a new section `[yukkuris.your_type_name]`.
3.  Define the properties:

```toml
[yukkuris.marisa]
name = "Marisa"
image = "marisa.png"  # Must be in assets/images/
max_health = 100
width = 64
height = 64
base_happiness = 50
cost = 100
description = "A standard Marisa yukkuri."
```

4.  Add animations (see [Animation System](animation.md)).

### Adding a New Item

1.  Open `data/items/items.toml`.
2.  Add a new section `[items.your_item_name]`.
3.  Define properties:

```toml
[items.cookie]
name = "Cookie"
image = "cookie.png"
cost = 10
nutrition = 20  # How much hunger it reduces
fun = 5         # How much happiness it gives
comfort = 0
is_portable = true # Can be carried by Yukkuris
```

### Modifying AI and Interactions

The AI is utility-based. See [AI System](ai_system.md) for details on modifying `data/ai/actions.toml`.

Interactions (social events) are defined in `data/ai/interactions.toml`. You can define new interactions or modify existing ones.

```toml
[interaction.Scream]
base_impact = -15.0
social_impact = { fear = 10.0 }
range_type = "auditory_loud" # visual, auditory, auditory_loud
```

### Modifying Game Rules

You can tweak global simulation rules in `data/rules.toml`, such as hunger decay rates and movement speeds.

```toml
[stat_decay]
hunger = 2.0      # Hunger points lost per second
happiness = 0.5
```

## Validation

The game validates data files on startup. If you make a mistake (e.g., missing a required field or using the wrong data type), the game will exit with an error message telling you what went wrong.
