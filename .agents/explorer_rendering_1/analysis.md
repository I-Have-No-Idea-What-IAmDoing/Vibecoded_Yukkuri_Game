# Design Analysis: Dynamic Sprite Loading & Animator System

This document outlines the detailed architectural design and implementation plan for Bevy 0.19 native rendering, dynamic sprite loading, sprite sheet atlases, virtual-time animations, and sync mechanics for the *Yukkuri Raising Game* port.

---

## 1. Requirements Reference

- **R1. Dynamic Sprite/Atlas Loading**: Load sprite dimensions and sheets dynamically from configuration (`data/yukkuris/types.toml`), compile Bevy `TextureAtlasLayout` structures on the fly, and assign them during prefab spawning in `src/prefabs/mod.rs`.
- **R2. Animator Component & System**: Implement `Animator` in Rust, support virtual time, speed multipliers, loop/ping-pong playback, frame-specific gameplay events, and legacy fallback behavior.

---

## 2. Architecture Overview

To maintain FFI boundary isolation and avoid name collisions with Bevy's built-in `Sprite` component, the system utilizes a custom `YukkuriSprite` component. A synchronization system bridges changes from the custom components to Bevy's native rendering components (`Sprite` and `TextureAtlas`).

```
 +------------------+     (Virtual Time)     +------------------+
 |    AI FFI /      | ---------------------> |    Animator      |
 |   Flight Sys     |                        |    Component     |
 +------------------+                        +------------------+
          |                                            |
          | (Sets current_action/flight override)      | (Updates frame indices)
          v                                            v
 +------------------+                        +------------------+
 |  YukkuriStats    |                        |   YukkuriSprite  | (Holds logical frame, flip,
 |  (Agility Mod)   |                        |    Component     |  and alpha state)
 +------------------+                        +------------------+
                                                       |
                                                       | (Resolves Asset handles)
                                                       v
                                             +------------------+
                                             |  Bevy Native     | (Renders image & slices
                                             | Sprite & Atlas   |  atlas coordinates)
                                             +------------------+
```

---

## 3. Data & Resource Structures

### A. Configuration Models (`src/render/config.rs` or in `mod.rs`)

We define the configuration structures matching `data/yukkuris/types.toml` schema:

```rust
use std::collections::HashMap;
use serde::Deserialize;

#[derive(Debug, Deserialize, Clone)]
pub struct AnimationDefConfig {
    pub frames: Vec<usize>,
    pub frame_duration: f32,
    #[serde(default = "default_true")]
    pub loop_anim: bool,
    #[serde(default)]
    pub ping_pong: bool,
    #[serde(default)]
    pub events: HashMap<usize, String>,
    pub image: Option<String>,
    pub width: Option<u32>,
    pub height: Option<u32>,
}

fn default_true() -> bool {
    true
}

#[derive(Debug, Deserialize, Clone)]
pub struct YukkuriTypeConfig {
    pub name: String,
    pub image: String,
    pub width: u32,
    pub height: u32,
    pub max_health: f32,
    pub base_happiness: f32,
    pub cost: u32,
    #[serde(default)]
    pub animations: HashMap<String, AnimationDefConfig>,
    #[serde(default = "default_one_u32")]
    pub frame_count: u32,
    #[serde(default = "default_duration")]
    pub frame_duration: f32,
    #[serde(default = "default_true")]
    pub loop_anim: bool,
}

fn default_one_u32() -> u32 {
    1
}

fn default_duration() -> f32 {
    0.1
}

#[derive(Debug, Deserialize, Clone)]
pub struct YukkuriTypesToml {
    pub yukkuris: HashMap<String, YukkuriTypeConfig>,
}
```

### B. Global Registries (`src/render/resources.rs`)

These resources hold parsed type configs and active `TextureAtlasLayout` handles:

```rust
use bevy::prelude::*;
use std::collections::HashMap;

#[derive(Resource, Debug, Default, Clone)]
pub struct YukkuriTypeRegistry {
    pub types: HashMap<String, YukkuriTypeConfig>,
}

#[derive(Resource, Debug, Default, Clone)]
pub struct TextureAtlasRegistry {
    // Maps (image_path, frame_width, frame_height) -> layout handle
    pub layouts: HashMap<(String, u32, u32), Handle<TextureAtlasLayout>>,
    // Cache of loaded image handles to prevent garbage collection
    pub images: HashMap<String, Handle<Image>>,
}
```

