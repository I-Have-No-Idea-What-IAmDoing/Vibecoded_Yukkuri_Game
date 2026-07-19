use serde::Deserialize;
use bevy::prelude::*;
use std::fs;
use crate::ai::{Needs, StableId, SteeringConfig, YukkuriStats, EmotionalState, AIState, Flight, VisibleTargets, Persistable, BaseColliderRadius, Personality, RelationshipRegistry, GossipQueue};

#[derive(Debug, Deserialize, Clone)]
pub struct PrefabHeader {
    pub type_id: String,
    pub name: String,
    pub growth_stage: String,
}

#[derive(Debug, Deserialize, Clone)]
pub struct PhysicsPrefab {
    pub radius: f32,
    pub mass: f32,
    pub friction: f32,
    pub restitution: f32,
}

#[derive(Debug, Deserialize, Clone)]
pub struct NeedsPrefab {
    pub max_health: f32,
    pub energy: f32,
    pub hunger: f32,
    pub max_stamina: f32,
}

#[derive(Debug, Deserialize, Clone)]
pub struct SteeringPrefab {
    pub max_speed: f32,
    pub max_force: f32,
    pub arrival_radius: f32,
    pub perception_radius: f32,
}

#[derive(Debug, Deserialize, Clone)]
pub struct YukkuriPrefab {
    pub prefab: PrefabHeader,
    pub physics: PhysicsPrefab,
    pub needs: NeedsPrefab,
    pub steering: SteeringPrefab,
}

/// Loads a yukkuri prefab from a TOML configuration file.
pub fn load_prefab(path: &str) -> Result<YukkuriPrefab, Box<dyn std::error::Error>> {
    let content = fs::read_to_string(path)?;
    let prefab: YukkuriPrefab = toml::from_str(&content)?;
    Ok(prefab)
}

use crate::render::{YukkuriSprite, YukkuriTypeRegistry, TextureAtlasRegistry, YukkuriShadow};

