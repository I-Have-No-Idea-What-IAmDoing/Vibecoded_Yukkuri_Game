use bevy::prelude::*;
use bevy::time::TimeUpdateStrategy;
use std::time::Duration;
use std::sync::{Arc, Mutex};
use bevy::ecs::system::RunSystemOnce;
use vibecoded_yukkuri_game::ai::{
    Needs, YukkuriStats, BaseColliderRadius, Dead, EmotionalState, StableId, AIState,
    Personality, RelationshipRegistry, GossipQueue, SocialIdCounter, GossipPacket, RelationshipData,
    persistence::TimeElapsed, GossipEvent,
};
use vibecoded_yukkuri_game::audio::PlaySoundEvent;
use vibecoded_yukkuri_game::simulation::needs::{
    CleanPoopMessage, Poop, SimulationSettings,
};
use vibecoded_yukkuri_game::simulation::lifecycle::{EntityGrewMessage, EntityDiedMessage};
use vibecoded_yukkuri_game::simulation::SimulationPlugin;
use vibecoded_yukkuri_game::render::{YukkuriRenderPlugin, YukkuriSprite};

fn setup_test_app() -> App {
    let mut app = App::new();
    app.add_plugins(MinimalPlugins);
    app.add_plugins(bevy::diagnostic::DiagnosticsPlugin);
    app.add_plugins(AssetPlugin::default());
    app.init_asset::<Image>();

    app.init_resource::<ButtonInput<KeyCode>>();
    app.init_resource::<ButtonInput<MouseButton>>();

    // Register components for reflection
    app.register_type::<Needs>()
        .register_type::<YukkuriStats>()
        .register_type::<BaseColliderRadius>()
        .register_type::<Dead>()
        .register_type::<EmotionalState>()
        .register_type::<StableId>()
        .register_type::<Personality>()
        .register_type::<RelationshipRegistry>()
        .register_type::<GossipQueue>()
        .register_type::<TimeElapsed>()
        .init_resource::<SocialIdCounter>();

    // Add our simulation and rendering plugins
    app.add_plugins(SimulationPlugin);
    app.add_plugins(avian2d::PhysicsPlugins::default());
    app.init_resource::<avian2d::collider_tree::ColliderTreeDiagnostics>();
    app.init_resource::<avian2d::spatial_query::SpatialQueryDiagnostics>();
    app.init_resource::<avian2d::dynamics::solver::SolverDiagnostics>();
    app.init_resource::<avian2d::collision::CollisionDiagnostics>();
    app.add_plugins(YukkuriRenderPlugin);

    // Register messages
    app.add_message::<PlaySoundEvent>()
        .add_message::<GossipEvent>();

    // Configure virtual time max_delta to allow large jumps in headless tests
    app.world_mut()
        .resource_mut::<Time<Virtual>>()
        .set_max_delta(Duration::from_secs(10));

    app
}

#[test]
fn test_needs_decay_and_starvation() {
    let mut app = setup_test_app();

    // Spawn a Yukkuri with custom needs
    let entity = app
        .world_mut()
        .spawn((
            Transform::default(),
            Needs {
                health: 100.0,
                hunger: 0.0,
                energy: 100.0,
                cleanliness: 100.0,
                social: 100.0,
                max_health: 100.0,
                ..default()
            },
        ))
        .id();

    // First update to initialize time and run startup systems
    app.update();

    // Advance time by 0.1 real seconds, which corresponds to 6.0 game seconds (time_scale = 60.0)
    app.insert_resource(TimeUpdateStrategy::ManualDuration(Duration::from_secs_f32(0.1)));
    app.update();

    let world = app.world();
    let needs = world.get::<Needs>(entity).unwrap();

    // Verify decay/increases:
    // hunger = 0.0 + 2.0 * 6.0 = 12.0
    // energy = 100.0 - 0.5 * 6.0 = 97.0
    // cleanliness = 100.0 - 0.2 * 6.0 = 98.8
    // social = 100.0 - 0.5 * 6.0 = 97.0
    // health should remain 100.0 since hunger is not 100.0
    assert!((needs.hunger - 12.0).abs() < 1e-4, "expected hunger 12.0, got {}", needs.hunger);
    assert!((needs.energy - 97.0).abs() < 1e-4, "expected energy 97.0, got {}", needs.energy);
    assert!((needs.cleanliness - 98.8).abs() < 1e-4, "expected cleanliness 98.8, got {}", needs.cleanliness);
    assert!((needs.social - 97.0).abs() < 1e-4, "expected social 97.0, got {}", needs.social);
    assert_eq!(needs.health, 100.0);

    // Now test starvation damage by forcing hunger to 100.0
    app.world_mut().entity_mut(entity).get_mut::<Needs>().unwrap().hunger = 100.0;

    // Tick again by 0.1 real seconds (6.0 game seconds)
    app.update();

    let needs = app.world().get::<Needs>(entity).unwrap();
    // health = 100.0 - 5.0 * 6.0 = 70.0
    assert!((needs.health - 70.0).abs() < 1e-4, "expected health 70.0, got {}", needs.health);
}

#[test]
fn test_poop_spawning_on_bladder_full() {
    let mut app = setup_test_app();

    // Set settings so poop spawning is guaranteed when bladder is full
    let mut settings = app.world().resource::<SimulationSettings>().clone();
    settings.cleanliness_decay_rate = 0.0;
    settings.poop_spawn_chance = 10.0;
    settings.bladder_full_chance_mult = 10.0;
    settings.spawn_offset_range = 0.0; // spawn exactly at entity location
    app.insert_resource(settings);

    // Spawn a Yukkuri with bladder full (> 80.0)
    let entity = app
        .world_mut()
        .spawn((
            Transform::from_xyz(42.0, 24.0, 0.0),
            Needs {
                bladder: 90.0,
                cleanliness: 100.0,
                ..default()
            },
        ))
        .id();

    // Set manual time update strategy before first update to initialize virtual time correctly
    app.insert_resource(TimeUpdateStrategy::ManualDuration(Duration::from_secs_f32(1.0)));
    app.update(); // initializes time
    app.update(); // ticks virtual time

    let world = app.world_mut();
    let needs = world.get::<Needs>(entity).unwrap();

    // Bladder should be reset to 0.0
    assert_eq!(needs.bladder, 0.0);
    // Cleanliness should have penalty applied (100.0 - 5.0 = 95.0)
    assert_eq!(needs.cleanliness, 95.0);

    // Verify poop entity spawned at (42.0, 24.0, 1.0)
    let mut poop_query = world.query_filtered::<(&Transform, &Poop), With<Poop>>();
    let mut poop_iter = poop_query.iter(world);
    let (poop_transform, _) = poop_iter.next().expect("Poop entity should have spawned");
    assert_eq!(poop_transform.translation.x, 42.0);
    assert_eq!(poop_transform.translation.y, 24.0);
    assert_eq!(poop_transform.translation.z, 1.0);
    assert!(poop_iter.next().is_none());
}

