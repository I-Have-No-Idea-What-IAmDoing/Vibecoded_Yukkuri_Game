# Analysis & Design: FFI Animation Command Parsing & AIState/Flight Sync

This analysis report provides a read-only investigation and complete design specification for Milestone 3 (FFI & Action Animation Sync) under Milestone R2. It details the Rust implementation of the sprite animation system, FFI command dispatching for `PlayAnimation`, and state synchronization with `AIState` and flight states.

---

## 1. Executive Summary

The objective of this design is to enable Bevy 0.19 to parse and execute `CommandType::PlayAnimation` commands dispatched from Python behavior trees and to synchronize entity animations with their active `AIState` and `Flight` states. 

Key design outcomes include:
1. **Rust Animation Components**: Creation of `AnimationDefinition` and `Animator` components mirroring their Python equivalents.
2. **Animation Update System**: A Bevy system (`update_animator_system`) driven by `Time<Virtual>` to handle standard looping, ping-pong playback, speed multipliers, and sprite sheet index mapping.
3. **FFI Command Dispatching**: Mapping `CommandType::PlayAnimation` in `apply_ai_commands` to switch active animations.
4. **State Synchronization**: A Bevy system (`sync_yukkuri_animations`) that automatically maps `AIState::current_action` and applies flight state overrides when entities are airborne, with a locking mechanism to prevent immediate overrides of manually triggered animations.
5. **Frame Events**: Emitter logic for firing `AnimationFrameEvent` when specific frames are entered.

---

## 2. Codebase Investigation & Python Reference

### 2.1. Python Animation State and Updates
In the Python codebase (`src/yukkuri_game/game/systems/animation.py`), the `AnimationSystem` updates the `Animator` component and syncs the calculated frame index to the `Sprite` component.
Key details:
- **Ping-Pong Animation**:
  ```python
  if current_anim_def.ping_pong:
      if animator.forward:
          animator.current_frame_index += 1
          if animator.current_frame_index >= len(current_anim_def.frames):
              animator.current_frame_index -= 2
              animator.forward = False
              # ... handle edge cases ...
      else:
          animator.current_frame_index -= 1
          if animator.current_frame_index < 0:
              animator.current_frame_index = 1
              animator.forward = True
  ```
- **LOD Optimization**: Updating is skipped or throttled based on `LODComponent`.
- **AIState Sync**: The active action is converted to lowercase and synced:
  ```python
  target_anim = ai_state.current_action.lower()
  ```
- **Flight Overrides**: If the entity has a `Flight` component and its state is airborne:
  - `FlightState.SWOOPING` -> plays `"swoop"` animation.
  - Other flight states (`FLYING`, `TAKEOFF`, `HOVERING`) -> play `"fly"` animation.

### 2.2. Python FFI Command Structure
The Python FFI entry point (`tick_entity_with_blackboard` in `src/yukkuri_game/game/systems/behavior_ffi.py`) extracts and translates commands to their Rust counterparts.
The `PLAY_ANIMATION` command type maps to `RustCommandType.PlayAnimation`.
The payload contains:
- `animation_name`: The name of the animation to play (e.g. `"jump"`, `"eat"`, `"speak"`).
- Additional payload parameters (like `speed` or `loop`) can be optionally provided and parsed.

---

## 3. Rust/Bevy Design Specifications

### 3.1. Data Models & Components

We propose defining the following structures, co-located in a new module `src/render/mod.rs` (or `src/render.rs`) or in `src/ai/mod.rs` as appropriate. To keep layouts clean, defining them in `src/render/mod.rs` is recommended.

