use bevy::prelude::*;
use avian2d::prelude::*;
use std::sync::Mutex;
use vibecoded_yukkuri_game::ai::{
    AIPlugin, AIState, StableId, Needs,
};
use vibecoded_yukkuri_game::ai::persistence::{save_game, load_game, Economy, TimeElapsed};
use vibecoded_yukkuri_game::prefabs::{load_prefab, spawn_yukkuri_prefab};
use vibecoded_yukkuri_game::render::{TextureAtlasRegistry, YukkuriTypeRegistry};

static TEST_MUTEX: Mutex<()> = Mutex::new(());

fn init_python() {}

#[test]
fn test_persistence_round_trip() {
    let _lock = TEST_MUTEX.lock().unwrap_or_else(|e| e.into_inner());
    init_python();

    // 1. Initialize Bevy app
    let mut app = App::new();
    app.add_plugins(MinimalPlugins);
    app.add_plugins(bevy::input::InputPlugin);
    app.add_plugins(bevy::asset::AssetPlugin::default());
    app.add_plugins(PhysicsPlugins::default());
    app.add_plugins(AIPlugin);
    app.add_plugins(vibecoded_yukkuri_game::simulation::SimulationPlugin);
    app.add_plugins(vibecoded_yukkuri_game::render::YukkuriRenderPlugin);

    // Register our custom resources for reflection
    app.register_type::<Economy>()
        .register_type::<TimeElapsed>()
        .init_resource::<Economy>()
        .init_resource::<TimeElapsed>();

    // Initialize Avian diagnostic resources required by physics systems
    app.init_resource::<avian2d::collider_tree::ColliderTreeDiagnostics>();
    app.init_resource::<avian2d::spatial_query::SpatialQueryDiagnostics>();
    app.init_resource::<avian2d::dynamics::solver::SolverDiagnostics>();
    app.init_resource::<avian2d::collision::CollisionDiagnostics>();

    // 2. Load prefab and spawn entity
    let prefab = load_prefab("data/prefabs/reimu.toml")
        .expect("Failed to load reimu.toml prefab");

    let spawned_entity = std::sync::Arc::new(std::sync::Mutex::new(None));
    let spawned_entity_clone = spawned_entity.clone();
    let prefab_clone = prefab.clone();

    app.add_systems(PostStartup, move |mut commands: Commands, asset_server: Res<AssetServer>, atlas_registry: Res<TextureAtlasRegistry>, type_registry: Res<YukkuriTypeRegistry>| {
        let entity = spawn_yukkuri_prefab(
            &mut commands,
            &prefab_clone,
            Vec2::new(100.0, 100.0),
            &asset_server,
            &atlas_registry,
            &type_registry,
        );
        *spawned_entity_clone.lock().unwrap() = Some(entity);
    });

    // Run startup systems
    app.update();

    let entity = {
        let guard = spawned_entity.lock().unwrap();
        guard.expect("Failed to spawn entity")
    };

    // 3. Set components and resources
    {
        let world = app.world_mut();
        
        // Modify needs
        if let Some(mut needs) = world.get_mut::<Needs>(entity) {
            needs.hunger = 80.0;
        }

        // Set global economy and time elapsed
        world.insert_resource(Economy { money: 2345 });
        world.insert_resource(TimeElapsed { elapsed: 678.9, ..Default::default() });

        // Set AI state to test ticking and FFI caching
        if let Some(mut ai_state) = world.get_mut::<AIState>(entity) {
            ai_state.current_action = "Sleeping".to_string();
        }
    }

    // Tick the AI system once to populate Python-side _ai_states
    app.update();

    // 4. Save the game
    let save_path = "test_persistence_round_trip.sqlite";
    let saved_time = app.world().resource::<TimeElapsed>().elapsed;
    let saved_hunger = app.world().get::<Needs>(entity).unwrap().hunger;
    save_game(app.world_mut(), save_path).expect("Failed to save game");

    // 5. Change state so we can verify restoration
    {
        let world = app.world_mut();
        world.insert_resource(Economy { money: 0 });
        world.insert_resource(TimeElapsed { elapsed: 0.0, ..Default::default() });
        world.despawn(entity);
    }

    // 6. Load the game
    load_game(app.world_mut(), save_path).expect("Failed to load game");

    // 7. Verify restoration
    {
        let world = app.world_mut();
        
        // Economy and Time
        let eco = world.get_resource::<Economy>().expect("Economy resource missing");
        assert_eq!(eco.money, 2345);
        let time = world.get_resource::<TimeElapsed>().expect("TimeElapsed resource missing");
        assert_eq!(time.elapsed, saved_time);

        // Entity must be restored
        let mut query = world.query_filtered::<Entity, With<Needs>>();
        let restored_entities: Vec<Entity> = query.iter(world).collect();
        assert_eq!(restored_entities.len(), 1);
        let restored_entity = restored_entities[0];

        // Needs restored
        let needs = world.get::<Needs>(restored_entity).expect("Needs missing");
        assert_eq!(needs.hunger, saved_hunger);

        // StableId restored and correct
        let stable = world.get::<StableId>(restored_entity).expect("StableId missing");
        assert_eq!(stable.0, entity.to_bits());
    }

    // Clean up temporary save file
    let _ = std::fs::remove_file(save_path);
}