#[test]
fn test_cleanliness_reduction_near_poop() {
    let mut app = setup_test_app();

    // Disable normal cleanliness decay to only measure poop smell effect
    let mut settings = app.world().resource::<SimulationSettings>().clone();
    settings.cleanliness_decay_rate = 0.0;
    settings.poop_smell_radius = 200.0;
    settings.poop_smell_strength = 5.0;
    app.insert_resource(settings);

    // Spawn a poop at (0.0, 0.0)
    app.world_mut().spawn((
        Transform::from_xyz(0.0, 0.0, 1.0),
        Poop,
    ));

    // Spawn Yukkuri 1: near the poop (50.0, 0.0), within 200.0 radius
    let yukkuri_near = app
        .world_mut()
        .spawn((
            Transform::from_xyz(50.0, 0.0, 0.0),
            Needs {
                cleanliness: 100.0,
                ..default()
            },
        ))
        .id();

    // Spawn Yukkuri 2: far from the poop (300.0, 0.0), outside 200.0 radius
    let yukkuri_far = app
        .world_mut()
        .spawn((
            Transform::from_xyz(300.0, 0.0, 0.0),
            Needs {
                cleanliness: 100.0,
                ..default()
            },
        ))
        .id();

    // Set manual time update strategy before first update to initialize virtual time correctly
    app.insert_resource(TimeUpdateStrategy::ManualDuration(Duration::from_secs_f32(0.1)));
    app.update(); // initializes time
    app.update(); // ticks virtual time

    let world = app.world();
    let needs_near = world.get::<Needs>(yukkuri_near).unwrap();
    let needs_far = world.get::<Needs>(yukkuri_far).unwrap();

    // Near Yukkuri should have cleanliness reduced by poop_smell_strength * 0.1 = 0.5 (so 99.5)
    assert_eq!(needs_near.cleanliness, 99.5);
    // Far Yukkuri cleanliness should remain 100.0
    assert_eq!(needs_far.cleanliness, 100.0);
}

#[test]
fn test_clean_poop_message() {
    let mut app = setup_test_app();

    // Spawn three poops
    let poop1 = app.world_mut().spawn((
        Transform::from_xyz(0.0, 0.0, 1.0),
        Poop,
    )).id();

    let poop2 = app.world_mut().spawn((
        Transform::from_xyz(10.0, 10.0, 1.0),
        Poop,
    )).id();

    let poop3 = app.world_mut().spawn((
        Transform::from_xyz(100.0, 100.0, 1.0),
        Poop,
    )).id();

    // Send CleanPoopMessage at (0.0, 0.0) with radius 30.0 using a one-off system
    let _ = app.world_mut().run_system_once(|mut writer: MessageWriter<CleanPoopMessage>| {
        writer.write(CleanPoopMessage {
            position: Vec2::new(0.0, 0.0),
            radius: 30.0,
        });
    });

    app.update();

    let world = app.world_mut();

    // Check which poops still exist (get_entity returns Result, so is_err() means despawned)
    assert!(world.get_entity(poop1).is_err(), "poop1 should be cleaned");
    assert!(world.get_entity(poop2).is_err(), "poop2 should be cleaned");
    assert!(world.get_entity(poop3).is_ok(), "poop3 should NOT be cleaned");

    // Verify PlaySoundEvent was written using a one-off system
    let sound_events = Arc::new(Mutex::new(Vec::new()));
    let sound_events_clone = sound_events.clone();
    let _ = world.run_system_once(move |mut reader: MessageReader<PlaySoundEvent>| {
        for event in reader.read() {
            sound_events_clone.lock().unwrap().push(event.clone());
        }
    });

    let events = sound_events.lock().unwrap();
    assert_eq!(events.len(), 1, "Should have received exactly 1 sound event");
    assert_eq!(events[0].name, "click");
}

#[test]
fn test_baby_to_child_transition() {
    let mut app = setup_test_app();
    app.insert_resource(TimeUpdateStrategy::ManualDuration(Duration::from_secs_f32(2.0)));

    // Override settings to disable need decay to prevent starvation death during time steps
    let mut settings = app.world().resource::<SimulationSettings>().clone();
    settings.hunger_decay_rate = 0.0;
    settings.starvation_damage_rate = 0.0;
    app.insert_resource(settings);

    let entity = app
        .world_mut()
        .spawn((
            Transform::from_scale(Vec3::splat(0.5)),
            Needs {
                health: 100.0,
                max_health: 100.0,
                ..default()
            },
            YukkuriStats {
                growth_stage: "Baby".to_string(),
                age: 0.0,
                ..default()
            },
            BaseColliderRadius(16.0),
        )
    ).id();

    // First update initializes time and runs startup systems (delta is 0)
    app.update();
    // Second update ticks time by 2.0s (120.0s game time)
    app.update();

    let world = app.world();
    let stats = world.get::<YukkuriStats>(entity).unwrap();
    let needs = world.get::<Needs>(entity).unwrap();
    let transform = world.get::<Transform>(entity).unwrap();

    assert_eq!(stats.growth_stage, "Child");
    assert_eq!(stats.age, 120.0);
    // scale should grow from 0.5 to 0.75
    assert_eq!(transform.scale.x, 0.75);
    // max_health should have child_max_health_bonus (+50.0) applied
    assert_eq!(needs.max_health, 150.0);
    // health should have growth_health_restore (+50.0) applied and clamped to max_health
    assert_eq!(needs.health, 150.0);

    // Verify EntityGrewMessage was written
    let grew_events = Arc::new(Mutex::new(Vec::new()));
    let grew_events_clone = grew_events.clone();
    let _ = app.world_mut().run_system_once(move |mut reader: MessageReader<EntityGrewMessage>| {
        for event in reader.read() {
            grew_events_clone.lock().unwrap().push(event.clone());
        }
    });
    assert_eq!(grew_events.lock().unwrap().len(), 1);
}