### C. Animator & Component Structures (`src/render/components.rs`)

The logical visual components used by gameplay systems:

```rust
use bevy::prelude::*;
use std::collections::HashMap;

#[derive(Debug, Clone)]
pub struct AnimationDefinition {
    pub name: String,
    pub frames: Vec<usize>,
    pub frame_duration: f32,
    pub loop_anim: bool,
    pub ping_pong: bool,
    pub events: HashMap<usize, String>,
    pub image_handle: Handle<Image>,
    pub layout_handle: Handle<TextureAtlasLayout>,
}

#[derive(Component, Debug, Clone)]
pub struct Animator {
    pub animations: HashMap<String, AnimationDefinition>,
    pub current_animation: String,
    pub current_frame_index: usize,
    pub timer: f32,
    pub finished: bool,
    pub speed: f32,
    pub next_animation: Option<String>,
    pub forward: bool,
}

#[derive(Component, Debug, Clone)]
pub struct YukkuriSprite {
    pub image_name: String,
    pub width: u32,
    pub height: u32,
    pub layer: u32,
    pub flip_x: bool,
    pub flip_y: bool,
    pub alpha: u8,
    // Fallback/Simple frame-based animation fields
    pub frame_count: u32,
    pub frame_duration: f32,
    pub current_frame: usize,
    pub timer: f32,
    pub loop_anim: bool,
    pub is_animating: bool,
}
```

### D. Events (`src/render/events.rs`)

Fired by the Animator system on specific animation frame milestones:

```rust
use bevy::prelude::*;

#[derive(Event, Debug, Clone)]
pub struct AnimationEvent {
    pub entity: Entity,
    pub event_name: String,
    pub animation_name: String,
    pub frame_index: usize,
}
```

---

## 4. Dynamic Atlas Loading (R1)

### A. PNG Header Dimension Parser

Because Bevy loads image assets asynchronously, we cannot synchronously retrieve image dimensions from `Handle<Image>` immediately at startup. We implement a synchronous PNG parser that reads metadata directly from disk:

```rust
use std::fs::File;
use std::io::Read;
use std::path::Path;

pub fn get_png_dimensions<P: AsRef<Path>>(path: P) -> Option<(u32, u32)> {
    let mut file = File::open(path).ok()?;
    let mut header = [0u8; 24];
    file.read_exact(&mut header).ok()?;
    
    // Validate PNG Signature: [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]
    if header[0..8] != [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A] {
        return None;
    }
    
    // Width (16-19) and Height (20-23) are big-endian u32
    let width = u32::from_be_bytes([header[16], header[17], header[18], header[19]]);
    let height = u32::from_be_bytes([header[20], header[21], header[22], header[23]]);
    
    Some((width, height))
}
```

### B. Startup Load & Registration System

On startup, Bevy loads the configuration file, parses PNG dimensions, registers layouts in `Assets<TextureAtlasLayout>`, and populates the registries:

```rust
use std::fs;

pub fn setup_graphics_assets_system(
    asset_server: Res<AssetServer>,
    mut texture_layouts: ResMut<Assets<TextureAtlasLayout>>,
    mut type_registry: ResMut<YukkuriTypeRegistry>,
    mut atlas_registry: ResMut<TextureAtlasRegistry>,
) {
    let manifest_dir = env!("CARGO_MANIFEST_DIR");
    let types_path = format!("{}/data/yukkuris/types.toml", manifest_dir);
    
    let content = fs::read_to_string(&types_path)
        .expect("Failed to read data/yukkuris/types.toml");
    let toml_data: YukkuriTypesToml = toml::from_str(&content)
        .expect("Failed to deserialize types.toml");
        
    type_registry.types = toml_data.yukkuris;
    
    // Scan all registered types and build texture layouts
    for (_type_id, config) in type_registry.types.iter() {
        let base_img_name = config.image.clone();
        register_atlas_layout(
            &base_img_name,
            config.width,
            config.height,
            manifest_dir,
            &asset_server,
            &mut texture_layouts,
            &mut atlas_registry,
        );
        
        // Also pre-register any animation overrides
        for (_, anim_cfg) in config.animations.iter() {
            if let Some(ref custom_img) = anim_cfg.image {
                let w = anim_cfg.width.unwrap_or(config.width);
                let h = anim_cfg.height.unwrap_or(config.height);
                register_atlas_layout(
                    custom_img,
                    w,
                    h,
                    manifest_dir,
                    &asset_server,
                    &mut texture_layouts,
                    &mut atlas_registry,
                );
            }
        }
    }
}

fn register_atlas_layout(
    img_name: &str,
    frame_width: u32,
    frame_height: u32,
    manifest_dir: &str,
    asset_server: &AssetServer,
    texture_layouts: &mut Assets<TextureAtlasLayout>,
    atlas_registry: &mut TextureAtlasRegistry,
) {
    let key = (img_name.to_string(), frame_width, frame_height);
    if atlas_registry.layouts.contains_key(&key) {
        return;
    }
    
    let asset_path = format!("images/{}", img_name);
    let full_path = format!("{}/assets/{}", manifest_dir, asset_path);
    
    // Extract sheet dimensions
    let (sheet_width, sheet_height) = get_png_dimensions(&full_path)
        .unwrap_or((frame_width, frame_height)); // Fallback if file not found or not PNG (e.g. bed.jpg)
        
    let columns = sheet_width / frame_width;
    let rows = sheet_height / frame_height;
    
    let layout = TextureAtlasLayout::from_grid(
        UVec2::new(frame_width, frame_height),
        columns,
        rows,
        None,
        None,
    );
    
    let layout_handle = texture_layouts.add(layout);
    let img_handle = asset_server.load(asset_path);
    
    atlas_registry.layouts.insert(key, layout_handle);
    atlas_registry.images.insert(img_name.to_string(), img_handle);
}
```

