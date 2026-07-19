use bevy::prelude::*;
use avian2d::prelude::*;
use rand::Rng;
use crate::ai::{Needs, YukkuriStats, Dead, BaseColliderRadius, EmotionalState, AIState, StableId, RelationshipRegistry, Personality};
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
                    lifecycle_feedback_system,
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

pub fn lifecycle_tick_system(
    mut commands: Commands,
    time: Res<Time>,
    settings: Res<SimulationSettings>,
    time_elapsed: Res<crate::ai::persistence::TimeElapsed>,
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
    let game_dt = time.delta_secs() * time_elapsed.scale * time_elapsed.game_speed;
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
    mut query: Query<(
        Entity,
        &Transform,
        &mut Needs,
        &EmotionalState,
        &YukkuriStats,
        &StableId,
    ), Without<Dead>>,
) {
    if breeding_timer.duration() == Duration::ZERO {
        *breeding_timer = Timer::from_seconds(1.0, TimerMode::Repeating);
    }

    breeding_timer.tick(time.delta());
    if !breeding_timer.just_finished() {
        return;
    }

    let mut rng = rand::thread_rng();

    for (entity, transform, mut needs, emotional, stats, _stable_id) in query.iter_mut() {
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

                let baby_ent = spawn_yukkuri_prefab(
                    &mut commands,
                    &baby_prefab,
                    baby_pos,
                    &asset_server,
                    &atlas_registry,
                    &type_registry,
                );

                let parent_ent = entity;
                commands.queue(move |world: &mut World| {
                    let parent_stable_id;
                    let parent_family_id;
                    let parent_personality;
                    
                    if let Some(parent_ref) = world.get::<StableId>(parent_ent) {
                        parent_stable_id = parent_ref.0;
                    } else {
                        return;
                    }
                    
                    if let Some(parent_reg) = world.get::<RelationshipRegistry>(parent_ent) {
                        parent_family_id = parent_reg.family_group_id;
                    } else {
                        parent_family_id = None;
                    }
                    
                    if let Some(parent_pers) = world.get::<Personality>(parent_ent) {
                        parent_personality = Some(parent_pers.clone());
                    } else {
                        parent_personality = None;
                    }
                    
                    let child_stable_id;
                    if let Some(child_ref) = world.get::<StableId>(baby_ent) {
                        child_stable_id = child_ref.0;
                    } else {
                        return;
                    }
                    
                    let fam_id = parent_family_id.unwrap_or_else(|| rand::random::<u64>());
                    
                    // Link parent and child relationships
                    if let Some(mut p_reg) = world.get_mut::<RelationshipRegistry>(parent_ent) {
                        p_reg.biological_children.push(child_stable_id);
                        if p_reg.family_group_id.is_none() {
                            p_reg.family_group_id = Some(fam_id);
                        }
                    }
                    
                    if let Some(mut c_reg) = world.get_mut::<RelationshipRegistry>(baby_ent) {
                        c_reg.biological_parents.push(parent_stable_id);
                        c_reg.family_group_id = Some(fam_id);
                    }
                    
                    // Personality & Trait genetics inheritance
                    if let Some(parent_p) = parent_personality {
                        let mut local_rng = rand::thread_rng();
                        use rand::Rng;
                        
                        let kindness = (parent_p.kindness as f32 + local_rng.gen_range(-10.0..=10.0)).clamp(-100.0, 100.0) as i32;
                        let energy = (parent_p.energy as f32 + local_rng.gen_range(-10.0..=10.0)).clamp(-100.0, 100.0) as i32;
                        let bravery = (parent_p.bravery as f32 + local_rng.gen_range(-10.0..=10.0)).clamp(-100.0, 100.0) as i32;
                        let greed = (parent_p.greed as f32 + local_rng.gen_range(-10.0..=10.0)).clamp(-100.0, 100.0) as i32;
                        
                        let mut traits = std::collections::HashSet::new();
                        for t in &parent_p.traits {
                            if local_rng.gen_bool(0.5) {
                                traits.insert(t.clone());
                            }
                        }
                        
                        let t_registry = world.get_resource::<crate::simulation::skills::TraitRegistry>();
                        if let Some(tr) = t_registry {
                            if local_rng.gen_bool(0.1) || traits.is_empty() {
                                let keys: Vec<String> = tr.traits.keys().cloned().collect();
                                if !keys.is_empty() {
                                    let rand_idx = local_rng.gen_range(0..keys.len());
                                    traits.insert(keys[rand_idx].clone());
                                }
                            }
                        }
                        
                        if let Some(mut c_pers) = world.get_mut::<Personality>(baby_ent) {
                            c_pers.kindness = kindness;
                            c_pers.energy = energy;
                            c_pers.bravery = bravery;
                            c_pers.greed = greed;
                            c_pers.traits = traits;
                        }
                    }
                });

                info!("Adult {} bred a new baby!", stats.name);
            } else {
                warn!("Breeding failed: could not load prefab at {}", prefab_path);
            }
        }
    }
}

pub fn lifecycle_feedback_system(
    mut commands: Commands,
    mut grew_reader: MessageReader<EntityGrewMessage>,
    mut died_reader: MessageReader<EntityDiedMessage>,
    yukkuri_query: Query<(&Transform, &YukkuriStats)>,
) {
    for msg in grew_reader.read() {
        if let Ok((trans, stats)) = yukkuri_query.get(msg.entity) {
            info!("{} grew up to {}!", stats.name, msg.new_stage);
            commands.spawn((
                crate::simulation::needs::FloatingText {
                    velocity: Vec2::new(0.0, 40.0),
                    lifetime: 0.0,
                    max_lifetime: 2.0,
                },
                Text::new("Level Up!"),
                TextColor(Color::srgb(0.95, 0.95, 0.2)),
                TextFont {
                    font_size: FontSize::Px(22.0),
                    ..default()
                },
                Transform::from_translation(trans.translation + Vec3::new(0.0, 30.0, 1.5)),
            ));
        }
    }

    for msg in died_reader.read() {
        if let Ok((trans, stats)) = yukkuri_query.get(msg.entity) {
            info!("{} has died...", stats.name);
            commands.spawn((
                crate::simulation::needs::FloatingText {
                    velocity: Vec2::new(0.0, 20.0),
                    lifetime: 0.0,
                    max_lifetime: 2.0,
                },
                Text::new("Dead..."),
                TextColor(Color::srgb(0.6, 0.6, 0.6)),
                TextFont {
                    font_size: FontSize::Px(20.0),
                    ..default()
                },
                Transform::from_translation(trans.translation + Vec3::new(0.0, 30.0, 1.5)),
            ));
        }
    }
}