#[test]
fn test_child_to_adult_transition() {
    let mut app = setup_test_app();
    app.insert_resource(TimeUpdateStrategy::ManualDuration(Duration::from_secs_f32(4.0)));

    // Override settings to disable need decay to prevent starvation death during time steps
    let mut settings = app.world().resource::<SimulationSettings>().clone();
    settings.hunger_decay_rate = 0.0;
    settings.starvation_damage_rate = 0.0;
    app.insert_resource(settings);

    let entity = app
        .world_mut()
        .spawn((
            Transform::from_scale(Vec3::splat(0.75)),
            Needs {
                health: 100.0,
                max_health: 150.0,
                ..default()
            },
            YukkuriStats {
                growth_stage: "Child".to_string(),
                age: 100.0, // starts at Child threshold
                ..default()
            },
            BaseColliderRadius(16.0),
        )
    ).id();

    // First update initializes time
    app.update();
    // Second update ticks time by 4.0s (240.0s game time, total age 340.0)
    app.update();

    let world = app.world();
    let stats = world.get::<YukkuriStats>(entity).unwrap();
    let needs = world.get::<Needs>(entity).unwrap();
    let transform = world.get::<Transform>(entity).unwrap();

    assert_eq!(stats.growth_stage, "Adult");
    assert_eq!(stats.age, 340.0);
    // scale should grow to 1.0
    assert_eq!(transform.scale.x, 1.0);
    // max_health should stay at 150.0 (no bonus for Adult transition)
    assert_eq!(needs.max_health, 150.0);
    // health should have +50.0 restore clamped to max_health
    assert_eq!(needs.health, 150.0);
}

#[test]
fn test_death_on_zero_health() {
    let mut app = setup_test_app();

    let entity = app
        .world_mut()
        .spawn((
            Transform::default(),
            Needs {
                health: 0.0, // dead immediately
                max_health: 100.0,
                ..default()
            },
            YukkuriStats {
                growth_stage: "Adult".to_string(),
                ..default()
            },
            AIState::default(),
            YukkuriSprite {
                image_name: "reimu.png".to_string(),
                width: 32,
                height: 32,
                layer: 2,
                flip_x: false,
                flip_y: false,
                alpha: 255,
                frame_count: 1,
                frame_duration: 0.1,
                current_frame: 0,
                timer: 0.0,
                loop_anim: false,
                is_animating: false,
                sprite_entity: None,
            },
            Sprite::default(),
        )
    ).id();

    app.update();

    let world = app.world();
    assert!(world.get::<Dead>(entity).is_some());
    assert!(world.get::<AIState>(entity).is_none());

    let sprite = world.get::<Sprite>(entity).unwrap();
    let yukkuri_sprite = world.get::<YukkuriSprite>(entity).unwrap();
    assert!(sprite.flip_y);
    assert!(yukkuri_sprite.flip_y);

    // Verify EntityDiedMessage was written
    let died_events = Arc::new(Mutex::new(Vec::new()));
    let died_events_clone = died_events.clone();
    let _ = app.world_mut().run_system_once(move |mut reader: MessageReader<EntityDiedMessage>| {
        for event in reader.read() {
            died_events_clone.lock().unwrap().push(event.clone());
        }
    });
    assert_eq!(died_events.lock().unwrap().len(), 1);
}