---

## 5. Animator & Sync Systems (R2)

### A. Animator Update System (`src/render/systems.rs`)

Updates entities with `Animator` and `YukkuriSprite`. Multiplies frame advance speed by both Animator parameters and optional `YukkuriStats::agility` attributes (clamped to 1.5 maximum).

```rust
pub fn update_animator_system(
    time: Res<Time>,
    mut query: Query<(Entity, &mut Animator, &mut YukkuriSprite, Option<&YukkuriStats>)>,
    mut event_writer: EventWriter<AnimationEvent>,
) {
    let base_dt = time.delta_secs();
    
    for (entity, mut animator, mut sprite, maybe_stats) in query.iter_mut() {
        let current_anim = animator.current_animation.to_lowercase();
        let anim_def = match animator.animations.get(&current_anim) {
            Some(def) => def,
            None => continue,
        };
        
        // Sync overrides from animation definition onto sprite
        sprite.image_name = anim_def.image_handle.path().unwrap().to_string(); // or original name
        // (For simplicity, we map override handles directly during sync system instead of name string)
        
        if animator.finished {
            if let Some(ref next) = animator.next_animation {
                if animator.animations.contains_key(&next.to_lowercase()) {
                    let next_name = next.clone();
                    switch_animation(&mut animator, &next_name);
                }
            }
            continue;
        }
        
        let agility_mod = if let Some(stats) = maybe_stats {
            // Placeholder: Assume agility is fetched or defaulting to 1.0
            // (Need to extend YukkuriStats struct in src/ai/mod.rs to include agility)
            1.0 // stats.agility.min(1.5)
        } else {
            1.0
        };
        
        let effective_dt = base_dt * animator.speed * agility_mod;
        animator.timer += effective_dt;
        
        let mut frame_changed = false;
        while animator.timer >= anim_def.frame_duration {
            animator.timer -= anim_def.frame_duration;
            frame_changed = true;
            
            let frame_len = anim_def.frames.len();
            if anim_def.ping_pong {
                if animator.forward {
                    animator.current_frame_index += 1;
                    if animator.current_frame_index >= frame_len {
                        if frame_len > 1 {
                            animator.current_frame_index = frame_len - 2;
                            animator.forward = false;
                        } else {
                            animator.current_frame_index = 0;
                        }
                    }
                } else {
                    if animator.current_frame_index > 0 {
                        animator.current_frame_index -= 1;
                    } else {
                        if frame_len > 1 {
                            animator.current_frame_index = 1;
                            animator.forward = true;
                        } else {
                            animator.current_frame_index = 0;
                        }
                    }
                }
            } else {
                animator.current_frame_index += 1;
                if animator.current_frame_index >= frame_len {
                    if anim_def.loop_anim {
                        animator.current_frame_index = 0;
                    } else {
                        animator.current_frame_index = frame_len - 1;
                        animator.finished = true;
                    }
                }
            }
            
            if frame_changed {
                if let Some(event_name) = anim_def.events.get(&animator.current_frame_index) {
                    event_writer.send(AnimationEvent {
                        entity,
                        event_name: event_name.clone(),
                        animation_name: animator.current_animation.clone(),
                        frame_index: animator.current_frame_index,
                    });
                }
            }
            
            if animator.finished {
                break;
            }
        }
        
        // Sync frame index to sprite
        if animator.current_frame_index < anim_def.frames.len() {
            sprite.current_frame = anim_def.frames[animator.current_frame_index];
        }
        
        // Immediate transition check
        if animator.finished {
            if let Some(ref next) = animator.next_animation {
                if animator.animations.contains_key(&next.to_lowercase()) {
                    let next_name = next.clone();
                    switch_animation(&mut animator, &next_name);
                    
                    let new_def = &animator.animations[&animator.current_animation.to_lowercase()];
                    if animator.current_frame_index < new_def.frames.len() {
                        sprite.current_frame = new_def.frames[animator.current_frame_index];
                    }
                }
            }
        }
    }
}

fn switch_animation(animator: &mut Animator, new_anim: &str) {
    animator.current_animation = new_anim.to_string();
    animator.current_frame_index = 0;
    animator.timer = 0.0;
    animator.finished = false;
    animator.forward = true;
}
```