#### `AnimationDefinition`
Holds metadata for a single animation sequence, deserialized from TOML configurations (e.g., `data/yukkuris/types.toml`).
```rust
use serde::Deserialize;
use std::collections::HashMap;

#[derive(Debug, Deserialize, Clone)]
pub struct AnimationDefinition {
    /// Name of the animation.
    pub name: String,
    /// Indices of the frames in the texture atlas.
    pub frames: Vec<usize>,
    /// Duration of each frame in seconds.
    pub frame_duration: f32,
    /// Whether the animation loops.
    #[serde(rename = "loop", default = "default_true")]
    pub loop_: bool,
    /// Whether to play frames back-and-forth.
    #[serde(default)]
    pub ping_pong: bool,
    /// Mapping of frame index (within the `frames` list) to custom event names.
    #[serde(default)]
    pub events: HashMap<usize, String>,
    /// Optional sprite sheet image override.
    pub image: Option<String>,
    /// Optional frame width override.
    pub width: Option<u32>,
    /// Optional frame height override.
    pub height: Option<u32>,
}

fn default_true() -> bool {
    true
}
```

#### `Animator` Component
Tracks active animation playback. Added to entities spawned via prefabs that have animated sheets.
```rust
use bevy::prelude::Component;
use std::collections::HashMap;

#[derive(Component, Debug, Clone)]
pub struct Animator {
    /// Active animation library for the entity.
    pub animations: HashMap<String, AnimationDefinition>,
    /// The currently active animation name (keys are lowercased).
    pub current_animation: String,
    /// Current index into the frames list of the active animation.
    pub current_frame_index: usize,
    /// Cumulative elapsed time (seconds) in the current frame.
    pub timer: f32,
    /// Set to true when a non-looping animation reaches the end.
    pub finished: bool,
    /// Speed multiplier for delta time.
    pub speed: f32,
    /// Optional name of the animation to switch to upon completion.
    pub next_animation: Option<String>,
    /// Flag for tracking direction in ping-pong playback (true = forward, false = reverse).
    pub forward: bool,
    /// Manual override flag to protect FFI-driven animations from state sync overwrites.
    pub manual_override: bool,
    /// Captured AIState action when manual override was activated.
    pub ai_action_at_override: String,
}
```

#### `AnimationFrameEvent` Event
Fired in Bevy when a frame with an associated event is entered.
```rust
use bevy::prelude::{Event, Entity};

#[derive(Event, Debug, Clone)]
pub struct AnimationFrameEvent {
    pub entity: Entity,
    pub event_name: String,
    pub animation_name: String,
    pub frame_index: usize,
}
```

---

## 4. Systems Design & Logic Flow

### 4.1. Animator Update System
Calculates frame progression based on `Time<Virtual>`. Updates the underlying Bevy `Sprite::texture_atlas::index` for drawing.