#[test]
fn test_breeding_spawns_baby() {
    let mut app = setup_test_app();
    app.insert_resource(TimeUpdateStrategy::ManualDuration(Duration::from_secs_f32(1.0)));

    // Override settings before first update: always breed, no offset, disable decay
    let mut settings = app.world().resource::<SimulationSettings>().clone();
    settings.breeding_chance = 1.0;
    settings.baby_spawn_offset_range = 0.0;
    settings.energy_decay_rate = 0.0;
    settings.happiness_decay_rate = 0.0;
    // Ensure thresholds are well below what we'll set on the entity
    settings.breeding_happiness_threshold = 50.0;
    settings.breeding_energy_threshold = 50.0;
    app.insert_resource(settings);

    // Spawn parent entity BEFORE the first update so it exists when the
    // Local<Timer> initialises and fires for the first time.
    let parent_entity = app
        .world_mut()
        .spawn((
            Transform::from_xyz(100.0, 100.0, 0.0),
            Needs {
                health: 100.0,
                max_health: 100.0,
                energy: 100.0,
                ..default()
            },
            YukkuriStats {
                name: "ParentReimu".to_string(),
                type_id: "reimu".to_string(),
                growth_stage: "Adult".to_string(),
                age: 300.0,
                ..default()
            },
            EmotionalState {
                happiness: 100.0,
                stress: 0.0,
            },
            BaseColliderRadius(16.0),
            StableId(12345),
            RelationshipRegistry::default(),
            Personality {
                kindness: 80,
                energy: 70,
                bravery: 60,
                greed: 50,
                base_kindness: 80,
                base_energy: 70,
                base_bravery: 60,
                base_greed: 50,
                traits: {
                    let mut s = std::collections::HashSet::new();
                    s.insert("Stubborn".to_string());
                    s
                },
            },
        ))
        .id();

    // Run up to 20 updates (20 virtual seconds) — the 1-second repeating timer
    // must fire at least once, deducting energy on the very first frame.
    for i in 0..20 {
        app.update();
        let energy = app.world().get::<Needs>(parent_entity).unwrap().energy;
        if energy < 100.0 {
            println!("Breeding triggered on update {i}: energy={energy}");
            break;
        }
    }

    let world = app.world_mut();

    // Parent energy should have decreased by breeding_cost (50.0)
    let parent_needs = world.get::<Needs>(parent_entity).unwrap();
    assert_eq!(parent_needs.energy, 50.0, "Energy was not deducted; breeding did not fire");

    // Verify a baby reimu was spawned
    let mut baby_query = world.query_filtered::<(Entity, &Transform, &YukkuriStats, &StableId, &RelationshipRegistry, &Personality), Without<Dead>>();
    let mut babies = Vec::new();
    for (entity, transform, stats, stable_id, rel_reg, personality) in baby_query.iter(world) {
        if stats.growth_stage == "Baby" {
            babies.push((entity, transform.translation, stats.clone(), stable_id.clone(), rel_reg.clone(), personality.clone()));
        }
    }

    assert_eq!(babies.len(), 1, "Exactly one baby should have spawned");
    let (baby_ent, baby_pos, baby_stats, baby_stable, baby_rel, baby_pers) = &babies[0];
    assert!((baby_pos.x - 100.0).abs() < 1.0, "Baby x position wrong: {}", baby_pos.x);
    assert!((baby_pos.y - 100.0).abs() < 1.0, "Baby y position wrong: {}", baby_pos.y);
    assert_eq!(baby_stats.growth_stage, "Baby");
    // Age starts at 0 but one lifecycle tick (time_scale=60 × dt=1.0s = 60) may
    // have already run.  Verify the baby is still well within the Baby stage.
    assert!(
        baby_stats.age < 100.0,
        "Baby age ({}) should be below baby_age_threshold (100)",
        baby_stats.age
    );

    // Verify parent-child lineage
    let parent_reg = world.get::<RelationshipRegistry>(parent_entity).unwrap();
    assert!(parent_reg.biological_children.contains(&baby_stable.0), "Parent must list baby in biological children");
    assert!(baby_rel.biological_parents.contains(&12345), "Baby must list parent stable ID 12345 in biological parents");
    assert!(parent_reg.family_group_id.is_some(), "Parent should have assigned a family group ID");
    assert_eq!(parent_reg.family_group_id, baby_rel.family_group_id, "Family group IDs must match");

    // Verify personality inheritance
    assert!((baby_pers.kindness - 80).abs() <= 10, "Baby kindness ({}) should be close to parent's (80)", baby_pers.kindness);
    assert!((baby_pers.energy - 70).abs() <= 10, "Baby energy ({}) should be close to parent's (70)", baby_pers.energy);
    assert!((baby_pers.bravery - 60).abs() <= 10, "Baby bravery ({}) should be close to parent's (60)", baby_pers.bravery);
    assert!((baby_pers.greed - 50).abs() <= 10, "Baby greed ({}) should be close to parent's (50)", baby_pers.greed);
}

#[test]
fn test_family_proximity_benefits() {
    let mut app = setup_test_app();
    app.insert_resource(TimeUpdateStrategy::ManualDuration(Duration::from_secs_f32(1.0)));

    let mut settings = app.world().resource::<SimulationSettings>().clone();
    settings.family_benefit_range = 150.0;
    settings.family_happiness_gain = 1.0;
    settings.family_stress_reduction = 1.0;
    settings.family_sleep_energy_gain = 5.0;
    settings.family_sleep_stress_reduction = 5.0;
    settings.family_food_sharing_threshold = 50.0;
    settings.family_food_sharing_amount = 10.0;
    settings.energy_decay_rate = 0.0;
    settings.hunger_decay_rate = 0.0;
    settings.cleanliness_decay_rate = 0.0;
    settings.social_decay_rate = 0.0;
    settings.happiness_decay_rate = 0.0;
    settings.stress_decay_rate = 0.0;
    app.insert_resource(settings);

    // Spawn A (Family Group 1)
    let entity_a = app.world_mut().spawn((
        Transform::from_xyz(0.0, 0.0, 0.0),
        Needs {
            hunger: 10.0,
            energy: 50.0,
            ..default()
        },
        EmotionalState {
            happiness: 50.0,
            stress: 50.0,
        },
        RelationshipRegistry {
            family_group_id: Some(1),
            ..default()
        },
        AIState {
            current_action: "Sleep".to_string(),
            ..default()
        },
    )).id();

    // Spawn B (Family Group 1)
    let entity_b = app.world_mut().spawn((
        Transform::from_xyz(50.0, 0.0, 0.0), // distance = 50.0, within benefit range
        Needs {
            hunger: 60.0, // Above sharing threshold
            energy: 50.0,
            ..default()
        },
        EmotionalState {
            happiness: 50.0,
            stress: 50.0,
        },
        RelationshipRegistry {
            family_group_id: Some(1),
            ..default()
        },
        AIState {
            current_action: "Eat".to_string(),
            ..default()
        },
    )).id();

    app.update();

    // Trigger proximity benefits by advancing time by 2.1s (timer is 2.0s)
    app.insert_resource(TimeUpdateStrategy::ManualDuration(Duration::from_secs_f32(2.1)));
    app.update();

    let world = app.world();
    let a_emotion = world.get::<EmotionalState>(entity_a).unwrap();
    let b_emotion = world.get::<EmotionalState>(entity_b).unwrap();
    let b_needs = world.get::<Needs>(entity_b).unwrap();

    // Togetherness:
    // A happiness = 50.0 + 1.0 = 51.0
    // A stress = 50.0 - 1.0 = 49.0
    // B happiness = 50.0 + 1.0 = 51.0
    // B stress = 50.0 - 1.0 = 49.0
    
    // Nest sharing: A is sleeping, so B energy + 5.0 = 55.0, B stress - 5.0 = 44.0
    assert!(a_emotion.happiness > 50.0);
    assert!(a_emotion.stress < 50.0);
    assert!(b_emotion.happiness > 50.0);
    assert!(b_emotion.stress < 45.0);
    assert!(b_needs.energy > 50.0);
}

