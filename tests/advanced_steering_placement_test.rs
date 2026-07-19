use bevy::prelude::*;
use avian2d::prelude::*;
use bevy::ecs::system::RunSystemOnce;

use vibecoded_yukkuri_game::ai::{SteeringConfig, BaseColliderRadius, Flight, MoveTarget, StuckDetector};
use vibecoded_yukkuri_game::simulation::kinematic_controller::KinematicVelocity;
use vibecoded_yukkuri_game::ai::persistence::Economy;
use vibecoded_yukkuri_game::render::{YukkuriRenderPlugin, YukkuriSprite, YukkuriShadow};
use vibecoded_yukkuri_game::ui::placement::{PlacementState, PlacementGhost};
use vibecoded_yukkuri_game::simulation::inventory::{ItemRegistry, ItemConfig, ItemStats};

#[test]
fn test_shadow_scaling_with_altitude() {
    let mut app = App::new();
    app.add_plugins(MinimalPlugins);
    app.add_plugins(bevy::asset::AssetPlugin::default());
    app.add_plugins(YukkuriRenderPlugin);

    // Spawn child sprite
    let child_sprite = app.world_mut().spawn((
        Transform::from_xyz(0.0, 0.0, 0.1),
        Visibility::default(),
    )).id();

    // Spawn parent entity with YukkuriShadow and BaseColliderRadius
    let parent = app.world_mut().spawn((
        Transform::default(),
        BaseColliderRadius(20.0),
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
            sprite_entity: Some(child_sprite),
        },
        Flight {
            altitude: 0.0,
            max_altitude: 100.0,
            ..default()
        },
        YukkuriShadow,
    )).id();

    // Update once to insert the shadow Sprite component
    app.update();

    // Verify Sprite component was inserted on parent
    let (size_ground, alpha_ground) = {
        let sprite = app.world().get::<Sprite>(parent).expect("Shadow Sprite not inserted");
        (sprite.custom_size.expect("Size not set"), sprite.color.alpha())
    };

    // Shift child sprite up (simulating altitude + bobbing)
    app.world_mut().get_mut::<Transform>(child_sprite).unwrap().translation.y = 50.0;

    // Update again
    app.update();

    // Verify shadow size and alpha shrunk
    let sprite_alt = app.world().get::<Sprite>(parent).unwrap();
    let size_alt = sprite_alt.custom_size.unwrap();
    assert!(size_alt.x < size_ground.x, "Shadow did not shrink with altitude");
    assert!(sprite_alt.color.alpha() < alpha_ground, "Shadow did not fade with altitude");
}

#[test]
fn test_steering_forces_separation_and_arrival() {
    let mut app = App::new();
    app.add_plugins(MinimalPlugins);
    app.add_plugins(PhysicsPlugins::default());

    // Initialize Avian diagnostic resources required by physics systems
    app.init_resource::<avian2d::collider_tree::ColliderTreeDiagnostics>();
    app.init_resource::<avian2d::spatial_query::SpatialQueryDiagnostics>();
    app.init_resource::<avian2d::dynamics::solver::SolverDiagnostics>();
    app.init_resource::<avian2d::collision::CollisionDiagnostics>();

    // Register only the steering system and its required types/resources
    app.register_type::<SteeringConfig>();
    app.register_type::<StuckDetector>();
    app.add_systems(Update, vibecoded_yukkuri_game::ai::move_target_steering_system);

    // First update to register and initialize time
    app.update();

    app.insert_resource(bevy::time::TimeUpdateStrategy::ManualDuration(std::time::Duration::from_secs_f32(0.1)));

    // Spawn Entity A (moving to target)
    let entity_a = app.world_mut().spawn((
        Transform::from_xyz(0.0, 0.0, 0.0),
        LinearVelocity::default(),
        KinematicVelocity::default(),
        BaseColliderRadius(15.0),
        SteeringConfig {
            max_speed: 100.0,
            max_force: 50.0,
            arrival_radius: 50.0,
            perception_radius: 100.0,
        },
        MoveTarget {
            position: Vec2::new(100.0, 0.0),
            acceptance_radius: 5.0,
        },
    )).id();

    // Spawn Entity B close to A to trigger separation force
    let _entity_b = app.world_mut().spawn((
        Transform::from_xyz(10.0, 5.0, 0.0),
        LinearVelocity::default(),
        KinematicVelocity::default(),
        BaseColliderRadius(15.0),
        SteeringConfig::default(),
    )).id();

    // Update physics and steering systems
    app.update();
    app.update();

    // Verify Entity A has non-zero velocity directing it towards target but influenced by separation
    let vel_a = app.world().get::<KinematicVelocity>(entity_a).unwrap().target;
    assert!(vel_a.x > 0.0, "Entity A is not moving forward");
    // Since B is at (10, 5) relative to A (0, 0), separation should push A in negative Y
    assert!(vel_a.y < 0.0, "Separation force did not push Entity A away from Entity B");

    // Move Entity A close to the target to verify arrival deceleration
    app.world_mut().get_mut::<Transform>(entity_a).unwrap().translation.x = 90.0; // 10px away, which is < arrival_radius (50px)
    app.update();
    app.update();

    let vel_a_arrival = app.world().get::<KinematicVelocity>(entity_a).unwrap().target;
    assert!(vel_a_arrival.length() < 100.0, "Entity A did not slow down near target");
}