```rust
use bevy::prelude::*;

pub fn update_animator_system(
    time: Res<Time<Virtual>>,
    mut query: Query<(Entity, &mut Animator, &mut Sprite)>,
    mut event_writer: EventWriter<AnimationFrameEvent>,
) {
    let dt = time.delta_secs();

    for (entity, mut animator, mut sprite) in query.iter_mut() {
        if animator.finished {
            // Auto-transition to next animation if defined
            if let Some(ref next_anim) = animator.next_animation {
                let next = next_anim.to_lowercase();
                if animator.animations.contains_key(&next) {
                    switch_animation(&mut animator, &next);
                }
            }
            continue;
        }

        let current_anim = animator.current_animation.clone();
        let anim_def = match animator.animations.get(&current_anim) {
            Some(def) => def,
            None => continue,
        };

        let num_frames = anim_def.frames.len();
        if num_frames == 0 {
            continue;
        }

        // Apply speed modifier
        animator.timer += dt * animator.speed;

        let frame_duration = anim_def.frame_duration;
        let mut frame_changed = false;

        while animator.timer >= frame_duration {
            animator.timer -= frame_duration;

            if anim_def.ping_pong {
                if animator.forward {
                    animator.current_frame_index += 1;
                    if animator.current_frame_index >= num_frames {
                        if num_frames > 1 {
                            animator.current_frame_index = num_frames - 2;
                            animator.forward = false;
                        } else {
                            animator.current_frame_index = 0;
                            animator.forward = true;
                        }
                    }
                } else {
                    if animator.current_frame_index > 0 {
                        animator.current_frame_index -= 1;
                    } else {
                        if num_frames > 1 {
                            animator.current_frame_index = 1;
                            animator.forward = true;
                        } else {
                            animator.current_frame_index = 0;
                            animator.forward = true;
                        }
                    }
                }
            } else {
                animator.current_frame_index += 1;
                if animator.current_frame_index >= num_frames {
                    if anim_def.loop_ {
                        animator.current_frame_index = 0;
                    } else {
                        animator.current_frame_index = num_frames - 1;
                        animator.finished = true;
                    }
                }
            }

            frame_changed = true;

            // Trigger animation frame event if defined
            if let Some(event_name) = anim_def.events.get(&animator.current_frame_index) {
                event_writer.send(AnimationFrameEvent {
                    entity,
                    event_name: event_name.clone(),
                    animation_name: current_anim.clone(),
                    frame_index: animator.current_frame_index,
                });
            }

            if animator.finished {
                break;
            }
        }

        // Sync index to Bevy's Sprite TextureAtlas field
        if animator.current_frame_index < num_frames {
            let actual_index = anim_def.frames[animator.current_frame_index];
            if let Some(ref mut atlas) = sprite.texture_atlas {
                atlas.index = actual_index;
            }
        }

        // Handle immediate transition on end of playback
        if animator.finished {
            if let Some(ref next_anim) = animator.next_animation {
                let next = next_anim.to_lowercase();
                if animator.animations.contains_key(&next) {
                    switch_animation(&mut animator, &next);
                    
                    if let Some(new_def) = animator.animations.get(&animator.current_animation) {
                        if animator.current_frame_index < new_def.frames.len() {
                            let actual_index = new_def.frames[animator.current_frame_index];
                            if let Some(ref mut atlas) = sprite.texture_atlas {
                                atlas.index = actual_index;
                            }
                        }
                    }
                }
            }
        }
    }
}

/// Helper to switch active animation on an Animator
pub fn switch_animation(animator: &mut Animator, new_anim: &str) {
    let normalized = new_anim.to_lowercase();
    if animator.current_animation != normalized {
        animator.current_animation = normalized;
        animator.current_frame_index = 0;
        animator.timer = 0.0;
        animator.finished = false;
        animator.forward = true;
    }
}
```

### 4.2. FFI Command Parsing & Dispatching
In `apply_ai_commands` (located in `src/ai/mod.rs`), we add parsing for `CommandType::PlayAnimation`. This updates the animator component and marks it as a manual override.

```rust
// Inside apply_ai_commands system, matching on CommandType:
CommandType::PlayAnimation => {
    let anim_name = cmd.payload.get("animation_name")
        .cloned()
        .unwrap_or_else(|| "default".to_string());
    let normalized = anim_name.to_lowercase();

    // Optional override parameters
    let speed = cmd.payload.get("speed")
        .and_then(|v| v.parse::<f32>().ok());
    let loop_override = cmd.payload.get("loop")
        .and_then(|v| v.parse::<bool>().ok());
    let next_anim = cmd.payload.get("next_animation")
        .cloned();

    // Query for Animator and AIState on the active entity
    if let Ok((entity, _, _, _)) = query.get_mut(bevy_entity) {
        if let Some(mut animator) = animator_query.get_mut(entity).ok() {
            if animator.animations.contains_key(&normalized) {
                switch_animation(&mut animator, &normalized);
                animator.manual_override = true;
                
                // Get current AI action to lock manual override
                if let Some(ai_state) = ai_state_query.get(entity).ok() {
                    animator.ai_action_at_override = ai_state.current_action.clone();
                }

                if let Some(s) = speed {
                    animator.speed = s;
                }
                if let Some(l) = loop_override {
                    if let Some(def) = animator.animations.get_mut(&normalized) {
                        def.loop_ = l;
                    }
                }
                if let Some(next) = next_anim {
                    animator.next_animation = Some(next);
                }
            } else {
                warn!("PlayAnimation command received unknown animation name: {}", normalized);
            }
        }
    }
}
```
*Note: In the above command parsing block, `animator_query` is `Query<&mut Animator>` and `ai_state_query` is `Query<&AIState>`.*