#[test]
fn test_relationship_decay() {
    let mut app = setup_test_app();
    
    app.world_mut().insert_resource(TimeElapsed { elapsed: 1000.0, ..Default::default() });
    
    // Spawn entity A
    let entity_a = app.world_mut().spawn((
        StableId(1),
        RelationshipRegistry {
            relationships: {
                let mut map = std::collections::HashMap::new();
                // 1. Should decay (last update at 300.0s, now 1000.0s, delta 700s > 600s)
                let mut rel1 = RelationshipData::new(300.0);
                rel1.last_update = 300.0;
                map.insert(2, rel1);
                
                // 2. Exempt: parent (last update at 300.0s)
                let mut rel2 = RelationshipData::new(300.0);
                rel2.last_update = 300.0;
                map.insert(3, rel2);
                
                map
            },
            biological_parents: vec![3].into_iter().collect(),
            ..default()
        },
    )).id();

    // Spawn entity B (stable_id 2)
    app.world_mut().spawn((
        StableId(2),
        RelationshipRegistry::default(),
    ));

    // Spawn parent entity C (stable_id 3)
    app.world_mut().spawn((
        StableId(3),
        RelationshipRegistry::default(),
    ));

    app.update();

    let world = app.world();
    let reg = world.get::<RelationshipRegistry>(entity_a).unwrap();
    
    // Relationship 2 should be decayed and removed.
    // Relationship 3 (parent) should be preserved.
    assert!(!reg.relationships.contains_key(&2));
    assert!(reg.relationships.contains_key(&3));
}

#[test]
fn test_gossip_witness_and_direct_exchange() {
    let mut app = setup_test_app();
    app.world_mut().insert_resource(TimeElapsed { elapsed: 100.0, ..Default::default() });

    // Spawn initiator A
    let entity_a = app.world_mut().spawn((
        Transform::from_xyz(0.0, 0.0, 0.0),
        StableId(1),
        GossipQueue::default(),
        RelationshipRegistry {
            family_group_id: Some(10),
            ..default()
        },
        YukkuriStats::default(),
    )).id();

    // Spawn target B
    let entity_b = app.world_mut().spawn((
        Transform::from_xyz(10.0, 0.0, 0.0),
        StableId(2),
        GossipQueue::default(),
        RelationshipRegistry {
            family_group_id: Some(10),
            ..default()
        },
        YukkuriStats::default(),
    )).id();

    // Spawn witness C (in range, same family group)
    let entity_c = app.world_mut().spawn((
        Transform::from_xyz(100.0, 0.0, 0.0), // distance = 100.0 < 300.0
        StableId(3),
        GossipQueue::default(),
        RelationshipRegistry {
            family_group_id: Some(10),
            ..default()
        },
        YukkuriStats::default(),
    )).id();

    // Spawn witness D (too far)
    let entity_d = app.world_mut().spawn((
        Transform::from_xyz(400.0, 0.0, 0.0), // distance = 400.0 > 300.0
        StableId(4),
        GossipQueue::default(),
        RelationshipRegistry::default(),
        YukkuriStats::default(),
    )).id();

    app.update();

    // Write a GossipEvent
    use vibecoded_yukkuri_game::ai::GossipEvent;
    let _ = app.world_mut().run_system_once(move |mut writer: MessageWriter<GossipEvent>| {
        writer.write(GossipEvent {
            initiator_entity: entity_a,
            target_entity: entity_b,
            initiator_stable_id: 1,
            target_stable_id: 2,
            position: Vec2::new(0.0, 0.0),
            range_type: "visual".to_string(),
            event_type: "Dance".to_string(),
        });
    });

    app.update();

    let world = app.world();
    let gossip_c = world.get::<GossipQueue>(entity_c).unwrap();
    let gossip_d = world.get::<GossipQueue>(entity_d).unwrap();

    // Witness C should have received a GossipPacket about target B
    assert_eq!(gossip_c.priority_queue.len(), 1);
    let packet = &gossip_c.priority_queue[0];
    assert_eq!(packet.target_id, 2);
    assert_eq!(packet.event_type, "Dance");
    assert_eq!(packet.value, 15.0); // 10.0 + 5.0 interest group bonus

    // Witness D is too far, should have 0 packets
    assert_eq!(gossip_d.priority_queue.len(), 0);

    // Direct exchange test:
    // Let's add a packet to D's queue about target 5, and trigger direct talk with C
    app.world_mut().entity_mut(entity_d).get_mut::<GossipQueue>().unwrap().add_packet(GossipPacket {
        target_id: 5,
        event_type: "Talk".to_string(),
        value: 20.0,
        timestamp: 100.0,
    });
    
    // Set position of D close to C to Talk
    app.world_mut().entity_mut(entity_d).get_mut::<Transform>().unwrap().translation = Vec3::new(105.0, 0.0, 0.0);

    let _ = app.world_mut().run_system_once(move |mut writer: MessageWriter<GossipEvent>| {
        writer.write(GossipEvent {
            initiator_entity: entity_c,
            target_entity: entity_d,
            initiator_stable_id: 3,
            target_stable_id: 4,
            position: Vec2::new(100.0, 0.0),
            range_type: "visual".to_string(),
            event_type: "Talk".to_string(),
        });
    });

    app.update();

    let world = app.world();
    let gossip_c_after = world.get::<GossipQueue>(entity_c).unwrap();
    
    // C should now have the packet about target 5 shared by D (value decayed: 20.0 * 0.9 = 18.0)
    let found = gossip_c_after.priority_queue.iter().any(|p| p.target_id == 5 && p.value == 18.0);
    assert!(found, "Shared gossip should be present in C's queue");
}

#[test]
fn test_trait_decay_modifiers() {
    let mut app = setup_test_app();

    // Spawns a Yukkuri with GLUTTON and LONER traits
    let mut traits = std::collections::HashSet::new();
    traits.insert("GLUTTON".to_string());
    traits.insert("LONER".to_string());

    let entity = app
        .world_mut()
        .spawn((
            Transform::default(),
            Needs {
                health: 100.0,
                hunger: 0.0,
                energy: 100.0,
                cleanliness: 100.0,
                social: 100.0,
                max_health: 100.0,
                ..default()
            },
            Personality {
                kindness: 0,
                energy: 0,
                bravery: 0,
                greed: 0,
                base_kindness: 0,
                base_energy: 0,
                base_bravery: 0,
                base_greed: 0,
                traits,
            },
        ))
        .id();

    // First update to run loaders and initialize
    app.update();

    // Advance time by 0.1 real seconds, which corresponds to 6.0 game seconds (time_scale = 60.0)
    app.insert_resource(TimeUpdateStrategy::ManualDuration(Duration::from_secs_f32(0.1)));
    app.update();

    let world = app.world();
    let needs = world.get::<Needs>(entity).unwrap();

    // Base decay rates:
    // hunger: 2.0. With GLUTTON (1.5x) -> 3.0. For 6s -> 18.0
    // social: 0.5. With LONER (0.5x) -> 0.25. For 6s -> 1.5. So social = 98.5
    assert!((needs.hunger - 18.0).abs() < 1e-4, "expected hunger 18.0, got {}", needs.hunger);
    assert!((needs.social - 98.5).abs() < 1e-4, "expected social 98.5, got {}", needs.social);
}

