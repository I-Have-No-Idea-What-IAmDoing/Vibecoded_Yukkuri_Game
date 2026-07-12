use bevy::prelude::*;
use avian2d::prelude::*;
use std::collections::HashMap;
use vibecoded_yukkuri_game::ai::{AIPlugin, AIState, Flight, PoppedCommands};
use vibecoded_yukkuri_game::ai::commands::{Command, CommandType};
use vibecoded_yukkuri_game::prefabs::{load_prefab, spawn_yukkuri_prefab};
use vibecoded_yukkuri_game::render::{
    AnimationDefConfig, YukkuriTypeConfig, YukkuriTypeRegistry, TextureAtlasRegistry,
    YukkuriRenderPlugin, YukkuriSprite, Animator, AnimationEvent
};

use vibecoded_yukkuri_game::ai::yukkuri_rust;

#[test]
fn test_rendering_animation_systems() {
    pyo3::append_to_inittab!(yukkuri_rust);
    pyo3::prepare_freethreaded_python();

    let mut app = App::new();
    app.add_plugins(MinimalPlugins);
    app.add_plugins(bevy::input::InputPlugin);
    app.add_plugins(bevy::asset::AssetPlugin::default());
    app.add_plugins(PhysicsPlugins::default());
    app.add_plugins(AIPlugin);
    app.add_plugins(vibecoded_yukkuri_game::simulation::SimulationPlugin);
    app.add_plugins(YukkuriRenderPlugin);

    // Initialize Avian diagnostic resources required by physics systems
    app.init_resource::<avian2d::collider_tree::ColliderTreeDiagnostics>();
    app.init_resource::<avian2d::spatial_query::SpatialQueryDiagnostics>();
    app.init_resource::<avian2d::dynamics::solver::SolverDiagnostics>();
    app.init_resource::<avian2d::collision::CollisionDiagnostics>();

    app.insert_resource(bevy::time::TimeUpdateStrategy::ManualDuration(std::time::Duration::ZERO));

    // 1. Manually insert mock animation configurations for a "mock_yukkuri" type into the registry
    let mut animations = HashMap::new();
    animations.insert("idle".to_string(), AnimationDefConfig {
        frames: vec![0],
        frame_duration: 0.1,
        loop_anim: true,
        ping_pong: false,
        events: HashMap::new(),
        image: None,
        width: None,
        height: None,
    });
    animations.insert("eat".to_string(), AnimationDefConfig {
        frames: vec![0, 1, 2],
        frame_duration: 0.1,
        loop_anim: true,
        ping_pong: false,
        events: HashMap::new(),
        image: None,
        width: None,
        height: None,
    });
    animations.insert("fly".to_string(), AnimationDefConfig {
        frames: vec![3, 4],
        frame_duration: 0.1,
        loop_anim: true,
        ping_pong: false,
        events: HashMap::new(),
        image: None,
        width: None,
        height: None,
    });
    animations.insert("swoop".to_string(), AnimationDefConfig {
        frames: vec![5],
        frame_duration: 0.1,
        loop_anim: true,
        ping_pong: false,
        events: HashMap::new(),
        image: None,
        width: None,
        height: None,
    });
    animations.insert("jump".to_string(), AnimationDefConfig {
        frames: vec![6],
        frame_duration: 0.1,
        loop_anim: false,
        ping_pong: false,
        events: {
            let mut evs = HashMap::new();
            evs.insert(0, "jump_started".to_string());
            evs
        },
        image: None,
        width: None,
        height: None,
    });
    animations.insert("sleep".to_string(), AnimationDefConfig {
        frames: vec![7],
        frame_duration: 0.1,
        loop_anim: true,
        ping_pong: false,
        events: HashMap::new(),
        image: None,
        width: None,
        height: None,
    });

    let mock_config = YukkuriTypeConfig {
        name: "Mock Yukkuri".to_string(),
        image: "reimu.png".to_string(), // Uses an existing file
        width: 64,
        height: 64,
        max_health: 100.0,
        base_happiness: 50.0,
        cost: 100,
        is_prey: Some(true),
        can_fly: Some(true),
        max_altitude: Some(80.0),
        fly_stamina: Some(100.0),
        is_predator: None,
        prey_tags: None,
        prey_sense_radius: None,
        aggression: None,
        dps: None,
        animations,
        frame_count: 1,
        frame_duration: 0.1,
        loop_anim: true,
    };

    // 2. Load a prefab configuration, overriding the type_id to our mock
    let mut prefab = load_prefab("data/prefabs/reimu.toml")
        .expect("Failed to load prefab");
    prefab.prefab.type_id = "mock_yukkuri".to_string();

    let spawned_entity = std::sync::Arc::new(std::sync::Mutex::new(None));
    let spawned_entity_clone = spawned_entity.clone();
    let prefab_clone = prefab.clone();
    let mock_config_clone = mock_config.clone();

    app.add_systems(PostStartup, move |
        mut commands: Commands,
        asset_server: Res<AssetServer>,
        mut atlas_registry: ResMut<TextureAtlasRegistry>,
        mut type_registry: ResMut<YukkuriTypeRegistry>
    | {
        // Manually insert mock animation configurations for "mock_yukkuri"
        type_registry.types.insert("mock_yukkuri".to_string(), mock_config_clone.clone());

        let handle_img = Handle::<Image>::default();
        let handle_layout = Handle::<TextureAtlasLayout>::default();
        atlas_registry.images.insert("reimu.png".to_string(), handle_img);
        atlas_registry.layouts.insert(("reimu.png".to_string(), 64, 64), handle_layout);

        let entity = spawn_yukkuri_prefab(
            &mut commands,
            &prefab_clone,
            Vec2::new(0.0, 0.0),
            &asset_server,
            &atlas_registry,
            &type_registry,
        );
        *spawned_entity_clone.lock().unwrap() = Some(entity);
    });

    // Run startup systems
    app.update();

    let entity = spawned_entity.lock().unwrap().expect("Failed to spawn entity");

    // Test 1: Initial Action Sync (AIState::current_action = "Eat" -> plays "eat")
    {
        let mut ai_state = app.world_mut().get_mut::<AIState>(entity).unwrap();
        ai_state.current_action = "Eat".to_string();
    }

    app.update();

    {
        let animator = app.world().get::<Animator>(entity).unwrap();
        assert_eq!(animator.current_animation, "eat");
        assert_eq!(animator.current_frame_index, 0);
        let sprite = app.world().get::<YukkuriSprite>(entity).unwrap();
        assert_eq!(sprite.current_frame, 0); // frame index 0 of eat is 0
    }

    // Test 2: Flight State Override (FlightState = 2 -> plays "fly")
    {
        let mut flight = app.world_mut().get_mut::<Flight>(entity).unwrap();
        flight.flight_state = 2; // Flying
    }

    app.update();

    {
        let animator = app.world().get::<Animator>(entity).unwrap();
        assert_eq!(animator.current_animation, "fly");
        let sprite = app.world().get::<YukkuriSprite>(entity).unwrap();
        assert_eq!(sprite.current_frame, 3); // frame index 0 of fly is 3
    }

    // Test 3: Swoop Flight Override (FlightState = 5 -> plays "swoop")
    {
        let mut flight = app.world_mut().get_mut::<Flight>(entity).unwrap();
        flight.flight_state = 5; // Swooping
        flight.altitude = 50.0;
    }

    app.update();

    {
        let animator = app.world().get::<Animator>(entity).unwrap();
        assert_eq!(animator.current_animation, "swoop");
        let sprite = app.world().get::<YukkuriSprite>(entity).unwrap();
        assert_eq!(sprite.current_frame, 5); // frame index 0 of swoop is 5
    }

    // Test 4: FFI PlayAnimation command (dispatches "jump" -> manual_override = true, locks ai_action_at_override)
    {
        // Ground the entity first
        let mut flight = app.world_mut().get_mut::<Flight>(entity).unwrap();
        flight.flight_state = 0;
        
        let mut popped = app.world_mut().resource_mut::<PoppedCommands>();
        let mut payload = HashMap::new();
        payload.insert("animation_name".to_string(), "jump".to_string());
        popped.0.push(Command {
            cmd_type: CommandType::PlayAnimation,
            entity_id: entity.index().index(),
            payload,
        });
    }

    // Run update to process commands and sync animations
    app.update();

    {
        let animator = app.world().get::<Animator>(entity).unwrap();
        assert_eq!(animator.current_animation, "jump");
        assert!(animator.manual_override);
        assert_eq!(animator.ai_action_at_override, "Eat"); // Action was Eat at override
    }

    // Test 5: Override Protection (flight state changes to Flying, but manual_override is true, so "jump" remains)
    {
        let mut flight = app.world_mut().get_mut::<Flight>(entity).unwrap();
        flight.flight_state = 2; // Flying
    }

    app.update();

    {
        let animator = app.world().get::<Animator>(entity).unwrap();
        assert_eq!(animator.current_animation, "jump"); // Remains "jump" because manual_override is true
        assert!(animator.manual_override);
    }

    // Test 6: Override Release (AIState::current_action changes to "Sleep" -> manual_override releases -> switches to "sleep")
    {
        // Set flight to 0 (grounded) to avoid flight override taking over
        let mut flight = app.world_mut().get_mut::<Flight>(entity).unwrap();
        flight.flight_state = 0;

        let mut ai_state = app.world_mut().get_mut::<AIState>(entity).unwrap();
        ai_state.current_action = "Sleep".to_string();
    }

    app.update();

    {
        let animator = app.world().get::<Animator>(entity).unwrap();
        assert_eq!(animator.current_animation, "sleep");
        assert!(!animator.manual_override); // released
    }

    // Test 7: Frame events are emitted
    let mut cursor = {
        let messages = app.world().resource::<Messages<AnimationEvent>>();
        messages.get_cursor()
    };

    {
        // Let's manually set active animation back to "jump" (frame 0 triggers event "jump_started")
        let mut popped = app.world_mut().resource_mut::<PoppedCommands>();
        let mut payload = HashMap::new();
        payload.insert("animation_name".to_string(), "jump".to_string());
        popped.0.push(Command {
            cmd_type: CommandType::PlayAnimation,
            entity_id: entity.index().index(),
            payload,
        });
    }

    app.update();

    // Advance virtual time by 0.15s to trigger frame 0's timer rollover
    app.insert_resource(bevy::time::TimeUpdateStrategy::ManualDuration(std::time::Duration::from_secs_f32(0.15)));

    app.update();

    app.insert_resource(bevy::time::TimeUpdateStrategy::ManualDuration(std::time::Duration::ZERO));

    // Read the AnimationEvent message queue
    {
        let messages = app.world().resource::<Messages<AnimationEvent>>();
        let events: Vec<AnimationEvent> = cursor.read(messages).cloned().collect();
        assert!(!events.is_empty(), "No AnimationEvent was emitted");
        assert_eq!(events[0].event_name, "jump_started");
        assert_eq!(events[0].animation_name, "jump");
    }
}