### B. Legacy Fallback Animation System

Handles simple sprites without an `Animator` component attached:

```rust
pub fn update_fallback_animation_system(
    time: Res<Time>,
    mut query: Query<&mut YukkuriSprite, Without<Animator>>,
) {
    let dt = time.delta_secs();
    for mut sprite in query.iter_mut() {
        if !sprite.is_animating || sprite.frame_count <= 1 {
            continue;
        }
        
        sprite.timer += dt;
        while sprite.timer >= sprite.frame_duration {
            sprite.timer -= sprite.frame_duration;
            sprite.current_frame += 1;
            
            if sprite.current_frame >= sprite.frame_count as usize {
                if sprite.loop_anim {
                    sprite.current_frame = 0;
                } else {
                    sprite.current_frame = sprite.frame_count as usize - 1;
                    sprite.is_animating = false;
                    break;
                }
            }
        }
    }
}
```

### C. Bevy Native Renderer Synchronization System

Translates logical `YukkuriSprite` states into Bevy's built-in `Sprite` (or `TextureAtlas`) components. Coordinates changes in scale, flips, texture overrides, and color alpha transparency:

```rust
pub fn sync_bevy_sprite_system(
    mut commands: Commands,
    atlas_registry: Res<TextureAtlasRegistry>,
    query: Query<(Entity, &YukkuriSprite, Option<&Animator>)>,
    mut bevy_sprite_query: Query<&mut Sprite>,
) {
    for (entity, yukkuri_sprite, maybe_animator) in query.iter() {
        // Resolve appropriate image handle and atlas layout
        let (image_handle, layout_handle) = if let Some(animator) = maybe_animator {
            let current_anim = animator.current_animation.to_lowercase();
            if let Some(def) = animator.animations.get(&current_anim) {
                (def.image_handle.clone(), Some(def.layout_handle.clone()))
            } else {
                continue;
            }
        } else {
            // Fallback base configuration
            let img_name = &yukkuri_sprite.image_name;
            let img_handle = match atlas_registry.images.get(img_name) {
                Some(h) => h.clone(),
                None => continue,
            };
            
            let layout_handle = if yukkuri_sprite.frame_count > 1 {
                let key = (img_name.clone(), yukkuri_sprite.width, yukkuri_sprite.height);
                atlas_registry.layouts.get(&key).cloned()
            } else {
                None
            };
            
            (img_handle, layout_handle)
        };
        
        let texture_atlas = layout_handle.map(|layout| TextureAtlas {
            layout,
            index: yukkuri_sprite.current_frame,
        });
        
        let alpha_f32 = yukkuri_sprite.alpha as f32 / 255.0;
        let sprite_color = Color::srgba(1.0, 1.0, 1.0, alpha_f32);
        
        if let Ok(mut bevy_sprite) = bevy_sprite_query.get_mut(entity) {
            bevy_sprite.image = image_handle;
            bevy_sprite.texture_atlas = texture_atlas;
            bevy_sprite.flip_x = yukkuri_sprite.flip_x;
            bevy_sprite.flip_y = yukkuri_sprite.flip_y;
            bevy_sprite.color = sprite_color;
        } else {
            // Insert Bevy native components if not present
            commands.entity(entity).insert((
                Sprite {
                    image: image_handle,
                    texture_atlas,
                    flip_x: yukkuri_sprite.flip_x,
                    flip_y: yukkuri_sprite.flip_y,
                    color: sprite_color,
                    ..default()
                },
            ));
        }
    }
}
```

