use bevy::prelude::*;
use avian2d::prelude::*;
use std::sync::{Arc, Mutex};
use vibecoded_yukkuri_game::ai::{
    AIPlugin, MoveTarget, StableId, SteeringConfig, VisibleTargets,
    Predator, YukkuriStats, RelationshipRegistry, Personality, Flight,
};
use vibecoded_yukkuri_game::render::{TextureAtlasRegistry, YukkuriTypeRegistry};
use vibecoded_yukkuri_game::prefabs::{load_prefab, spawn_yukkuri_prefab};

// ---------------------------------------------------------------------------
// Shared test infrastructure
// ---------------------------------------------------------------------------

/// Serialises test execution so no two tests build a Bevy `App` concurrently.
static TEST_MUTEX: Mutex<()> = Mutex::new(());

fn init_python() {}

/// Creates a minimal headless Bevy app with AIPlugin and physics.
///
/// Does **not** call `app.update()` — callers must add any `PostStartup`
/// spawn systems before their first `app.update()` so they fire during startup.
fn make_app() -> App {
    let mut app = App::new();
    app.add_plugins(MinimalPlugins);
    app.add_plugins(bevy::input::InputPlugin);
    app.add_plugins(bevy::asset::AssetPlugin::default());
    app.add_plugins(PhysicsPlugins::default());
    app.add_plugins(AIPlugin);
    app.add_plugins(vibecoded_yukkuri_game::simulation::SimulationPlugin);
    app.add_plugins(vibecoded_yukkuri_game::render::YukkuriRenderPlugin);
    // Initialize Avian diagnostic resources required by physics systems
    app.init_resource::<avian2d::collider_tree::ColliderTreeDiagnostics>();
    app.init_resource::<avian2d::spatial_query::SpatialQueryDiagnostics>();
    app.init_resource::<avian2d::dynamics::solver::SolverDiagnostics>();
    app.init_resource::<avian2d::collision::CollisionDiagnostics>();
    app.insert_resource(bevy::time::TimeUpdateStrategy::ManualDuration(std::time::Duration::from_secs_f32(0.2)));
    app
}

/// Registers a `PostStartup` system that spawns one yukkuri at `position`.
///
/// Returns an `Arc<Mutex<Option<Entity>>>` that will contain the spawned
/// entity after the first `app.update()`.  Must be called **before** the
/// first `app.update()` on `app`.
fn add_spawn_system(app: &mut App, position: Vec2) -> Arc<Mutex<Option<Entity>>> {
    let prefab = load_prefab("data/prefabs/reimu.toml")
        .expect("Failed to load reimu.toml prefab");

    let slot: Arc<Mutex<Option<Entity>>> = Arc::new(Mutex::new(None));
    let slot_clone = slot.clone();
    let prefab_clone = prefab.clone();

    app.add_systems(
        PostStartup,
        move |mut commands: Commands,
              asset_server: Res<AssetServer>,
              atlas_registry: Res<TextureAtlasRegistry>,
              type_registry: Res<YukkuriTypeRegistry>| {
            let e = spawn_yukkuri_prefab(
                &mut commands,
                &prefab_clone,
                position,
                &asset_server,
                &atlas_registry,
                &type_registry,
            );
            *slot_clone.lock().unwrap() = Some(e);
        },
    );

    slot
}

/// Convenience: register one spawn, fire startup, and return the entity.
fn spawn_one(app: &mut App, position: Vec2) -> Entity {
    let slot = add_spawn_system(app, position);
    app.update(); // fires PostStartup → fills slot
    let entity = *slot.lock().unwrap();
    entity.expect("PostStartup spawn system did not run")
}