#[test]
fn test_skill_xp_and_level_up() {
    let mut app = setup_test_app();

    let entity = app
        .world_mut()
        .spawn((
            Transform::default(),
            Needs {
                health: 100.0,
                max_health: 100.0,
                ..default()
            },
            Personality {
                traits: std::collections::HashSet::from(["ATHLETIC".to_string()]),
                ..default()
            },
            YukkuriStats {
                intelligence: 1.5,
                ..default()
            },
            EmotionalState::default(),
        ))
        .id();

    // Update to initialize personality and skills
    app.update();

    // ATHLETIC trait has skill modifier for athletics: { passion_multiplier = 1.5, soft_cap_offset = 5 }
    // Thus, athletics skill passion should be 1.5.
    // Soft cap level: base 10 + (passion 1.5 * 2) = 13 + offset 5 = 18.
    // Let's send AddXpEvent message for athletics:
    let _ = app.world_mut().run_system_once(move |mut writer: MessageWriter<vibecoded_yukkuri_game::simulation::skills::AddXpEvent>| {
        writer.write(vibecoded_yukkuri_game::simulation::skills::AddXpEvent {
            entity,
            skill_id: "athletics".to_string(),
            amount: 50.0,
        });
    });

    app.update();

    let world = app.world();
    let skills = world.get::<vibecoded_yukkuri_game::simulation::skills::Skills>(entity).unwrap();
    let state = skills.states.get("athletics").unwrap();

    // XP gained: Amount (50) * Passion (1.5) * Intelligence (1.5) * Soft Cap Multiplier (1.0) = 112.5.
    // Base required XP for level 1: 100.0 * 1.5^1 = 150.0.
    // So current_xp should be 112.5, level should still be 1.
    assert_eq!(state.level, 1);
    assert!((state.current_xp - 112.5).abs() < 1e-4, "expected xp 112.5, got {}", state.current_xp);

    // Let's add more XP to level up:
    let _ = app.world_mut().run_system_once(move |mut writer: MessageWriter<vibecoded_yukkuri_game::simulation::skills::AddXpEvent>| {
        writer.write(vibecoded_yukkuri_game::simulation::skills::AddXpEvent {
            entity,
            skill_id: "athletics".to_string(),
            amount: 30.0, // XP gain = 30 * 1.5 * 1.5 = 67.5. Total XP = 180.0
        });
    });

    app.update();

    let world = app.world();
    let skills = world.get::<vibecoded_yukkuri_game::simulation::skills::Skills>(entity).unwrap();
    let state = skills.states.get("athletics").unwrap();

    // Total XP was 180.0. Required for level 1 was 150.0.
    // So it should level up to 2.
    // remaining XP = 180.0 - 150.0 = 30.0.
    assert_eq!(state.level, 2);
    assert!((state.current_xp - 30.0).abs() < 1e-4, "expected remaining xp 30.0, got {}", state.current_xp);
}

#[test]
fn test_skill_decay() {
    let mut app = setup_test_app();

    let entity = app
        .world_mut()
        .spawn((
            Transform::default(),
            Needs::default(),
            Personality::default(),
            YukkuriStats::default(),
        ))
        .id();

    app.update();

    // Gain some XP in combat skill:
    let _ = app.world_mut().run_system_once(move |mut writer: MessageWriter<vibecoded_yukkuri_game::simulation::skills::AddXpEvent>| {
        writer.write(vibecoded_yukkuri_game::simulation::skills::AddXpEvent {
            entity,
            skill_id: "combat".to_string(),
            amount: 20.0, // Passion 1.0, Intelligence 1.0 -> 20.0 XP
        });
    });

    app.update();

    // Verify initial XP:
    {
        let skills = app.world().get::<vibecoded_yukkuri_game::simulation::skills::Skills>(entity).unwrap();
        let state = skills.states.get("combat").unwrap();
        assert_eq!(state.current_xp, 20.0);
    }

    // Advance time by 1.5 game-days = 1.5 * 86400 = 129600 game seconds
    {
        let mut time_elapsed = app.world_mut().resource_mut::<TimeElapsed>();
        time_elapsed.elapsed += 129600.0;
    }

    app.update();

    let world = app.world();
    let skills = world.get::<vibecoded_yukkuri_game::simulation::skills::Skills>(entity).unwrap();
    let state = skills.states.get("combat").unwrap();

    // Decay rate for combat is 50.0 per day.
    // Days since last use: 1.5 days.
    // Excess days: 1.5 - 1.0 grace = 0.5 days.
    // Loss: 50.0 * 0.5 = 25.0 XP.
    // Since initial XP was 20.0, current_xp should decay to 0.0.
    assert_eq!(state.current_xp, 0.0);
}

#[test]
fn test_navigation_grid_updates() {
    use vibecoded_yukkuri_game::simulation::hpa::NavigationService;
    use avian2d::prelude::*;

    let mut app = setup_test_app();
    app.insert_resource(NavigationService::new(400.0, 400.0, 25.0));

    // Spawn a static obstacle
    app.world_mut().spawn((
        Transform::from_xyz(100.0, 100.0, 0.0),
        RigidBody::Static,
        Collider::rectangle(50.0, 50.0),
    ));

    app.update();

    let nav_service = app.world().resource::<NavigationService>();
    let grid = nav_service.grid.read().unwrap();
    
    // Position (100, 100) translates to grid cells around (4, 4) if grid step size is 25
    // Let's verify that some cells are blocked (not walkable: access_mask = 0)
    let blocked_count = grid.cells.iter().filter(|c| c.access_mask == 0).count();
    assert!(blocked_count > 0, "Expected some blocked cells due to static collider");
}