---

## 6. Integration with Prefab Spawning

The spawning signature in `src/prefabs/mod.rs` must be expanded to reference our type registries and asset servers, assigning scale multipliers to `Transform` based on `growth_stage` configuration:

```rust
pub fn spawn_yukkuri_prefab(
    commands: &mut Commands,
    prefab: &YukkuriPrefab,
    position: Vec2,
    asset_server: &AssetServer,
    atlas_registry: &TextureAtlasRegistry,
    type_registry: &YukkuriTypeRegistry,
) -> Entity {
    let scale_factor = match prefab.prefab.growth_stage.as_str() {
        "Baby" => 0.5,
        "Child" => 0.75,
        _ => 1.0,
    };
    
    let type_id = &prefab.prefab.type_id;
    let type_config = type_registry.types.get(type_id)
        .expect("spawning prefab with unregistered type_id");
        
    let image_name = type_config.image.clone();
    let frame_count = type_config.frame_count;
    let frame_duration = type_config.frame_duration;
    let loop_anim = type_config.loop_anim;
    
    let yukkuri_sprite = YukkuriSprite {
        image_name,
        width: type_config.width,
        height: type_config.height,
        layer: 2, // LAYER_ENTITIES
        flip_x: false,
        flip_y: false,
        alpha: 255,
        frame_count,
        frame_duration,
        current_frame: 0,
        timer: 0.0,
        loop_anim,
        is_animating: frame_count > 1,
    };
    
    let animator = crate::render::build_animator(
        type_id,
        asset_server,
        atlas_registry,
        type_registry,
    );
    
    let mut entity_commands = commands.spawn((
        // Scale applied directly to transform
        Transform::from_xyz(position.x, position.y, 0.0)
            .with_scale(Vec3::splat(scale_factor)),
        Visibility::default(),
        yukkuri_sprite,
        // ... physics and need components
    ));
    
    if let Some(anim) = animator {
        entity_commands.insert(anim);
    }
    
    let entity_id = entity_commands.id();
    commands.entity(entity_id).insert(StableId::from_entity(entity_id));
    
    entity_id
}
```

---

## 7. FFI & State Sync Design

### A. Mapping `CommandType::PlayAnimation`

When Bevy pops AI commands, `CommandType::PlayAnimation` will be processed inside the existing command dispatcher system `apply_ai_commands`:

- **Payload key**: `"animation_name"`: Target animation (e.g. `"eat"`, `"sleep"`).
- **Payload key**: `"next_animation"` (optional): Chain animation (e.g. `"idle"`).
- **Payload key**: `"speed"` (optional stringified float): Speed multiplier.

```rust
// Inside apply_ai_commands system:
CommandType::PlayAnimation => {
    let anim_name = cmd.payload.get("animation_name").cloned().unwrap_or_default();
    let next_anim = cmd.payload.get("next_animation").cloned();
    let speed = cmd.payload.get("speed")
        .and_then(|v| v.parse::<f32>().ok())
        .unwrap_or(1.0);
        
    if let Some(mut animator) = animator_query.get_mut(bevy_entity) {
        switch_animation(&mut animator, &anim_name);
        animator.next_animation = next_anim;
        animator.speed = speed;
    }
}
```

### B. Overrides Sync System

The game automatically overrides current animations based on flight states and AI states. We execute a sync system *before* the animator system updates:

```rust
pub fn sync_ai_and_flight_animations_system(
    mut query: Query<(&AIState, Option<&Flight>, &mut Animator)>,
) {
    for (ai_state, maybe_flight, mut animator) in query.iter_mut() {
        let mut target_anim = ai_state.current_action.to_lowercase();
        
        if let Some(flight) = maybe_flight {
            // flight_state mappings:
            // 5: SWOOPING -> "swoop"
            // 1, 2, 3: TAKEOFF, FLYING, HOVERING -> "fly"
            if flight.flight_state == 5 {
                target_anim = "swoop".to_string();
            } else if flight.flight_state >= 1 && flight.flight_state <= 3 {
                target_anim = "fly".to_string();
            }
        }
        
        if animator.animations.contains_key(&target_anim) && animator.current_animation != target_anim {
            switch_animation(&mut animator, &target_anim);
        }
    }
}
```