// ---------------------------------------------------------------------------
// Test 1 – SteeringConfig is inserted with TOML values
// ---------------------------------------------------------------------------
#[test]
fn test_steering_config_inserted_from_prefab() {
    let _lock = TEST_MUTEX.lock().unwrap_or_else(|e| e.into_inner());
    init_python();

    let mut app = make_app();
    let entity = spawn_one(&mut app, Vec2::new(0.0, 0.0));

    let world = app.world();
    let cfg = world
        .get::<SteeringConfig>(entity)
        .expect("SteeringConfig component missing after spawn");

    // Values come from data/prefabs/reimu.toml [steering]
    assert_eq!(cfg.max_speed, 150.0, "max_speed mismatch");
    assert_eq!(cfg.perception_radius, 300.0, "perception_radius mismatch");
    assert_eq!(cfg.arrival_radius, 25.0, "arrival_radius mismatch");
}

// ---------------------------------------------------------------------------
// Test 2 – Nearby entities are detected by populate_visible_targets_system
// ---------------------------------------------------------------------------
#[test]
fn test_perception_detects_nearby_entities() {
    let _lock = TEST_MUTEX.lock().unwrap_or_else(|e| e.into_inner());
    init_python();

    let mut app = make_app();

    // Register both spawns before the first update so both PostStartup
    // systems fire during startup.
    let slot1 = add_spawn_system(&mut app, Vec2::new(0.0, 0.0));
    let slot2 = add_spawn_system(&mut app, Vec2::new(100.0, 0.0));

    app.update(); // startup → both entities spawned

    let e1 = slot1.lock().unwrap().expect("e1 not spawned");
    let e2 = slot2.lock().unwrap().expect("e2 not spawned");

    // Tick once more so populate_visible_targets_system runs in Update.
    app.update();

    let world = app.world();
    let v1 = world.get::<VisibleTargets>(e1).expect("e1 missing VisibleTargets");
    let v2 = world.get::<VisibleTargets>(e2).expect("e2 missing VisibleTargets");

    let e2_id = e2.index().index();
    let e1_id = e1.index().index();

    assert!(
        v1.targets.iter().any(|t| t.entity_id == e2_id),
        "e1 should see e2 (distance 100 < radius 300)"
    );
    assert!(
        v2.targets.iter().any(|t| t.entity_id == e1_id),
        "e2 should see e1 (distance 100 < radius 300)"
    );
}

// ---------------------------------------------------------------------------
// Test 3 – Entities beyond perception_radius are NOT detected
// ---------------------------------------------------------------------------
#[test]
fn test_perception_ignores_distant_entities() {
    let _lock = TEST_MUTEX.lock().unwrap_or_else(|e| e.into_inner());
    init_python();

    let mut app = make_app();

    let slot1 = add_spawn_system(&mut app, Vec2::new(0.0, 0.0));
    let slot2 = add_spawn_system(&mut app, Vec2::new(500.0, 0.0));

    app.update();

    let e1 = slot1.lock().unwrap().expect("e1 not spawned");
    let e2 = slot2.lock().unwrap().expect("e2 not spawned");

    app.update();

    let world = app.world();
    let v1 = world.get::<VisibleTargets>(e1).expect("e1 missing VisibleTargets");
    let v2 = world.get::<VisibleTargets>(e2).expect("e2 missing VisibleTargets");

    let e2_id = e2.index().index();
    let e1_id = e1.index().index();

    assert!(
        !v1.targets.iter().any(|t| t.entity_id == e2_id),
        "e1 should NOT see e2 at distance 500 > radius 300"
    );
    assert!(
        !v2.targets.iter().any(|t| t.entity_id == e1_id),
        "e2 should NOT see e1 at distance 500 > radius 300"
    );
}

// ---------------------------------------------------------------------------
// Test 4 – stable_id in TargetInfo matches target entity bits
// ---------------------------------------------------------------------------
#[test]
fn test_visible_target_stable_id_matches_entity_bits() {
    let _lock = TEST_MUTEX.lock().unwrap_or_else(|e| e.into_inner());
    init_python();

    let mut app = make_app();

    let slot1 = add_spawn_system(&mut app, Vec2::new(0.0, 0.0));
    let slot2 = add_spawn_system(&mut app, Vec2::new(100.0, 0.0));

    app.update();

    let e1 = slot1.lock().unwrap().expect("e1 not spawned");
    let e2 = slot2.lock().unwrap().expect("e2 not spawned");

    app.update();

    let world = app.world();

    let e2_stable = world
        .get::<StableId>(e2)
        .expect("e2 missing StableId")
        .0;

    let v1 = world.get::<VisibleTargets>(e1).expect("e1 missing VisibleTargets");
    let e2_id = e2.index().index();

    let target = v1
        .targets
        .iter()
        .find(|t| t.entity_id == e2_id)
        .expect("e2 not found in e1's VisibleTargets");

    assert_eq!(
        target.stable_id, e2_stable,
        "stable_id in TargetInfo should match e2.to_bits()"
    );
}

