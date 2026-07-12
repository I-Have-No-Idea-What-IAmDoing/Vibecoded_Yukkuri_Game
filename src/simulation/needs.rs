// INTEGRITY MANDATE:
// DO NOT CHEAT. All implementations must be genuine. Specifically:
// - DO NOT hardcode test results, expected outputs, or verification strings in source code.
// - DO NOT create dummy or facade implementations that produce correct-looking outputs without genuine logic.
// - DO NOT circumvent the intended task by delegating core work to external tools or pre-built solutions when the task requires building from scratch.
// - DO NOT fabricate verification outputs, logs, or attestation artifacts.
// - Every implementation must maintain real state and produce real behavior — not return hardcoded values.
// A Forensic Auditor will independently verify your work. Shortcut strategies WILL be detected and your work WILL be rejected.

use bevy::prelude::*;
use avian2d::prelude::*;
use rand::Rng;
use crate::ai::{Needs, Dead, EmotionalState};
use crate::audio::PlaySoundEvent;

/// Marker component for Poop entities.
#[derive(Component, Reflect, Debug, Default, Clone, PartialEq)]
#[reflect(Component, Default)]
pub struct Poop;

/// Message to clean poop in a radius around a position.
#[derive(Message, Debug, Clone)]
pub struct CleanPoopMessage {
    pub position: Vec2,
    pub radius: f32,
}

/// Resource containing default simulation values matching Python decay/poop rules.
#[derive(Resource, Debug, Clone, Reflect)]
#[reflect(Resource, Default)]
pub struct SimulationSettings {
    pub hunger_decay_rate: f32,
    pub energy_decay_rate: f32,
    pub cleanliness_decay_rate: f32,
    pub social_decay_rate: f32,
    pub starvation_damage_rate: f32,
    pub time_scale: f32,
    pub poop_spawn_chance: f32,
    pub bladder_full_threshold: f32,
    pub bladder_full_chance_mult: f32,
    pub cleanliness_critical_threshold: f32,
    pub cleanliness_critical_chance_mult: f32,
    pub spawn_cleanliness_penalty: f32,
    pub spawn_offset_range: f32,
    pub poop_smell_radius: f32,
    pub poop_smell_strength: f32,
    pub age_decay_rate: f32,
    pub baby_age_threshold: f32,
    pub child_age_threshold: f32,
    pub growth_health_restore: f32,
    pub child_max_health_bonus: f32,
    pub breeding_happiness_threshold: f32,
    pub breeding_energy_threshold: f32,
    pub breeding_cost: f32,
    pub breeding_chance: f32,
    pub baby_spawn_offset_range: f32,
    pub family_benefit_range: f32,
    pub family_happiness_gain: f32,
    pub family_stress_reduction: f32,
    pub family_food_sharing_threshold: f32,
    pub family_food_sharing_amount: f32,
    pub family_sleep_energy_gain: f32,
    pub family_sleep_stress_reduction: f32,
    pub stress_decay_rate: f32,
    pub happiness_decay_rate: f32,
    pub xp_base: f32,
    pub xp_exponent: f32,
}

impl Default for SimulationSettings {
    fn default() -> Self {
        Self {
            hunger_decay_rate: 2.0,
            energy_decay_rate: 0.5,
            cleanliness_decay_rate: 0.2,
            social_decay_rate: 0.5,
            starvation_damage_rate: 5.0,
            time_scale: 60.0,
            poop_spawn_chance: 0.01,
            bladder_full_threshold: 80.0,
            bladder_full_chance_mult: 10.0,
            cleanliness_critical_threshold: 10.0,
            cleanliness_critical_chance_mult: 5.0,
            spawn_cleanliness_penalty: 5.0,
            spawn_offset_range: 10.0,
            poop_smell_radius: 200.0,
            poop_smell_strength: 5.0,
            age_decay_rate: 1.0,
            baby_age_threshold: 100.0,
            child_age_threshold: 300.0,
            growth_health_restore: 50.0,
            child_max_health_bonus: 50.0,
            breeding_happiness_threshold: 80.0,
            breeding_energy_threshold: 80.0,
            breeding_cost: 50.0,
            breeding_chance: 0.001,
            baby_spawn_offset_range: 20.0,
            family_benefit_range: 150.0,
            family_happiness_gain: 0.5,
            family_stress_reduction: 0.5,
            family_food_sharing_threshold: 50.0,
            family_food_sharing_amount: 1.0,
            family_sleep_energy_gain: 0.5,
            family_sleep_stress_reduction: 1.0,
            stress_decay_rate: 5.0,
            happiness_decay_rate: 0.5,
            xp_base: 100.0,
            xp_exponent: 1.5,
        }
    }
}

