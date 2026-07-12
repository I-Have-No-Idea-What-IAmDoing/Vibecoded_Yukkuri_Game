use bevy::prelude::*;
use avian2d::prelude::*;
use rand::Rng;
use crate::ai::{Needs, YukkuriStats, Dead, BaseColliderRadius, EmotionalState, AIState};
use crate::render::{YukkuriSprite, TextureAtlasRegistry, YukkuriTypeRegistry};
use crate::simulation::needs::SimulationSettings;
use crate::prefabs::{spawn_yukkuri_prefab, load_prefab};
use std::time::Duration;

/// Plugin that handles biological lifecycle, growth stage transitions, death, and breeding.
pub struct LifecycleSimulationPlugin;

impl Plugin for LifecycleSimulationPlugin {
    fn build(&self, app: &mut App) {
        app.add_message::<EntityGrewMessage>()
            .add_message::<EntityDiedMessage>()
            .add_systems(
                Update,
                (
                    lifecycle_tick_system,
                    death_system,
                    breeding_system,
                ),
            );
    }
}

/// Message emitted when a yukkuri grows to a new stage.
#[derive(Message, Debug, Clone)]
pub struct EntityGrewMessage {
    pub entity: Entity,
    pub new_stage: String,
}

/// Message emitted when a yukkuri dies.
#[derive(Message, Debug, Clone)]
pub struct EntityDiedMessage {
    pub entity: Entity,
}

/// System that increments yukkuri age and handles stage transitions (Baby -> Child -> Adult).
pub fn lifecycle_tick_system(
    mut commands: Commands,
    time: Res<Time<Virtual>>,
    settings: Res<SimulationSettings>,
    mut query: Query<
        (
            Entity,
            &mut Transform,
            &mut YukkuriStats,
            &mut Needs,
            &BaseColliderRadius,
        ),
        Without<Dead>,
    >,
    mut grew_writer: MessageWriter<EntityGrewMessage>,
) {
    let game_dt = time.delta_secs() * settings.time_scale;
    if game_dt <= 0.0 {
        return;
    }

    for (entity, mut transform, mut stats, mut needs, base_radius) in query.iter_mut() {
        stats.age += settings.age_decay_rate * game_dt;

        let mut transitioned = false;
        let mut new_stage = stats.growth_stage.clone();
        let mut scale_factor = 1.0;

        if stats.growth_stage == "Baby" && stats.age >= settings.baby_age_threshold {
            new_stage = "Child".to_string();
            scale_factor = 0.75;
            transitioned = true;

            // Apply child max health bonus and restore health
            needs.max_health += settings.child_max_health_bonus;
            needs.health = (needs.health + settings.growth_health_restore).clamp(0.0, needs.max_health);
        } else if stats.growth_stage == "Child" && stats.age >= settings.child_age_threshold {
            new_stage = "Adult".to_string();
            scale_factor = 1.0;
            transitioned = true;

            // Restore health on adult transition
            needs.health = (needs.health + settings.growth_health_restore).clamp(0.0, needs.max_health);
        }

        if transitioned {
            stats.growth_stage = new_stage.clone();
            transform.scale = Vec3::splat(scale_factor);
            // Re-insert collider with base radius (transform scale will scale it physically)
            commands.entity(entity).insert(Collider::circle(base_radius.0));

            grew_writer.write(EntityGrewMessage {
                entity,
                new_stage,
            });
        }
    }
}

/// System that monitors health and handles yukkuri death.
pub fn death_system(
    mut commands: Commands,
    query: Query<(Entity, &Needs, &YukkuriStats), Without<Dead>>,
    mut sprite_query: Query<(&mut Sprite, &mut YukkuriSprite)>,
    mut died_writer: MessageWriter<EntityDiedMessage>,
) {
    for (entity, needs, stats) in query.iter() {
        if needs.health <= 0.0 {
            commands.entity(entity).insert(Dead);
            commands.entity(entity).remove::<AIState>();

            // Flip sprite upside down
            if let Ok((mut sprite, mut yukkuri_sprite)) = sprite_query.get_mut(entity) {
                sprite.flip_y = true;
                yukkuri_sprite.flip_y = true;
            }

            info!("Yukkuri {} ({}) has died.", stats.name, stats.type_id);

            died_writer.write(EntityDiedMessage { entity });
        }
    }
}

/// System that handles asexual breeding for happy, energetic adults.
pub fn breeding_system(
    mut commands: Commands,
    time: Res<Time<Virtual>>,
    settings: Res<SimulationSettings>,
    asset_server: Res<AssetServer>,
    atlas_registry: Res<TextureAtlasRegistry>,
    type_registry: Res<YukkuriTypeRegistry>,
    mut breeding_timer: Local<Timer>,
    mut query: Query<(&Transform, &mut Needs, &EmotionalState, &YukkuriStats), Without<Dead>>,
) {
    if breeding_timer.duration() == Duration::ZERO {
        *breeding_timer = Timer::from_seconds(1.0, TimerMode::Repeating);
    }

    breeding_timer.tick(time.delta());
    if !breeding_timer.just_finished() {
        return;
    }

    let mut rng = rand::thread_rng();

    for (transform, mut needs, emotional, stats) in query.iter_mut() {
        if stats.growth_stage != "Adult" {
            continue;
        }

        if emotional.happiness >= settings.breeding_happiness_threshold
            && needs.energy >= settings.breeding_energy_threshold
            && rng.gen::<f32>() < settings.breeding_chance
        {
            // Deduct breeding cost
            needs.energy = (needs.energy - settings.breeding_cost).clamp(0.0, 100.0);

            // Spawn baby of same type_id nearby
            let prefab_path = format!("data/prefabs/{}.toml", stats.type_id);
            if let Ok(prefab) = load_prefab(&prefab_path) {
                let offset = if settings.baby_spawn_offset_range > 0.0 {
                    Vec2::new(
                        rng.gen_range(-settings.baby_spawn_offset_range..settings.baby_spawn_offset_range),
                        rng.gen_range(-settings.baby_spawn_offset_range..settings.baby_spawn_offset_range),
                    )
                } else {
                    Vec2::ZERO
                };
                let baby_pos = transform.translation.truncate() + offset;

                let mut baby_prefab = prefab.clone();
                baby_prefab.prefab.growth_stage = "Baby".to_string();

                spawn_yukkuri_prefab(
                    &mut commands,
                    &baby_prefab,
                    baby_pos,
                    &asset_server,
                    &atlas_registry,
                    &type_registry,
                );

                info!("Adult {} bred a new baby!", stats.name);
            } else {
                warn!("Breeding failed: could not load prefab at {}", prefab_path);
            }
        }
    }
}
