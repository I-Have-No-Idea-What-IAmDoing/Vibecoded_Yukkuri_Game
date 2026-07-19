use bevy::prelude::*;
use serde::Deserialize;
use std::collections::HashMap;
use std::fs;
use std::path::Path;

pub mod lighting;

#[derive(Component, Debug, Clone, Reflect)]
#[reflect(Component)]
pub struct YukkuriShadow;

#[derive(Resource, Clone, Debug)]
pub struct ShadowTextureHandle(pub Handle<Image>);

fn create_shadow_image() -> Image {
    let size = 64;
    let mut data = vec![0u8; size * size * 4];
    for y in 0..size {
        for x in 0..size {
            let dx = (x as f32 - 31.5) / 32.0;
            let dy = (y as f32 - 31.5) / 32.0;
            let dist = (dx * dx + dy * dy).sqrt();
            let alpha = (1.0 - dist).clamp(0.0, 1.0).powf(2.0); // Soft radial falloff
            let idx = (y * size + x) * 4;
            data[idx] = 0;     // R
            data[idx + 1] = 0; // G
            data[idx + 2] = 0; // B
            data[idx + 3] = (alpha * 255.0) as u8; // A
        }
    }
    Image::new(
        bevy::render::render_resource::Extent3d {
            width: size as u32,
            height: size as u32,
            depth_or_array_layers: 1,
        },
        bevy::render::render_resource::TextureDimension::D2,
        data,
        bevy::render::render_resource::TextureFormat::Rgba8UnormSrgb,
        bevy::asset::RenderAssetUsages::default(),
    )
}



// --- Config structures matching data/yukkuris/types.toml schema ---

#[derive(Debug, Deserialize, Clone)]
pub struct AnimationDefConfig {
    pub frames: Vec<usize>,
    pub frame_duration: f32,
    #[serde(alias = "loop", default = "default_true")]
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

fn default_one_u32() -> u32 {
    1
}

fn default_duration() -> f32 {
    0.1
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
    pub is_prey: Option<bool>,
    #[serde(default)]
    pub can_fly: Option<bool>,
    #[serde(default)]
    pub max_altitude: Option<f32>,
    #[serde(default)]
    pub fly_stamina: Option<f32>,
    #[serde(default)]
    pub is_predator: Option<bool>,
    #[serde(default)]
    pub prey_tags: Option<Vec<String>>,
    #[serde(default)]
    pub prey_sense_radius: Option<f32>,
    #[serde(default)]
    pub aggression: Option<f32>,
    #[serde(default)]
    pub dps: Option<f32>,
    #[serde(default)]
    pub animations: HashMap<String, AnimationDefConfig>,
    #[serde(default = "default_one_u32")]
    pub frame_count: u32,
    #[serde(default = "default_duration")]
    pub frame_duration: f32,
    #[serde(default = "default_true")]
    pub loop_anim: bool,
}

#[derive(Debug, Deserialize, Clone)]
pub struct YukkuriTypesToml {
    pub yukkuris: HashMap<String, YukkuriTypeConfig>,
}

// --- Components ---

#[derive(Component, Debug, Clone)]
pub struct YukkuriSprite {
    pub image_name: String,
    pub width: u32,
    pub height: u32,
    pub layer: u32,
    pub flip_x: bool,
    pub flip_y: bool,
    pub alpha: u8,
    pub frame_count: u32,
    pub frame_duration: f32,
    pub current_frame: usize,
    pub timer: f32,
    pub loop_anim: bool,
    pub is_animating: bool,
    pub sprite_entity: Option<Entity>,
}

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
    pub manual_override: bool,
    pub ai_action_at_override: String,
}

// --- Resources ---

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

// --- Event ---

#[derive(Message, Debug, Clone)]
pub struct AnimationEvent {
    pub entity: Entity,
    pub event_name: String,
    pub animation_name: String,
    pub frame_index: usize,
}

// --- PNG Header parser ---

