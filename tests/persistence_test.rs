use bevy::prelude::*;
use avian2d::prelude::*;
use std::sync::Mutex;
use std::fs;
use pyo3::types::PyAnyMethods;
use vibecoded_yukkuri_game::ai::{
    yukkuri_rust, AIPlugin, AIState, StableId, Needs, PythonState,
};
use vibecoded_yukkuri_game::ai::persistence::{save_game, load_game, Economy, TimeElapsed};
use vibecoded_yukkuri_game::prefabs::{load_prefab, spawn_yukkuri_prefab};
use vibecoded_yukkuri_game::render::{TextureAtlasRegistry, YukkuriTypeRegistry};

static TEST_MUTEX: Mutex<()> = Mutex::new(());

fn init_python() {
    static PYTHON_INIT: std::sync::OnceLock<()> = std::sync::OnceLock::new();
    PYTHON_INIT.get_or_init(|| {
        pyo3::append_to_inittab!(yukkuri_rust);
        pyo3::prepare_freethreaded_python();
    });
}

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

    // Now, verify that the Python side cache has our state
    pyo3::Python::with_gil(|py| {
        let entity_id = entity.index().index();
        let behavior_module = py.import("yukkuri_game.game.systems.behavior_ffi").unwrap();
        let binding = behavior_module.getattr("_ai_states").unwrap();
        let ai_states = binding.downcast::<pyo3::types::PyDict>().unwrap();
        assert!(ai_states.contains(entity_id).unwrap());
        let py_state = ai_states.get_item(entity_id).unwrap();
        py_state.setattr("current_action", "Sleeping").unwrap();
    });

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

        // PythonState restored
        let py_state = world.get::<PythonState>(restored_entity).expect("PythonState missing");
        assert!(!py_state.serialized_blob.is_empty());

        // FFI Cache restored on the Python side for the new entity ID
        pyo3::Python::with_gil(|py| {
            let restored_id = restored_entity.index().index();
            let behavior_module = py.import("yukkuri_game.game.systems.behavior_ffi").unwrap();
            let binding = behavior_module.getattr("_ai_states").unwrap();
            let ai_states = binding.downcast::<pyo3::types::PyDict>().unwrap();
            assert!(ai_states.contains(restored_id).unwrap(), "Python state not restored for new entity ID {}", restored_id);
            let py_state_obj = ai_states.get_item(restored_id).unwrap();
            let action: String = py_state_obj.getattr("current_action").unwrap().extract().unwrap();
            assert_eq!(action, "Sleeping");
        });
    }

    // Clean up temporary save file
    let _ = fs::remove_file(save_path);
}