/// Ticks hunger, energy, cleanliness, social using virtual time and applying time_scale.
/// Applies starvation damage when hunger reaches 100.0. Clamps values appropriately.
pub fn needs_decay_tick_system(
    time: Res<Time<Virtual>>,
    settings: Res<SimulationSettings>,
    trait_registry: Res<crate::simulation::skills::TraitRegistry>,
    mut query: Query<(&mut Needs, Option<&crate::ai::Personality>), Without<Dead>>,
) {
    let game_dt = time.delta_secs() * settings.time_scale;
    if game_dt <= 0.0 {
        return;
    }
    for (mut needs, maybe_personality) in query.iter_mut() {
        let mut hunger_mult = 1.0;
        let mut energy_mult = 1.0;
        let mut social_mult = 1.0;
        let mut cleanliness_mult = 1.0;

        if let Some(personality) = maybe_personality {
            for trait_id in &personality.traits {
                if let Some(t_data) = trait_registry.traits.get(trait_id) {
                    if let Some(ref stat_mods) = t_data.stat_modifiers {
                        hunger_mult *= stat_mods.get("hunger_decay").copied().unwrap_or(1.0);
                        energy_mult *= stat_mods.get("energy_decay").copied().unwrap_or(1.0);
                        social_mult *= stat_mods.get("social_decay").copied().unwrap_or(1.0);
                        cleanliness_mult *= stat_mods.get("cleanliness_decay").copied().unwrap_or(1.0);
                    }
                }
            }
        }

        needs.hunger = (needs.hunger + settings.hunger_decay_rate * hunger_mult * game_dt).clamp(0.0, 100.0);
        needs.energy = (needs.energy - settings.energy_decay_rate * energy_mult * game_dt).clamp(0.0, 100.0);
        needs.cleanliness = (needs.cleanliness - settings.cleanliness_decay_rate * cleanliness_mult * game_dt).clamp(0.0, 100.0);
        needs.social = (needs.social - settings.social_decay_rate * social_mult * game_dt).clamp(0.0, 100.0);

        if needs.hunger >= 100.0 {
            needs.health = (needs.health - settings.starvation_damage_rate * game_dt).clamp(0.0, needs.max_health);
        }
    }
}

/// Evaluates poop spawning chance-based checks (base chance, bladder full, cleanliness critical)
/// using real delta-time, spawns poop entities with coordinates offset by spawn_offset_range,
/// decreases cleanliness by penalty, and resets bladder to 0.0.
pub fn poop_spawning_system(
    mut commands: Commands,
    time: Res<Time<Virtual>>,
    settings: Res<SimulationSettings>,
    asset_server: Res<AssetServer>,
    mut query: Query<(&Transform, &mut Needs), Without<Dead>>,
) {
    let dt = time.delta_secs();
    if dt <= 0.0 {
        return;
    }
    let mut rng = rand::thread_rng();
    for (transform, mut needs) in query.iter_mut() {
        let mut should_poop = false;

        // Periodic/Random spawning logic
        if rng.gen::<f32>() < settings.poop_spawn_chance * dt {
            should_poop = true;
        }

        // Bladder Logic
        if needs.bladder > settings.bladder_full_threshold
            && rng.gen::<f32>() < (settings.poop_spawn_chance * settings.bladder_full_chance_mult) * dt
        {
            should_poop = true;
        }

        // Cleanliness low (lose control)
        if needs.cleanliness < settings.cleanliness_critical_threshold
            && rng.gen::<f32>() < (settings.poop_spawn_chance * settings.cleanliness_critical_chance_mult) * dt
        {
            should_poop = true;
        }

        if should_poop {
            let (offset_x, offset_y) = if settings.spawn_offset_range > 0.0 {
                (
                    rng.gen_range(-settings.spawn_offset_range..settings.spawn_offset_range),
                    rng.gen_range(-settings.spawn_offset_range..settings.spawn_offset_range),
                )
            } else {
                (0.0, 0.0)
            };
            let poop_pos = transform.translation.truncate() + Vec2::new(offset_x, offset_y);

            commands.spawn((
                Transform::from_xyz(poop_pos.x, poop_pos.y, 1.0),
                Visibility::default(),
                Sprite {
                    image: asset_server.load("images/poop.png"),
                    ..default()
                },
                RigidBody::Dynamic,
                Collider::circle(10.0),
                Mass(1.0),
                Friction::new(0.2),
                Restitution::new(0.2),
                Poop,
            ));

            needs.cleanliness = (needs.cleanliness - settings.spawn_cleanliness_penalty).clamp(0.0, 100.0);
            needs.bladder = 0.0;
        }
    }
}

