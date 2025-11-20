# Yukkuri Raising Game (MVP)

A modern reimagining of "Yukkuri Hakkei" using Python and Pygame-ce.

## Setup

1. **Prerequisites**: Python 3.11+
2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   # OR
   pip install .
   ```
   (If using `uv`, `uv pip install .`)

3. **Run the Game**:
   ```bash
   python src/main.py
   ```

## Controls

* **Left Click**: Select Yukkuri
* **Right Click**: Buy Food Pellet ($5)
* **Arrow Keys**: Pan Camera
* **+/-**: Zoom In/Out
* **S**: Sell Selected Yukkuri
* **T**: Train Selected Yukkuri (Cost: $10)
* **Ctrl+S**: Save Game
* **Ctrl+L**: Load Game
* **1/2/3**: Set Simulation Speed (1x, 2x, 5x)
* **Space**: Pause/Unpause

## Modding / Extensibility

The game is data-driven. You can add content by editing files in `data/`.

### Adding a New Yukkuri Type

Edit `data/yukkuri_types.toml`:

```toml
[yukkuri.my_new_type]
name = "MyType"
base_health = 120
base_hunger = 80
base_happiness = 100
growth_rate = 1.2
description = "A new yukkuri type."
image_color = "0, 255, 255"
```

### Adding a New Item

Edit `data/items.toml`:

```toml
[item.new_toy]
name = "Super Ball"
type = "toy"
value = 50
cost = 100
restore_happiness = 30
image_color = "255, 0, 255"
```

### Adding a New AI Action

Edit `data/ai_actions.toml`. Example: A "Dance" action that requires high happiness.

```toml
[action.dance]
name = "Dance"
type = "leisure"
cooldown = 8.0
duration = 4.0

[[action.dance.considerations]]
input = "happiness"
curve = "logistic"
m = 5.0
k = 0.8 # Only dance if very happy (>80%)
```

## Architecture

* **ECS**: Entity-Component-System architecture for game objects.
* **Utility AI**: Modular AI system using Utility Curves defined in TOML.
* **Data-Driven**: All game parameters are externalized.

