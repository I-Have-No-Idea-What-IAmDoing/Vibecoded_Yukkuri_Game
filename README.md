# Yukkuri Raising Game - MVP

## Setup
1. Ensure Python 3.11+ is installed.
2. Install dependencies:
   ```bash
   pip install -e .
   ```
3. Run the game:
   ```bash
   python -m src.yukkuri_game.main
   ```
   Or for headless mode:
   ```bash
   python -m src.yukkuri_game.main --headless
   ```

## Controls
- **Mouse Wheel**: Zoom In/Out
- **Middle Click + Drag**: Pan Camera
- **Left Click**: Select Yukkuri or Item. Place item (in placement mode).
- **Right Click**: Cancel placement mode.
- **UI**:
  - **Buy Reimu/Cookie**: Enter placement mode to add entities to the world.
  - **Time Controls**: Pause/Resume and change simulation speed (1x, 2x, 5x, 0.5x).
  - **Save/Load**: Persist game state.
  - **Sell**: Sell the selected Yukkuri (available in the entity info window).
  - **Train**: Increase Badge count (available in the entity info window).

## Customization
### Adding a New Yukkuri
Edit `data/yukkuris/types.toml`:
```toml
[yukkuris.new_type]
name = "New Type"
image = "image.png" # Place in assets/images/
max_health = 100
```

### Adding a New Item
Edit `data/items/items.toml`:
```toml
[items.new_item]
name = "New Item"
image = "item.png"
nutrition = 10
```

### AI Behavior
Edit `data/ai/actions.toml` to define new Utility Actions, Considerations, and Effects.
You can define effects like `move_random` or `interact_item`.

```toml
[actions.Eat]
weight = 2.0
[actions.Eat.effects]
type = "interact_item"
target_stat = "nutrition"
consume = true
stat_changes = { hunger = -20.0, happiness = 5.0 }

[[actions.Eat.considerations]]
name = "Hunger"
input = "hunger"
curve = "linear"
params = { m = 1.0, b = 0.0 }
```