#[test]
fn test_mount_stacking_and_dismount() {
    use vibecoded_yukkuri_game::simulation::mount::{Mount, PendingDismount, HierarchyProxyCollider};
    use avian2d::prelude::*;

    let mut app = setup_test_app();

    // Parent
    let parent_id = app.world_mut().spawn((
        Transform::from_xyz(0.0, 0.0, 0.0),
        Mount::default(),
        Collider::circle(15.0),
        RigidBody::Dynamic,
    )).id();

    // Child
    let child_id = app.world_mut().spawn((
        Transform::from_xyz(0.0, 30.0, 0.0),
        Mount::default(),
        Collider::circle(15.0),
        RigidBody::Dynamic,
    )).id();

    // Mount child to parent
    app.world_mut().entity_mut(child_id).set_parent_in_place(parent_id);
    app.world_mut().entity_mut(child_id).remove::<RigidBody>();
    {
        let mut p_mount = app.world_mut().get_mut::<Mount>(parent_id).unwrap();
        p_mount.children_ids.push(child_id);
        p_mount.structure_dirty = true;
    }

    app.update();

    // Verify proxy collider spawned
    let mut proxy_query = app.world_mut().query::<(Entity, &HierarchyProxyCollider)>();
    let proxies: Vec<(Entity, &HierarchyProxyCollider)> = proxy_query.iter(app.world()).collect();
    assert_eq!(proxies.len(), 1);
    assert_eq!(proxies[0].1.root_entity, parent_id);

    // Dismount child
    app.world_mut().entity_mut(child_id).remove_parent_in_place();
    app.world_mut().entity_mut(child_id).insert(PendingDismount {
        parent_id,
        time_in_pending: 0.0,
    });

    // Run system to process dismount
    app.update();

    // Verify child has PendingDismount removed and RigidBody restored
    assert!(app.world().entity(child_id).get::<PendingDismount>().is_none());
    assert!(app.world().entity(child_id).get::<RigidBody>().is_some());
}

#[test]
fn test_inventory_pickup_and_drop() {
    use vibecoded_yukkuri_game::simulation::inventory::{
        InventoryComponent, InventoryPickupRequest, InventoryDropRequest, ItemStats, ItemRegistry, ItemConfig
    };

    let mut app = setup_test_app();

    // Seed registry
    let mut registry = ItemRegistry::default();
    registry.items.insert("cookie".to_string(), ItemConfig {
        name: "Cookie".to_string(),
        image: "cookie.png".to_string(),
        width: 20,
        height: 20,
        cost: 10,
        nutrition: Some(50.0),
        fun: None,
        comfort: None,
        quality: None,
        is_portable: true,
        obstacle_type: None,
        light_radius: None,
        light_color: None,
        light_intensity: None,
    });
    app.insert_resource(registry);

    // Picker
    let picker_id = app.world_mut().spawn((
        Transform::default(),
        InventoryComponent {
            capacity: 20,
            items: Vec::new(),
        },
    )).id();

    // Item to pick up
    let item_id = app.world_mut().spawn((
        Transform::from_xyz(5.0, 5.0, 0.0),
        ItemStats {
            type_id: "cookie".to_string(),
            value: 10.0,
            name: "Cookie".to_string(),
            nutrition: 50.0,
            fun: 0.0,
            comfort: 0.0,
            is_portable: true,
            quality: 1.0,
        },
    )).id();

    // Request pickup
    app.world_mut().entity_mut(picker_id).insert(InventoryPickupRequest {
        target_entity_id: item_id,
    });

    app.update();

    // Verify item is picked up
    assert!(app.world().get_entity(item_id).is_err());
    let inv = app.world().get::<InventoryComponent>(picker_id).unwrap();
    assert_eq!(inv.items.len(), 1);
    assert_eq!(inv.items[0].item_type_id, "cookie");

    // Request drop
    app.world_mut().entity_mut(picker_id).insert(InventoryDropRequest {
        item_type_id: "cookie".to_string(),
        quantity: 1,
    });

    app.update();

    // Verify item is dropped and inventory is empty
    let inv_after = app.world().get::<InventoryComponent>(picker_id).unwrap();
    assert!(inv_after.items.is_empty());
}

#[test]
fn test_visual_bobbing_and_flight() {
    use vibecoded_yukkuri_game::simulation::movement::MovementController;
    use vibecoded_yukkuri_game::render::YukkuriSprite;
    use vibecoded_yukkuri_game::ai::Flight;
    use avian2d::prelude::*;

    let mut app = setup_test_app();

    // Child sprite entity
    let sprite_entity = app.world_mut().spawn((
        Transform::default(),
        Visibility::default(),
    )).id();

    // Parent
    let _parent_id = app.world_mut().spawn((
        Transform::default(),
        MovementController::default(),
        LinearVelocity(Vec2::new(10.0, 0.0)),
        YukkuriSprite {
            image_name: "reimu.png".to_string(),
            width: 32,
            height: 32,
            layer: 2,
            flip_x: false,
            flip_y: false,
            alpha: 255,
            frame_count: 1,
            frame_duration: 0.1,
            current_frame: 0,
            timer: 0.0,
            loop_anim: false,
            is_animating: false,
            sprite_entity: Some(sprite_entity),
        },
        Flight {
            flight_state: 1, // TAKEOFF
            stamina: 100.0,
            vertical_speed: 100.0,
            max_altitude: 100.0,
            ..default()
        },
    )).id();

    // First update to register and initialize time
    app.update();

    // Set manual time update strategy to allow time to pass
    app.insert_resource(TimeUpdateStrategy::ManualDuration(std::time::Duration::from_secs_f32(1.0)));

    // Second update to step systems with delta time
    app.update();

    // Verify child transform updated with vertical bobbing + altitude offset
    let child_trans = app.world().get::<Transform>(sprite_entity).unwrap();
    assert!(child_trans.translation.y > 0.0);
}

