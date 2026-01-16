# Animation System

The Yukkuri Game features a robust animation system that allows for defining complex sprite behaviors using data-driven configuration.

## Defining Animations

Animations are defined within the Yukkuri Type definitions (e.g., in `data/yukkuris/types.toml`). Each Yukkuri type can have a dictionary of animations.

### Structure

An `AnimationDefinition` has the following fields:

-   **frames** (`List[int]`): A list of indices pointing to frames in the sprite sheet (or implicit frames if using a single image).
-   **frame_duration** (`float`): The time in seconds each frame is displayed.
-   **loop** (`bool`, default: `true`): Whether the animation should restart from the beginning after finishing.
-   **ping_pong** (`bool`, default: `false`): If true, the animation plays forward to the end, then reverses back to the start, oscillating back and forth.
-   **events** (`Dict[int, str]`, optional): A mapping of frame indices to event names. When the animation reaches a specified frame, an `AnimationEvent` is published to the Event Bus.
-   **image** (`str`, optional): Overrides the base sprite image for this specific animation.
-   **width** / **height** (`int`, optional): Overrides the sprite dimensions for this animation.

### Example

```toml
[yukkuris.reimu.animations.walk]
frames = [0, 1, 2, 3]
frame_duration = 0.15
loop = true

[yukkuris.reimu.animations.sleep]
frames = [4, 5]
frame_duration = 0.5
loop = true
ping_pong = true # Breathing effect: 4 -> 5 -> 4 -> 5...

[yukkuris.reimu.animations.attack]
frames = [6, 7, 8]
frame_duration = 0.1
loop = false
events = { 7 = "attack_hit" } # Triggers "attack_hit" event at frame 7
```

## Runtime Features

The `Animator` component manages the playback of animations at runtime.

-   **Speed Multiplier**: Animations can be sped up or slowed down dynamically (e.g., based on movement speed or game speed).
-   **Auto-Transition**: The system supports automatic transitioning to a specific next animation upon completion (useful for chains like "Attack" -> "Idle"). *Note: Currently controlled via code logic.*
-   **AI Integration**: The `AIState` component automatically syncs with the `Animator`. If the AI enters an action (e.g., "Eat"), the system looks for an animation named "eat" and plays it.
-   **System Overrides**: Certain gameplay systems can override the AI animation. For example, the `FlightSystem` forces "fly" or "swoop" animations when a Yukkuri is airborne, regardless of its current AI action.

## Event Handling

When an animation triggers an event defined in the `events` map, an `AnimationEvent` is fired. Systems can subscribe to this event to perform gameplay logic synchronized with visuals.

**Event Attributes:**
-   `entity_id`: The ID of the entity playing the animation.
-   `animation_name`: The name of the current animation.
-   `event_name`: The string name defined in the TOML (e.g., "footstep", "hit").
-   `frame_index`: The frame index that triggered the event.
