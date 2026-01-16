# Input System Documentation

The **Input System** in the Yukkuri Game Engine abstracts raw hardware input (keyboard, mouse) into semantic actions. It supports multiple contexts (e.g., Gameplay, Menu) with a priority-based consumption model.

## Core Concepts

### 1. Input Contexts (`InputContext`)
Input contexts interpret the same physical input differently depending on the game state. Contexts are defined in an `IntEnum` where higher values indicate higher priority.

- **`MENU` (Priority 10)**: Active during pause menus, main menu, etc.
- **`GAMEPLAY` (Priority 1)**: Active during normal gameplay.

### 2. Priority-Based Consumption
When multiple contexts are active:
1.  The Input Manager checks the highest priority active context first.
2.  If that context maps the input to an action, it "consumes" the input.
3.  Lower priority contexts never see the input if it was consumed by a higher one.

**Example**: If `ESCAPE` is mapped to "cancel" in `MENU` and "pause" in `GAMEPLAY`:
- If the Menu is open (`MENU` active), pressing `ESCAPE` triggers "cancel". The `GAMEPLAY` context is blocked from seeing it.
- If only `GAMEPLAY` is active, pressing `ESCAPE` triggers "pause".

## Architecture

- **`InputManager` (`engine/input_manager.py`)**: The central class.
    - Tracks raw hardware state (keys pressed, mouse pos).
    - Maintains active contexts.
    - Handles mappings.
    - Provides query methods (`is_action_pressed`, `is_action_just_pressed`).
- **`InputSystem` (`game/input_system.py`)**: An ECS System that queries the `InputManager` and triggers game logic (e.g., camera movement, tool usage).

## Default Mappings

### Gameplay Context
| Action | Key / Input | Description |
| :--- | :--- | :--- |
| `up`, `down`, `left`, `right` | Arrow Keys | Move camera |
| `pause` | `ESC` | Pause game |
| `interact` | `Z` | Generic interaction |
| `debug_toggle` | `F3` | Toggle debug overlay |
| `select` | Left Click | Select entity / UI |
| `place` | Left Click | Place held item/entity |
| `cancel_action` | Right Click | Cancel current tool |
| `pan` | Middle Click | Pan camera |
| `time_speed_up` | `+` (Equals) | Increase game speed |
| `time_speed_down` | `-` (Minus) | Decrease game speed |
| `screenshot` | `F12` | Take screenshot |
| `quicksave` | `F5` | Quicksave game |
| `quickload` | `F9` | Quickload game |

### Menu Context
| Action | Key / Input | Description |
| :--- | :--- | :--- |
| `confirm` | `ENTER` | Confirm selection |
| `cancel` | `ESC` | Go back / Close |
| `up`, `down` | Arrow Keys | Navigate menu |

## How to Add New Actions

1.  **Define the Action String**: Decide on a unique string key (e.g., "jump").
2.  **Add to Mappings**: Update `InputManager.__init__` in `src/yukkuri_game/engine/input_manager.py`.

```python
self._key_mappings[InputContext.GAMEPLAY]["jump"] = pygame.K_SPACE
```

3.  **Handle the Action**: Check for it in your system (e.g., `PlayerControlSystem`).

```python
input_service = world.services.get(InputService)
if input_service.is_action_just_pressed("jump"):
    # Executing jump logic
```