/// Uses disjoint queries to prevent B0001 Panics.
/// Deducts cleanliness for nearby entities within smell radius by poop_smell_strength * dt.
pub fn poop_cleanliness_reduction_system(
    time: Res<Time<Virtual>>,
    settings: Res<SimulationSettings>,
    poop_query: Query<&Transform, (With<Poop>, Without<Needs>)>,
    mut yukkuri_query: Query<(&Transform, &mut Needs), (Without<Poop>, With<Needs>, Without<Dead>)>,
) {
    let dt = time.delta_secs();
    if dt <= 0.0 {
        return;
    }
    let smell_radius_sq = settings.poop_smell_radius * settings.poop_smell_radius;
    let reduction = settings.poop_smell_strength * dt;

    for poop_transform in poop_query.iter() {
        let poop_pos = poop_transform.translation.truncate();
        for (yukkuri_transform, mut needs) in yukkuri_query.iter_mut() {
            let yukkuri_pos = yukkuri_transform.translation.truncate();
            if poop_pos.distance_squared(yukkuri_pos) < smell_radius_sq {
                needs.cleanliness = (needs.cleanliness - reduction).clamp(0.0, 100.0);
            }
        }
    }
}

/// Listens to CleanPoopMessage and despawns all Poop entities within radius of position.
/// Writes a PlaySoundEvent event/message with name "click" if any poop was cleaned.
pub fn handle_clean_poop_message_system(
    mut commands: Commands,
    mut message_reader: MessageReader<CleanPoopMessage>,
    mut message_writer: MessageWriter<PlaySoundEvent>,
    poop_query: Query<(Entity, &Transform), With<Poop>>,
) {
    for msg in message_reader.read() {
        let mut cleaned_any = false;
        let radius_sq = msg.radius * msg.radius;
        for (entity, transform) in poop_query.iter() {
            let pos = transform.translation.truncate();
            if pos.distance_squared(msg.position) <= radius_sq {
                commands.entity(entity).despawn();
                cleaned_any = true;
            }
        }
        if cleaned_any {
            message_writer.write(PlaySoundEvent {
                name: "click".to_string(),
            });
        }
    }
}

/// Detects left mouse click while the C key is pressed, converts screen coords to world coords,
/// and despawns any Poop entity within 32.0 units, writing "click" PlaySoundEvent if cleaned.
pub fn clean_poop_on_click_system(
    mut commands: Commands,
    mouse_button_input: Res<ButtonInput<MouseButton>>,
    keyboard_input: Res<ButtonInput<KeyCode>>,
    window_query: Query<&Window>,
    camera_query: Query<(&Camera, &GlobalTransform), With<crate::camera::MainCamera>>,
    poop_query: Query<(Entity, &Transform), With<Poop>>,
    mut message_writer: MessageWriter<PlaySoundEvent>,
) {
    if !keyboard_input.pressed(KeyCode::KeyC) {
        return;
    }
    if !mouse_button_input.just_pressed(MouseButton::Left) {
        return;
    }

    let Some(window) = window_query.iter().next() else { return; };
    let Some((camera, camera_transform)) = camera_query.iter().next() else { return; };

    let Some(cursor_position) = window.cursor_position() else { return; };
    let Ok(world_pos) = camera.viewport_to_world_2d(camera_transform, cursor_position) else {
        return;
    };

    let mut cleaned_any = false;
    let radius_sq = 32.0 * 32.0;

    for (entity, transform) in poop_query.iter() {
        let pos = transform.translation.truncate();
        if pos.distance_squared(world_pos) <= radius_sq {
            commands.entity(entity).despawn();
            cleaned_any = true;
        }
    }

    if cleaned_any {
        message_writer.write(PlaySoundEvent {
            name: "click".to_string(),
        });
    }
}

