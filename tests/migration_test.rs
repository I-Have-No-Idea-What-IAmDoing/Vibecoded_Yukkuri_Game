use bevy::prelude::*;
use avian2d::prelude::*;
use vibecoded_yukkuri_game::ai::{
    yukkuri_rust, AIPlugin, AIState, EntityRegistry, Needs, StableId, SteeringConfig,
    VisibleTargets, MoveTarget,
};
use vibecoded_yukkuri_game::render::{TextureAtlasRegistry, YukkuriTypeRegistry};
use vibecoded_yukkuri_game::prefabs::{load_prefab, spawn_yukkuri_prefab};

#[test]
fn test_integration_migration() {
    // 1. Prepare Python and FFI module registration
    pyo3::append_to_inittab!(yukkuri_rust);
    pyo3::prepare_freethreaded_python();

    // 2. Initialize headless Bevy app
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

    // 3. Load reimu.toml prefab file
    let prefab = load_prefab("data/prefabs/reimu.toml")
        .expect("Failed to load reimu.toml prefab");

    // 4. Spawn Yukkuri entity from prefab via a Bevy startup system
    let position = Vec2::new(100.0, 100.0);
    let spawned_entity = std::sync::Arc::new(std::sync::Mutex::new(None));
    let spawned_entity_clone = spawned_entity.clone();
    let prefab_clone = prefab.clone();

    app.add_systems(PostStartup, move |mut commands: Commands, asset_server: Res<AssetServer>, atlas_registry: Res<TextureAtlasRegistry>, type_registry: Res<YukkuriTypeRegistry>| {
        let entity = spawn_yukkuri_prefab(
            &mut commands,
            &prefab_clone,
            position,
            &asset_server,
            &atlas_registry,
            &type_registry,
        );
        *spawned_entity_clone.lock().unwrap() = Some(entity);
    });

    // Run the app update once to trigger Startup systems and apply Commands
    app.update();

    // Bind MutexGuard into a local before unwrapping to avoid lifetime issues.
    let entity = {
        let guard = spawned_entity.lock().unwrap();
        guard.expect("Failed to spawn entity")
    };

    // 5. Verify all expected components were inserted by spawn_yukkuri_prefab
    {
        let world = app.world_mut();

        // Physics components
        assert!(world.get::<Transform>(entity).is_some(), "Transform component missing");
        assert!(world.get::<RigidBody>(entity).is_some(), "RigidBody component missing");
        assert!(world.get::<Collider>(entity).is_some(), "Collider component missing");
        assert!(world.get::<Mass>(entity).is_some(), "Mass component missing");
        assert!(world.get::<Friction>(entity).is_some(), "Friction component missing");
        assert!(world.get::<Restitution>(entity).is_some(), "Restitution component missing");

        // StableId must encode the entity's own generational bits.
        let stable = world.get::<StableId>(entity)
            .expect("StableId component missing — entity was not stamped at spawn");
        assert_eq!(
            stable.0,
            entity.to_bits(),
            "StableId does not match entity bits"
        );

        // SteeringConfig must be present and sourced from TOML.
        let cfg = world.get::<SteeringConfig>(entity)
            .expect("SteeringConfig missing — not inserted by spawn_yukkuri_prefab");
        assert_eq!(cfg.max_speed, 150.0, "SteeringConfig.max_speed mismatch");
        assert_eq!(cfg.perception_radius, 300.0, "SteeringConfig.perception_radius mismatch");

        // Set hunger high so the Eat goal is active.
        if let Some(mut needs) = world.get_mut::<Needs>(entity) {
            needs.hunger = 80.0;
        }
        if let Some(mut ai_state) = world.get_mut::<AIState>(entity) {
            ai_state.current_action = "Eat".to_string();
        }

        // NOTE: We no longer manually inject a fake food TargetInfo here.
        // `populate_visible_targets_system` now owns VisibleTargets and clears it every
        // frame, so any manual insertion would be overwritten before the behavior tree ticks.
        //
        // Triggering the full Eat→MoveTo path requires a real food entity spawned in ECS
        // within perception range.  Food entities are not yet ported (deferred work); that
        // end-to-end test lives in a future `test_eat_goal_triggers_move_to` test.
    }

    // 6. Update Bevy app again to tick all AI systems (should not panic).
    app.update();

    // 7. Verify the AI pipeline ran correctly.
    let world = app.world();

    // EntityRegistry must map the entity's raw index → live Entity handle so that
    // apply_ai_commands can safely round-trip the Python-facing raw index.
    let registry = world.resource::<EntityRegistry>();
    let raw_index = entity.index().index();
    assert_eq!(
        registry.0.get(&raw_index),
        Some(&entity),
        "EntityRegistry did not map entity index {} -> Entity {:?}",
        raw_index,
        entity,
    );

    // VisibleTargets must be present (empty: only one entity exists, nothing in range).
    let visible = world.get::<VisibleTargets>(entity)
        .expect("VisibleTargets component missing after AI tick");
    assert!(
        visible.targets.is_empty(),
        "Expected empty VisibleTargets with only one entity in world; got {} targets",
        visible.targets.len()
    );

    // MoveTarget must NOT be present: behavior tree saw no food → no MoveTo issued.
    assert!(
        world.get::<MoveTarget>(entity).is_none(),
        "MoveTarget should not be inserted when VisibleTargets is empty (no food visible)"
    );
}