### 4.3. AIState & Flight Synchronization System
The `sync_yukkuri_animations` system synchronizes standard actions and flight state overrides. It includes a locking mechanism using `manual_override` and `ai_action_at_override` to ensure FFI-requested animations are not instantly overwritten by the default state sync in the same or subsequent frames.

```rust
pub fn sync_yukkuri_animations(
    mut query: Query<(Entity, &AIState, Option<&Flight>, &mut Animator)>,
) {
    for (entity, ai_state, maybe_flight, mut animator) in query.iter_mut() {
        // If manual override is active, check if the AI state/action has changed
        if animator.manual_override {
            if ai_state.current_action != animator.ai_action_at_override {
                // The AI state changed to a new action, clearing the manual override
                animator.manual_override = false;
            } else {
                // Keep manual animation active; skip state/flight sync
                continue;
            }
        }

        let mut target_anim = ai_state.current_action.to_lowercase();

        // Flight Overrides (airborne status takes precedence over current action)
        if let Some(flight) = maybe_flight {
            // flight_state != 0 (GROUNDED = 0)
            if flight.flight_state != 0 {
                if flight.flight_state == 5 { // SWOOPING
                    target_anim = "swoop".to_string();
                } else {
                    target_anim = "fly".to_string();
                }
            }
        }

        // Apply animation transition if it is defined
        if animator.animations.contains_key(&target_anim) {
            switch_animation(&mut animator, &target_anim);
        }
    }
}
```

---

## 5. Thread Safety, GIL Scheduling & Execution Order

To conform to PyO3 thread-safety rules:
- All FFI interactions run as exclusive systems or sequentially on the main thread in the `Update` schedule.
- The execution order of the animation and FFI systems should be scheduled inside the `AIPlugin` (or a rendering plugin) in `Update` as follows:
  1. `tick_python_ai_system` (runs behavior trees, pulls commands)
  2. `apply_ai_commands` (dispatches commands, including `PlayAnimation`)
  3. `sync_yukkuri_animations` (updates animator state from AIState/flight states)
  4. `update_animator_system` (advances timers, maps index to sprite sheet, fires events)
  
Registering these sequentially ensures commands are parsed first, then state overrides are reconciled, and finally frames are updated in a deterministic sequence:
```rust
app.add_systems(
    Update, 
    (
        tick_python_ai_system, 
        apply_ai_commands, 
        sync_yukkuri_animations, 
        update_animator_system
    ).chain()
);
```

---

## 6. Verification & Testing Strategy

To verify this implementation, the implementer must write or update integration tests in `tests/migration_test.rs` or `tests/rendering_camera_test.rs`. The test should initialize a headless Bevy app and verify:
1. **Initial Action Sync**: Spawning a yukkuri with `AIState::current_action = "Eat"` immediately transitions the animator to play the `"eat"` animation (if defined).
2. **Flight State Override**: Setting `flight.flight_state` to `2` (Flying) updates the animator to play `"fly"` instead of `"eat"`. Setting `flight.flight_state` to `5` (Swooping) updates the animator to play `"swoop"`.
3. **FFI Command Dispatch**: Pushing a `CommandType::PlayAnimation` for `"jump"` updates the animator's current animation to `"jump"` and sets `manual_override = true`.
4. **Override Protection**: Verifying that subsequent `sync_yukkuri_animations` ticks do NOT switch the animation back to `"eat"` or `"fly"` while `manual_override` is locked.
5. **Override Release**: Modifying `AIState::current_action` to `"Sleep"` releases the `manual_override` lock, causing the animator to sync to `"sleep"`.
6. **Frame Events**: Verifying that when the timer advances past `frame_duration`, Bevy's `EventReader<AnimationFrameEvent>` receives the correct event message.