/// Spawns a Yukkuri Bevy entity using the loaded prefab configuration.
///
/// The spawned entity is immediately stamped with a [`StableId`] so that the
/// [`EntityRegistry`][crate::ai::EntityRegistry] can safely convert Python-
/// facing raw indices back to live Bevy [`Entity`] handles.
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

    let mut yukkuri_sprite = YukkuriSprite {
        image_name: image_name.clone(),
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
        sprite_entity: None,
    };

    let animator = crate::render::build_animator(
        type_id,
        asset_server,
        atlas_registry,
        type_registry,
    );

    // Resolve initial image handle and atlas layout
    let (image_handle, layout_handle) = if let Some(ref animator) = animator {
        let current_anim = animator.current_animation.to_lowercase();
        if let Some(def) = animator.animations.get(&current_anim) {
            (def.image_handle.clone(), Some(def.layout_handle.clone()))
        } else {
            let img_handle = atlas_registry.images.get(&image_name).cloned().unwrap_or_default();
            (img_handle, None)
        }
    } else {
        let img_handle = atlas_registry.images.get(&image_name).cloned().unwrap_or_default();
        let layout_handle = if frame_count > 1 {
            let key = (image_name.clone(), type_config.width, type_config.height);
            atlas_registry.layouts.get(&key).cloned()
        } else {
            None
        };
        (img_handle, layout_handle)
    };

    let texture_atlas = layout_handle.map(|layout| TextureAtlas {
        layout,
        index: 0,
    });

    let bevy_sprite = Sprite {
        image: image_handle,
        texture_atlas,
        flip_x: false,
        flip_y: false,
        color: Color::srgba(1.0, 1.0, 1.0, 1.0),
        ..default()
    };

    let sprite_entity = commands.spawn((
        bevy_sprite,
        Transform::from_xyz(0.0, 0.0, 0.1),
        GlobalTransform::default(),
        Visibility::default(),
    )).id();

    yukkuri_sprite.sprite_entity = Some(sprite_entity);

    let mut entity_builder = commands.spawn((
        Transform::from_xyz(position.x, position.y, 0.0)
            .with_scale(Vec3::splat(scale_factor)),
        GlobalTransform::default(),
        Visibility::default(),
        yukkuri_sprite,
        YukkuriShadow,
        avian2d::prelude::RigidBody::Kinematic,
        avian2d::prelude::Collider::circle(prefab.physics.radius),
        avian2d::prelude::Mass(prefab.physics.mass),
        avian2d::prelude::Friction::new(prefab.physics.friction),
        avian2d::prelude::Restitution::new(prefab.physics.restitution),
        avian2d::prelude::LinearVelocity::default(),
        avian2d::prelude::AngularVelocity::default(),
        avian2d::prelude::CustomPositionIntegration,
        crate::simulation::kinematic_controller::KinematicVelocity::default(),
        crate::simulation::kinematic_controller::KinematicSettings::default(),
    ));

    let parent_entity = entity_builder.id();

    let initial_age = match prefab.prefab.growth_stage.as_str() {
        "Baby" => 0.0,
        "Child" => 100.0,
        _ => 300.0,
    };

    entity_builder.insert((
        Needs {
            health: prefab.needs.max_health,
            hunger: prefab.needs.hunger,
            social: 50.0,
            energy: prefab.needs.energy,
            cleanliness: 100.0,
            bladder: 0.0,
            easiness: 50.0,
            max_health: prefab.needs.max_health,
        },
        YukkuriStats {
            name: prefab.prefab.name.clone(),
            type_id: prefab.prefab.type_id.clone(),
            growth_stage: prefab.prefab.growth_stage.clone(),
            age: initial_age,
            intelligence: 1.0,
            badges: 0,
            quality_score: 0.0,
            discipline: 0.0,
            agility: 1.0,
            tastebud_spoiled: 0.0,
        },
        BaseColliderRadius(prefab.physics.radius),
        EmotionalState {
            happiness: 0.0,
            stress: 0.0,
        },
        AIState::default(),
        if type_config.can_fly.unwrap_or(false) {
            Flight {
                flight_state: 0,
                altitude: 0.0,
                stamina: type_config.fly_stamina.unwrap_or(100.0),
                max_stamina: type_config.fly_stamina.unwrap_or(100.0),
                max_altitude: type_config.max_altitude.unwrap_or(100.0),
                ..default()
            }
        } else {
            Flight {
                flight_state: 0,
                altitude: 0.0,
                stamina: 0.0,
                max_stamina: 0.0,
                max_altitude: 0.0,
                ..default()
            }
        },
        VisibleTargets::default(),
    ));

    if let Some(anim) = animator {
        entity_builder.insert(anim);
    }

    // Now that entity_builder borrow is complete, we can use commands
    commands.entity(parent_entity).add_child(sprite_entity);
    commands.entity(parent_entity).insert(StableId::from_entity(parent_entity));

    commands.entity(parent_entity).insert(SteeringConfig {
        max_speed: prefab.steering.max_speed,
        max_force: prefab.steering.max_force,
        perception_radius: prefab.steering.perception_radius,
        arrival_radius: prefab.steering.arrival_radius,
    });

    commands.entity(parent_entity).insert((
        Persistable,
        Personality::default(),
        RelationshipRegistry::default(),
        GossipQueue::default(),
    ));

    commands.queue(move |world: &mut World| {
        let mut rng = rand::thread_rng();
        use rand::Rng;
        use rand_distr::{Normal, Distribution};
        
        let dist = Normal::new(0.0f32, 30.0).unwrap();
        
        let kindness = (dist.sample(&mut rng) as i32).clamp(-100, 100);
        let energy = (dist.sample(&mut rng) as i32).clamp(-100, 100);
        let bravery = (dist.sample(&mut rng) as i32).clamp(-100, 100);
        let greed = (dist.sample(&mut rng) as i32).clamp(-100, 100);
        
        let mut traits = std::collections::HashSet::new();
        if let Some(tr) = world.get_resource::<crate::simulation::skills::TraitRegistry>() {
            let keys: Vec<String> = tr.traits.keys().cloned().collect();
            if !keys.is_empty() {
                let rand_idx = rng.gen_range(0..keys.len());
                traits.insert(keys[rand_idx].clone());
            }
        }
        
        if let Some(mut pers) = world.get_mut::<Personality>(parent_entity) {
            pers.kindness = kindness;
            pers.energy = energy;
            pers.bravery = bravery;
            pers.greed = greed;
            pers.base_kindness = kindness;
            pers.base_energy = energy;
            pers.base_bravery = bravery;
            pers.base_greed = greed;
            pers.traits = traits;
        }
    });

    if type_config.is_predator.unwrap_or(false) {
        let prey_tags = type_config.prey_tags.clone()
            .unwrap_or_else(|| vec!["reimu".to_string(), "marisa".to_string()])
            .into_iter()
            .collect();
        let prey_sense_radius = type_config.prey_sense_radius.unwrap_or(300.0);
        let aggression = type_config.aggression.unwrap_or(1.0);
        let dps = type_config.dps.unwrap_or(20.0);

        commands.entity(parent_entity).insert(crate::ai::Predator {
            prey_tags,
            prey_sense_radius,
            hunger_threshold: 60.0,
            aggression,
            dps,
        });
    }


    parent_entity
}