pub fn get_png_dimensions<P: AsRef<Path>>(path: P) -> Option<(u32, u32)> {
    use std::fs::File;
    use std::io::Read;
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

// --- Systems ---

pub fn setup_graphics_assets_system(
    mut commands: Commands,
    asset_server: Res<AssetServer>,
    mut texture_layouts: ResMut<Assets<TextureAtlasLayout>>,
    mut type_registry: ResMut<YukkuriTypeRegistry>,
    mut atlas_registry: ResMut<TextureAtlasRegistry>,
    mut images: ResMut<Assets<Image>>,
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

    // Procedurally generate shadow texture and insert handle as a resource
    let shadow_img = create_shadow_image();
    let shadow_handle = images.add(shadow_img);
    commands.insert_resource(ShadowTextureHandle(shadow_handle));
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
        .unwrap_or((frame_width, frame_height)); // Fallback if file not found or not PNG
        
    let columns = sheet_width / frame_width;
    let rows = sheet_height / frame_height;
    
    let layout = TextureAtlasLayout::from_grid(
        UVec2::new(frame_width, frame_height),
        columns.max(1),
        rows.max(1),
        None,
        None,
    );
    
    let layout_handle = texture_layouts.add(layout);
    let img_handle = asset_server.load(asset_path);
    
    atlas_registry.layouts.insert(key, layout_handle);
    atlas_registry.images.insert(img_name.to_string(), img_handle);
}

pub fn update_animator_system(
    time: Res<Time>,
    mut query: Query<(Entity, &mut Animator, &mut YukkuriSprite)>,
    mut event_writer: MessageWriter<'_, AnimationEvent>,
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
        let (frames, frame_duration, loop_anim, ping_pong, events) = {
            let anim_def = match animator.animations.get(&current_anim) {
                Some(def) => def,
                None => continue,
            };
            (
                anim_def.frames.clone(),
                anim_def.frame_duration,
                anim_def.loop_anim,
                anim_def.ping_pong,
                anim_def.events.clone(),
            )
        };

        let num_frames = frames.len();
        if num_frames == 0 {
            continue;
        }

        // Apply speed modifier
        animator.timer += dt * animator.speed;

        while animator.timer >= frame_duration {
            animator.timer -= frame_duration;

            if ping_pong {
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
                    if loop_anim {
                        animator.current_frame_index = 0;
                    } else {
                        animator.current_frame_index = num_frames - 1;
                        animator.finished = true;
                    }
                }
            }

            // Trigger animation frame event if defined
            if let Some(event_name) = events.get(&animator.current_frame_index) {
                event_writer.write(AnimationEvent {
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

        // Sync index to YukkuriSprite
        if animator.current_frame_index < num_frames {
            sprite.current_frame = frames[animator.current_frame_index];
        }

        // Handle immediate transition on end of playback
        if animator.finished {
            if let Some(ref next_anim) = animator.next_animation {
                let next = next_anim.to_lowercase();
                if animator.animations.contains_key(&next) {
                    switch_animation(&mut animator, &next);
                    
                    if let Some(new_def) = animator.animations.get(&animator.current_animation) {
                        if animator.current_frame_index < new_def.frames.len() {
                            sprite.current_frame = new_def.frames[animator.current_frame_index];
                        }
                    }
                }
            }
        }
    }
}

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

pub fn update_yukkuri_sprite_system(
    mut commands: Commands,
    atlas_registry: Res<TextureAtlasRegistry>,
    mut query: Query<(Entity, &mut YukkuriSprite, Option<&Animator>)>,
    mut bevy_sprite_query: Query<&mut Sprite>,
    time: Res<Time>,
) {
    let dt = time.delta_secs();
    for (entity, mut yukkuri_sprite, maybe_animator) in query.iter_mut() {
        // Legacy fallback tick if no animator is present
        if maybe_animator.is_none() && yukkuri_sprite.is_animating && yukkuri_sprite.frame_count > 1 {
            yukkuri_sprite.timer += dt;
            while yukkuri_sprite.timer >= yukkuri_sprite.frame_duration {
                yukkuri_sprite.timer -= yukkuri_sprite.frame_duration;
                yukkuri_sprite.current_frame += 1;
                if yukkuri_sprite.current_frame >= yukkuri_sprite.frame_count as usize {
                    if yukkuri_sprite.loop_anim {
                        yukkuri_sprite.current_frame = 0;
                    } else {
                        yukkuri_sprite.current_frame = yukkuri_sprite.frame_count as usize - 1;
                        yukkuri_sprite.is_animating = false;
                        break;
                    }
                }
            }
        }

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
        
        let sprite_target = yukkuri_sprite.sprite_entity.unwrap_or(entity);
        
        if let Ok(mut bevy_sprite) = bevy_sprite_query.get_mut(sprite_target) {
            bevy_sprite.image = image_handle;
            bevy_sprite.texture_atlas = texture_atlas;
            bevy_sprite.flip_x = yukkuri_sprite.flip_x;
            bevy_sprite.flip_y = yukkuri_sprite.flip_y;
            bevy_sprite.color = sprite_color;
        } else {
            commands.entity(sprite_target).insert(
                Sprite {
                    image: image_handle,
                    texture_atlas,
                    flip_x: yukkuri_sprite.flip_x,
                    flip_y: yukkuri_sprite.flip_y,
                    color: sprite_color,
                    ..default()
                },
            );
        }
    }
}

// --- Animator Builder ---

pub fn build_animator(
    type_id: &str,
    _asset_server: &AssetServer,
    atlas_registry: &TextureAtlasRegistry,
    type_registry: &YukkuriTypeRegistry,
) -> Option<Animator> {
    let config = type_registry.types.get(type_id)?;
    let mut anims = HashMap::new();

    for (name, anim_cfg) in config.animations.iter() {
        let name_lower = name.to_lowercase();
        
        let img_name = anim_cfg.image.as_ref().unwrap_or(&config.image);
        let w = anim_cfg.width.unwrap_or(config.width);
        let h = anim_cfg.height.unwrap_or(config.height);
        
        let img_handle = atlas_registry.images.get(img_name)?.clone();
        let layout_handle = atlas_registry.layouts.get(&(img_name.clone(), w, h))?.clone();
        
        anims.insert(name_lower.clone(), AnimationDefinition {
            name: name_lower,
            frames: anim_cfg.frames.clone(),
            frame_duration: anim_cfg.frame_duration,
            loop_anim: anim_cfg.loop_anim,
            ping_pong: anim_cfg.ping_pong,
            events: anim_cfg.events.clone(),
            image_handle: img_handle,
            layout_handle,
        });
    }

    // Fallback if no animations are configured but frame_count > 1
    if anims.is_empty() && config.frame_count > 1 {
        let img_name = &config.image;
        let w = config.width;
        let h = config.height;
        
        let img_handle = atlas_registry.images.get(img_name)?.clone();
        let layout_handle = atlas_registry.layouts.get(&(img_name.clone(), w, h))?.clone();
        
        let idle_anim = AnimationDefinition {
            name: "idle".to_string(),
            frames: (0..config.frame_count as usize).collect(),
            frame_duration: config.frame_duration,
            loop_anim: config.loop_anim,
            ping_pong: false,
            events: HashMap::new(),
            image_handle: img_handle,
            layout_handle,
        };
        anims.insert("idle".to_string(), idle_anim.clone());
        let mut walk_anim = idle_anim.clone();
        walk_anim.name = "walk".to_string();
        anims.insert("walk".to_string(), walk_anim);
    }

    if anims.is_empty() {
        return None;
    }

    let current_animation = if anims.contains_key("idle") {
        "idle".to_string()
    } else {
        anims.keys().next()?.clone()
    };

    Some(Animator {
        animations: anims,
        current_animation,
        current_frame_index: 0,
        timer: 0.0,
        finished: false,
        speed: 1.0,
        next_animation: None,
        forward: true,
        manual_override: false,
        ai_action_at_override: String::new(),
    })
}

pub fn update_shadow_system(
    mut commands: Commands,
    shadow_texture: Option<Res<ShadowTextureHandle>>,
    query_child: Query<&Transform>,
    mut query: Query<(Entity, &YukkuriSprite, &crate::ai::BaseColliderRadius, Option<&mut Sprite>, Option<&crate::ai::Flight>), With<YukkuriShadow>>,
) {
    let Some(shadow_handle) = shadow_texture else { return; };
    
    for (entity, sprite, radius, maybe_sprite, maybe_flight) in query.iter_mut() {
        let mut total_offset = 0.0;
        if let Some(sprite_ent) = sprite.sprite_entity {
            if let Ok(trans) = query_child.get(sprite_ent) {
                total_offset = trans.translation.y;
            }
        }
        
        let max_alt = maybe_flight.map(|f| f.max_altitude).unwrap_or(200.0).max(1.0);
        let factor = (1.0 - (total_offset / max_alt)).clamp(0.2, 1.0);
        
        let base_width = radius.0 * 2.2;
        let base_height = radius.0 * 0.8;
        
        if let Some(mut sprite_comp) = maybe_sprite {
            sprite_comp.custom_size = Some(Vec2::new(base_width * factor, base_height * factor));
            sprite_comp.color = Color::srgba(0.0, 0.0, 0.0, 0.45 * factor);
        } else {
            commands.entity(entity).insert(Sprite {
                image: shadow_handle.0.clone(),
                custom_size: Some(Vec2::new(base_width * factor, base_height * factor)),
                color: Color::srgba(0.0, 0.0, 0.0, 0.45 * factor),
                ..default()
            });
        }
    }
}

pub fn update_squish_stretch_system(
    query_vel: Query<(Entity, &crate::simulation::kinematic_controller::KinematicVelocity, &YukkuriSprite)>,
    mut query_transform: Query<&mut Transform>,
) {
    for (entity, vel, sprite) in query_vel.iter() {
        let target_ent = sprite.sprite_entity.unwrap_or(entity);
        if let Ok(mut transform) = query_transform.get_mut(target_ent) {
            let speed = vel.current.length();
            let stretch = (speed / 150.0).clamp(0.0, 0.25);
            
            let target_scale_y = 1.0 + stretch;
            let target_scale_x = 1.0 - (stretch * 0.5);
            
            transform.scale.x += (target_scale_x - transform.scale.x) * 0.2;
            transform.scale.y += (target_scale_y - transform.scale.y) * 0.2;
        }
    }
}

pub struct YukkuriRenderPlugin;

impl Plugin for YukkuriRenderPlugin {
    fn build(&self, app: &mut App) {
        // If running in a headless test environment without DefaultPlugins/SpritePlugin/ImagePlugin,
        // we must register the Assets<TextureAtlasLayout> and Assets<Image> storages ourselves.
        // We check if the resource already exists to avoid resetting it (which would cause panics).
        if !app.world().contains_resource::<Assets<TextureAtlasLayout>>() {
            app.init_asset::<TextureAtlasLayout>();
        }
        if !app.world().contains_resource::<Assets<Image>>() {
            app.init_asset::<Image>();
        }

        app.init_resource::<YukkuriTypeRegistry>()
            .init_resource::<TextureAtlasRegistry>()
            .register_type::<YukkuriShadow>()
            // NOTE: TextureAtlasLayout and Image are already registered by
            // DefaultPlugins (via SpritePlugin). Calling init_asset again would
            // reset the Assets<T> storage and invalidate all layout handles
            // created during Startup, causing index-out-of-bounds panics.
            .add_message::<AnimationEvent>()
            .add_plugins(lighting::YukkuriLightingPlugin)
            .add_systems(Startup, setup_graphics_assets_system)
            .add_systems(Update, (
                update_animator_system,
                update_yukkuri_sprite_system,
                update_shadow_system,
                update_squish_stretch_system,
            ).chain().after(crate::ai::sync_yukkuri_animations));
    }
}