#[test]
fn test_time_and_environment_systems() {
    use vibecoded_yukkuri_game::ai::persistence::TimeElapsed;
    use vibecoded_yukkuri_game::render::lighting::LightSource;
    use vibecoded_yukkuri_game::simulation::needs::FloatingText;

    let mut app = setup_test_app();

    // 1. Test Virtual Clock Ticking
    app.insert_resource(TimeElapsed {
        elapsed: 0.0,
        scale: 1.0,
        game_speed: 1.0,
    });

    app.update();
    app.insert_resource(TimeUpdateStrategy::ManualDuration(std::time::Duration::from_secs_f32(1.0)));
    app.update();

    let time_elapsed = app.world().resource::<TimeElapsed>();
    assert!(time_elapsed.elapsed > 0.0, "Time elapsed did not tick upward");

    // 2. Test Darkness Stress Accumulation at Night
    // Disable cursor light so the entity is in complete darkness
    use vibecoded_yukkuri_game::render::lighting::CursorLightMarker;
    let mut cursor_light_query = app.world_mut().query_filtered::<&mut LightSource, With<CursorLightMarker>>();
    if let Some(mut light) = cursor_light_query.iter_mut(app.world_mut()).next() {
        light.base_intensity = 0.0;
        light.intensity = 0.0;
    }

    // Spawn entity at (0, 0)
    let entity = app.world_mut().spawn((
        Transform::from_xyz(0.0, 0.0, 0.0),
        GlobalTransform::default(),
        Needs::default(),
        EmotionalState {
            stress: 0.0,
            happiness: 0.0,
        },
    )).id();

    // Force time to night (hour 0.0 = midnight)
    app.insert_resource(TimeElapsed {
        elapsed: 0.0, // hour_of_day is calculated from elapsed. 0.0 elapsed means hour 0.0
        scale: 1.0,
        game_speed: 1.0,
    });

    // Run update with delta time to tick stress
    app.update(); // first to set delta
    app.update(); // second to tick needs emotional decay

    let stress_val = app.world().get::<EmotionalState>(entity).unwrap().stress;
    assert!(stress_val > 0.0, "Stress did not accumulate in darkness at night");

    // 3. Test Proximity Light Safety
    // Reset stress to 0
    if let Some(mut emo) = app.world_mut().get_mut::<EmotionalState>(entity) {
        emo.stress = 0.0;
    }

    // Spawn a light source entity nearby
    app.world_mut().spawn((
        Transform::from_xyz(20.0, 20.0, 0.0),
        GlobalTransform::default(),
        LightSource {
            radius: 100.0,
            color: Color::WHITE,
            intensity: 1.0,
            flicker_style: 0,
            base_intensity: 1.0,
        },
    ));

    // Tick the systems
    app.update();

    let emotional = app.world().get::<EmotionalState>(entity).unwrap();
    assert_eq!(emotional.stress, 0.0, "Stress accumulated despite being near a light source");

    // 4. Test Floating Text Decay and Despawn
    let ft_entity = app.world_mut().spawn((
        Transform::from_xyz(0.0, 0.0, 0.0),
        TextColor(Color::WHITE),
        FloatingText {
            velocity: Vec2::new(0.0, 50.0),
            lifetime: 0.0,
            max_lifetime: 1.0,
        },
    )).id();

    // Step 0.5 seconds
    app.insert_resource(TimeUpdateStrategy::ManualDuration(std::time::Duration::from_secs_f32(0.5)));
    app.update();

    let ft_trans = app.world().get::<Transform>(ft_entity).unwrap();
    let ft_color = app.world().get::<TextColor>(ft_entity).unwrap();
    assert!(ft_trans.translation.y > 0.0, "Floating text did not move upward");
    assert!(ft_color.0.alpha() < 1.0, "Floating text opacity did not fade");

    // Step another 0.6 seconds (exceeding 1.0s max lifetime)
    app.insert_resource(TimeUpdateStrategy::ManualDuration(std::time::Duration::from_secs_f32(0.6)));
    app.update();

    assert!(app.world().get_entity(ft_entity).is_err(), "Floating text did not despawn on expiration");
}

#[test]
fn test_runtime_family_formation() {
    let mut app = setup_test_app();
    app.insert_resource(TimeUpdateStrategy::ManualDuration(std::time::Duration::from_secs_f32(2.5)));

    let elapsed = app.world().get_resource::<TimeElapsed>().map(|t| t.elapsed).unwrap_or(43200.0);

    // Spawn A
    let entity_a = app.world_mut().spawn((
        Transform::from_xyz(0.0, 0.0, 0.0),
        StableId(100),
        RelationshipRegistry::default(),
    )).id();

    // Spawn B
    let mut reg_b = RelationshipRegistry::default();
    let mut rel_b_to_a = RelationshipData::new(elapsed);
    rel_b_to_a.affinity = 90.0;
    rel_b_to_a.trust = 90.0;
    reg_b.relationships.insert(100, rel_b_to_a);

    let entity_b = app.world_mut().spawn((
        Transform::from_xyz(50.0, 0.0, 0.0),
        StableId(200),
        reg_b,
    )).id();

    // Add high affinity and trust from A to B (StableId 200) in A's registry
    {
        let mut reg_a = app.world_mut().get_mut::<RelationshipRegistry>(entity_a).unwrap();
        let mut rel_a_to_b = RelationshipData::new(elapsed);
        rel_a_to_b.affinity = 90.0;
        rel_a_to_b.trust = 90.0;
        reg_a.relationships.insert(200, rel_a_to_b);
    }

    // Update app twice (first updates time strategy, second advances time by 2.5 seconds and triggers family_formation_system)
    app.update();
    app.update();

    // Verify family group IDs
    let reg_a = app.world().get::<RelationshipRegistry>(entity_a).unwrap();
    let reg_b = app.world().get::<RelationshipRegistry>(entity_b).unwrap();

    assert!(reg_a.family_group_id.is_some(), "Entity A should have a family group assigned");
    assert!(reg_b.family_group_id.is_some(), "Entity B should have a family group assigned");
    assert_eq!(reg_a.family_group_id, reg_b.family_group_id, "Family group IDs must match");
}