/// Ticks emotional state stress and happiness decay over game time, modifying rates by traits.
/// Accumulates darkness stress if the entity is in darkness at night.
pub fn emotional_decay_tick_system(
    time: Res<Time<Virtual>>,
    settings: Res<SimulationSettings>,
    trait_registry: Res<crate::simulation::skills::TraitRegistry>,
    time_elapsed: Option<Res<crate::ai::persistence::TimeElapsed>>,
    query_lights: Query<(&GlobalTransform, &crate::render::lighting::LightSource)>,
    mut query: Query<(Entity, &GlobalTransform, &mut EmotionalState, Option<&crate::ai::Personality>), Without<Dead>>,
) {
    let game_dt = time.delta_secs() * settings.time_scale;
    if game_dt <= 0.0 {
        return;
    }

    let is_night = time_elapsed.as_ref().map(|te| te.is_night()).unwrap_or(false);

    for (_entity, g_trans, mut emotional_state, maybe_personality) in query.iter_mut() {
        let mut happiness_mult = 1.0;
        let mut stress_mult = 1.0;

        if let Some(personality) = maybe_personality {
            for trait_id in &personality.traits {
                if let Some(t_data) = trait_registry.traits.get(trait_id) {
                    if let Some(ref stat_mods) = t_data.stat_modifiers {
                        happiness_mult *= stat_mods.get("happiness_decay").copied().unwrap_or(1.0);
                        stress_mult *= stat_mods.get("stress_decay").copied().unwrap_or(1.0);
                    }
                }
            }
        }

        // Check if in light source range at night
        let mut in_light = false;
        if is_night {
            let entity_pos = g_trans.translation().xy();
            for (light_trans, light) in query_lights.iter() {
                if light.intensity > 0.0 {
                    let light_pos = light_trans.translation().xy();
                    let dist = entity_pos.distance(light_pos);
                    if dist <= light.radius {
                        in_light = true;
                        break;
                    }
                }
            }
        }

        // Stress Decay or Darkness Stress Accumulation
        if is_night && !in_light {
            let darkness_stress_rate = 5.0; // 5.0 per simulated second
            emotional_state.stress = (emotional_state.stress + darkness_stress_rate * game_dt).clamp(0.0, 100.0);
        } else if emotional_state.stress > 0.0 {
            emotional_state.stress = (emotional_state.stress - settings.stress_decay_rate * stress_mult * game_dt).clamp(0.0, 100.0);
        }

        // Happiness Decay (Return to Neutral 0.0)
        let baseline = 0.0;
        if emotional_state.happiness > baseline {
            emotional_state.happiness = (emotional_state.happiness - settings.happiness_decay_rate * happiness_mult * game_dt).clamp(baseline, 100.0);
        } else if emotional_state.happiness < baseline {
            emotional_state.happiness = (emotional_state.happiness + settings.happiness_decay_rate * happiness_mult * game_dt).clamp(-100.0, baseline);
        }
    }
}

/// Component for floating text indicators (upward movement and fade out).
#[derive(Component, Debug, Clone, Reflect)]
#[reflect(Component)]
pub struct FloatingText {
    pub velocity: Vec2,
    pub lifetime: f32,
    pub max_lifetime: f32,
}

impl Default for FloatingText {
    fn default() -> Self {
        Self {
            velocity: Vec2::new(0.0, 50.0),
            lifetime: 0.0,
            max_lifetime: 1.5,
        }
    }
}

/// System to update floating text transforms and text color alphas.
pub fn update_floating_text_system(
    time: Res<Time>,
    mut commands: Commands,
    mut query: Query<(Entity, &mut Transform, &mut TextColor, &mut FloatingText)>,
) {
    let dt = time.delta_secs();
    for (entity, mut transform, mut text_color, mut floating) in query.iter_mut() {
        floating.lifetime += dt;
        if floating.lifetime >= floating.max_lifetime {
            commands.entity(entity).despawn();
        } else {
            transform.translation += floating.velocity.extend(0.0) * dt;
            let alpha = (1.0 - (floating.lifetime / floating.max_lifetime)).clamp(0.0, 1.0);
            text_color.0 = text_color.0.with_alpha(alpha);
        }
    }
}

/// System to tick crying audio rolls for sad/unhappy yukkuri.
pub fn crying_feedback_system(
    time: Res<Time<Virtual>>,
    settings: Res<SimulationSettings>,
    mut message_writer: MessageWriter<PlaySoundEvent>,
    query: Query<(&Needs, &EmotionalState), Without<Dead>>,
) {
    let game_dt = time.delta_secs() * settings.time_scale;
    if game_dt <= 0.0 {
        return;
    }

    let mut rng = rand::thread_rng();
    for (_, emotional) in query.iter() {
        let rate = if emotional.happiness < -30.0 {
            0.10
        } else {
            0.01
        };

        if rng.gen::<f32>() < rate * game_dt {
            message_writer.write(PlaySoundEvent {
                name: "crying".to_string(),
            });
        }
    }
}

/// Bevy Plugin to register needs simulation resources, components, systems, and messages.
pub struct NeedsSimulationPlugin;

impl Plugin for NeedsSimulationPlugin {
    fn build(&self, app: &mut App) {
        app.register_type::<Poop>()
            .register_type::<FloatingText>()
            .init_resource::<SimulationSettings>()
            .register_type::<SimulationSettings>()
            .add_message::<CleanPoopMessage>()
            .add_systems(Update, (
                needs_decay_tick_system,
                emotional_decay_tick_system,
                poop_spawning_system,
                poop_cleanliness_reduction_system,
                handle_clean_poop_message_system,
                clean_poop_on_click_system,
                update_floating_text_system,
                crying_feedback_system,
            ));
    }
}