// ---------------------------------------------------------------------------
// Test 5 – MoveTarget is removed on arrival (acceptance_radius reached)
// ---------------------------------------------------------------------------
#[test]
fn test_move_target_removed_on_arrival() {
    let _lock = TEST_MUTEX.lock().unwrap_or_else(|e| e.into_inner());
    init_python();

    let mut app = make_app();
    let entity = spawn_one(&mut app, Vec2::new(0.0, 0.0));

    // Insert a MoveTarget at the entity's own position → dist ≈ 0 ≤ acceptance_radius.
    app.world_mut().entity_mut(entity).insert(MoveTarget {
        position: Vec2::new(0.0, 0.0),
        acceptance_radius: 50.0,
    });

    app.update();

    assert!(
        app.world().get::<MoveTarget>(entity).is_none(),
        "MoveTarget should be removed once within acceptance_radius"
    );
}

// ---------------------------------------------------------------------------
// Test 6 – Steering sets LinearVelocity toward MoveTarget
// ---------------------------------------------------------------------------
#[test]
fn test_steering_applies_velocity_toward_target() {
    let _lock = TEST_MUTEX.lock().unwrap_or_else(|e| e.into_inner());
    init_python();

    let mut app = make_app();
    let entity = spawn_one(&mut app, Vec2::new(0.0, 0.0));

    // Place target 200 units to the right — well outside acceptance_radius.
    app.world_mut().entity_mut(entity).insert(MoveTarget {
        position: Vec2::new(200.0, 0.0),
        acceptance_radius: 10.0,
    });

    app.update();

    let vel = app
        .world()
        .get::<vibecoded_yukkuri_game::simulation::kinematic_controller::KinematicVelocity>(entity)
        .expect("KinematicVelocity component missing");

    assert!(
        vel.target.x > 0.0,
        "KinematicVelocity.target.x should be positive when MoveTarget is to the right; got {:?}",
        vel.target
    );
    assert!(
        vel.target.y.abs() < 1.0,
        "KinematicVelocity.target.y should be near zero for purely horizontal target; got {:?}",
        vel.target
    );
}

// ---------------------------------------------------------------------------
// Test 7 – Predator/Prey perception is correctly classified
// ---------------------------------------------------------------------------
#[test]
fn test_perception_predator_prey_flags() {
    let _lock = TEST_MUTEX.lock().unwrap_or_else(|e| e.into_inner());
    init_python();

    let mut app = make_app();

    let predator_ent = app.world_mut().spawn((
        Transform::from_xyz(0.0, 0.0, 0.0),
        StableId(1),
        YukkuriStats {
            type_id: "flandre".to_string(),
            ..default()
        },
        RelationshipRegistry::default(),
        Personality::default(),
        VisibleTargets::default(),
        SteeringConfig {
            perception_radius: 300.0,
            ..default()
        },
        Predator {
            prey_tags: ["reimu".to_string()].into_iter().collect(),
            ..default()
        },
    )).id();

    let prey_ent = app.world_mut().spawn((
        Transform::from_xyz(100.0, 0.0, 0.0),
        StableId(2),
        YukkuriStats {
            type_id: "reimu".to_string(),
            ..default()
        },
        RelationshipRegistry::default(),
        Personality::default(),
        VisibleTargets::default(),
        SteeringConfig {
            perception_radius: 300.0,
            ..default()
        },
    )).id();

    // Tick to run populate_visible_targets_system
    app.update();
    app.update();

    let world = app.world();
    let v_predator = world.get::<VisibleTargets>(predator_ent).unwrap();
    let v_prey = world.get::<VisibleTargets>(prey_ent).unwrap();

    let target_prey = v_predator.targets.iter().find(|t| t.entity_id == prey_ent.index().index()).expect("flandre should see reimu");
    assert!(target_prey.is_prey, "flandre should see reimu as prey");
    assert!(!target_prey.is_threat, "flandre should not see reimu as threat");

    let target_pred = v_prey.targets.iter().find(|t| t.entity_id == predator_ent.index().index()).expect("reimu should see flandre");
    assert!(!target_pred.is_prey, "reimu should not see flandre as prey");
    assert!(target_pred.is_threat, "reimu should see flandre as threat");
}