#[test]
fn test_item_placement_system() {
    let mut app = App::new();
    app.add_plugins(MinimalPlugins);
    app.add_plugins(bevy::input::InputPlugin);
    app.add_plugins(bevy::asset::AssetPlugin::default());

    // Register UI & Inventory systems/resources
    app.init_resource::<PlacementState>();
    app.init_resource::<ItemRegistry>();
    app.insert_resource(Economy { money: 200 });
    app.add_message::<vibecoded_yukkuri_game::audio::PlaySoundEvent>();
    app.init_asset::<Image>();

    // Mock ItemRegistry item
    let mut registry = app.world_mut().resource_mut::<ItemRegistry>();
    registry.items.insert("cookie".to_string(), ItemConfig {
        name: "Cookie".to_string(),
        image: "cookie.png".to_string(),
        width: 32,
        height: 32,
        cost: 10,
        nutrition: Some(20.0),
        fun: Some(10.0),
        comfort: None,
        quality: None,
        is_portable: true,
        obstacle_type: None,
        light_radius: None,
        light_color: None,
        light_intensity: None,
    });

    // Spawn a camera (needed for placement raycasts)
    app.world_mut().spawn((
        Camera2d,
        Transform::default(),
        vibecoded_yukkuri_game::camera::CameraController::default(),
    ));

    // Register our update system
    app.add_systems(Update, vibecoded_yukkuri_game::ui::placement::update_placement_system);

    // 1. Enter placement mode
    {
        let mut state = app.world_mut().resource_mut::<PlacementState>();
        state.active = true;
        state.current_item_id = "cookie".to_string();
        state.cost = 10;
    }

    let _ = app.world_mut().run_system_once(vibecoded_yukkuri_game::ui::placement::update_placement_system);

    // Verify placement ghost entity was created
    let ghost_exists = {
        let mut query = app.world_mut().query::<&PlacementGhost>();
        query.iter(app.world()).next().is_some()
    };
    assert!(ghost_exists, "Placement ghost was not spawned");

    // 2. Press Left Mouse Button to confirm placement
    app.world_mut().resource_mut::<ButtonInput<MouseButton>>().press(MouseButton::Left);
    let _ = app.world_mut().run_system_once(vibecoded_yukkuri_game::ui::placement::update_placement_system);

    // Verify ghost is despawned, placement is inactive, economy money is deducted
    let state = app.world().resource::<PlacementState>();
    assert!(!state.active, "Placement state did not deactivate");
    assert_eq!(state.ghost_entity, None, "Ghost entity not cleared from state");

    let economy = app.world().resource::<Economy>();
    assert_eq!(economy.money, 190, "Funds were not deducted");

    // Verify item entity was spawned
    let item_spawned = {
        let mut query = app.world_mut().query::<&ItemStats>();
        query.iter(app.world()).next().is_some()
    };
    assert!(item_spawned, "Physical item was not spawned in the world");
}