// ---------------------------------------------------------------------------
// Test 8 – Obstacles block target perception (Line of Sight)
// ---------------------------------------------------------------------------
#[test]
fn test_perception_line_of_sight() {
    let _lock = TEST_MUTEX.lock().unwrap_or_else(|e| e.into_inner());
    init_python();

    let mut app = make_app();

    let observer = app.world_mut().spawn((
        Transform::from_xyz(0.0, 0.0, 0.0),
        StableId(1),
        YukkuriStats::default(),
        RelationshipRegistry::default(),
        Personality::default(),
        VisibleTargets::default(),
        SteeringConfig {
            perception_radius: 300.0,
            ..default()
        },
    )).id();

    let target = app.world_mut().spawn((
        Transform::from_xyz(100.0, 0.0, 0.0),
        StableId(2),
        YukkuriStats::default(),
        RelationshipRegistry::default(),
        Personality::default(),
        VisibleTargets::default(),
        SteeringConfig {
            perception_radius: 300.0,
            ..default()
        },
    )).id();

    // Spawn wall at (50.0, 0.0) blocking LOS
    app.world_mut().spawn((
        Transform::from_xyz(50.0, 0.0, 0.0),
        Collider::rectangle(20.0, 100.0),
        RigidBody::Static,
    ));

    // Update once to run physics & spatial query system to build spatial query maps
    app.update();

    let world = app.world();
    let visible = world.get::<VisibleTargets>(observer).unwrap();
    let target_id = target.index().index();

    assert!(
        !visible.targets.iter().any(|t| t.entity_id == target_id),
        "perception should be blocked by obstacle"
    );
}

// ---------------------------------------------------------------------------
// Test 9 – Prefab loader spawns Predator and customized Flight components
// ---------------------------------------------------------------------------
#[test]
fn test_prefab_spawns_predator_and_flight() {
    let _lock = TEST_MUTEX.lock().unwrap_or_else(|e| e.into_inner());
    init_python();

    let mut app = make_app();

    let prefab = load_prefab("data/prefabs/flandre.toml")
        .expect("Failed to load flandre.toml prefab");

    let spawned = std::sync::Arc::new(std::sync::Mutex::new(None));
    let spawned_clone = spawned.clone();

    app.add_systems(PostStartup, move |mut commands: Commands, asset_server: Res<AssetServer>, atlas_registry: Res<TextureAtlasRegistry>, type_registry: Res<YukkuriTypeRegistry>| {
        let entity = spawn_yukkuri_prefab(
            &mut commands,
            &prefab,
            Vec2::new(0.0, 0.0),
            &asset_server,
            &atlas_registry,
            &type_registry,
        );
        *spawned_clone.lock().unwrap() = Some(entity);
    });

    app.update();

    let entity = spawned.lock().unwrap().expect("flandre not spawned");

    let world = app.world();
    let predator = world.get::<Predator>(entity).expect("Predator component missing on spawned flandre");
    assert!(predator.prey_tags.contains("reimu"), "flandre should hunt reimu");
    assert_eq!(predator.prey_sense_radius, 350.0);
    assert_eq!(predator.aggression, 1.5);
    assert_eq!(predator.dps, 25.0);

    let flight = world.get::<Flight>(entity).expect("Flight component missing on spawned flandre");
    assert_eq!(flight.max_stamina, 120.0);
    assert_eq!(flight.max_altitude, 80.0);
}
