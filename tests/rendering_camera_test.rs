use bevy::prelude::*;
use bevy::input::ButtonInput;
use bevy::input::mouse::{MouseWheel, MouseMotion};
use avian2d::prelude::*;
use vibecoded_yukkuri_game::camera::{YukkuriCameraPlugin, MainCamera, CameraController};

fn setup_test_app() -> App {
    let mut app = App::new();
    app.add_plugins(MinimalPlugins);
    app.add_plugins(AssetPlugin::default());
    app.add_plugins(bevy::state::app::StatesPlugin);
    app.init_state::<vibecoded_yukkuri_game::GameState>();
    app.add_plugins(bevy::gizmos::GizmoPlugin);
    app.init_resource::<bevy::gizmos::config::GizmoConfigStore>();
    app.init_asset::<bevy::gizmos::GizmoAsset>();
    app.init_asset::<Mesh>();
    app.init_asset::<bevy::render::mesh::skinning::SkinnedMeshInverseBindposes>();
    
    // Add resources and messages needed by Camera systems
    app.init_resource::<ButtonInput<KeyCode>>();
    app.init_resource::<ButtonInput<MouseButton>>();
    app.add_message::<MouseWheel>();
    app.add_message::<MouseMotion>();
    
    // Insert WorldSettings resource
    app.insert_resource(vibecoded_yukkuri_game::ai::WorldSettings {
        width: 3000.0,
        height: 3000.0,
    });
    
    app.add_plugins(YukkuriCameraPlugin);
    
    // Set NextState to Gameplay immediately so the first update in the test transitions it
    app.world_mut().resource_mut::<NextState<vibecoded_yukkuri_game::GameState>>().set(vibecoded_yukkuri_game::GameState::Gameplay);
    
    app
}

#[test]
fn test_camera_follow() {
    let mut app = setup_test_app();
    
    let camera_id = app.world_mut().spawn((
        Camera2d,
        MainCamera,
        CameraController {
            tracked_entity: None,
            selected_entity: None,
            lerp_speed: 5.0,
            ..Default::default()
        },
        Transform::from_xyz(0.0, 0.0, 0.0),
    )).id();
    
    let target_id = app.world_mut().spawn((
        Transform::from_xyz(100.0, 100.0, 0.0),
        Collider::circle(20.0),
    )).id();
    
    app.world_mut().get_mut::<CameraController>(camera_id).unwrap().tracked_entity = Some(target_id);
    
    // Call update once to initialize time/systems
    app.update();
    
    // Advance virtual time by 0.1s
    app.insert_resource(bevy::time::TimeUpdateStrategy::ManualDuration(std::time::Duration::from_millis(100)));
    app.update();
    
    let camera_transform = app.world().get::<Transform>(camera_id).unwrap();
    // Camera should move from (0,0) towards (100,100)
    assert!(camera_transform.translation.x > 0.0);
    assert!(camera_transform.translation.y > 0.0);
    assert!(camera_transform.translation.x < 100.0);
}

#[test]
fn test_camera_pan_breaks_lock() {
    let mut app = setup_test_app();
    
    let camera_id = app.world_mut().spawn((
        Camera2d,
        MainCamera,
        CameraController {
            tracked_entity: Some(Entity::from_raw_u32(999).unwrap()),
            ..Default::default()
        },
        Transform::from_xyz(0.0, 0.0, 0.0),
        Projection::Orthographic(OrthographicProjection::default_2d()),
    )).id();
    
    // Call update once to initialize time/systems
    app.update();
    
    // Advance virtual time by 0.1s
    app.insert_resource(bevy::time::TimeUpdateStrategy::ManualDuration(std::time::Duration::from_millis(100)));
    
    // Simulate pressing KeyW
    let mut keyboard_input = app.world_mut().resource_mut::<ButtonInput<KeyCode>>();
    keyboard_input.press(KeyCode::KeyW);
    
    app.update();
    
    let controller = app.world().get::<CameraController>(camera_id).unwrap();
    assert!(controller.tracked_entity.is_none(), "Panning should break camera follow lock");
}

#[test]
fn test_camera_selection() {
    let mut app = setup_test_app();
    
    let mut camera = Camera {
        viewport: Some(bevy::camera::Viewport {
            physical_position: UVec2::ZERO,
            physical_size: UVec2::new(800, 600),
            depth: 0.0..1.0,
        }),
        ..Default::default()
    };
    camera.computed.clip_from_view = Mat4::IDENTITY;
    camera.computed.target_info = Some(bevy::camera::RenderTargetInfo {
        physical_size: UVec2::new(800, 600),
        scale_factor: 1.0,
    });
    
    // Spawn camera centered at target world pos
    let camera_transform = Transform::from_xyz(100.0, 100.0, 0.0);
    let camera_global_transform = GlobalTransform::from(camera_transform);
    let camera_id = app.world_mut().spawn((
        Camera2d,
        camera,
        Projection::Orthographic(OrthographicProjection::default_2d()),
        MainCamera,
        CameraController::default(),
        camera_transform,
        camera_global_transform,
    )).id();
    
    let target_transform = Transform::from_xyz(100.0, 100.0, 0.0);
    let target_global_transform = GlobalTransform::from(target_transform);
    let target_id = app.world_mut().spawn((
        target_transform,
        target_global_transform,
        Collider::circle(20.0),
    )).id();
    
    // Spawn Primary Window
    let mut window = Window {
        resolution: bevy::window::WindowResolution::new(800, 600),
        ..Default::default()
    };
    window.set_cursor_position(Some(Vec2::new(400.0, 300.0))); // Center clicks
    app.world_mut().spawn((window, bevy::window::PrimaryWindow));
    
    // Inject Left Click (Press and Release)
    {
        let mut mouse_input = app.world_mut().resource_mut::<ButtonInput<MouseButton>>();
        mouse_input.press(MouseButton::Left);
    }
    app.update();
    
    {
        let mut mouse_input = app.world_mut().resource_mut::<ButtonInput<MouseButton>>();
        mouse_input.release(MouseButton::Left);
    }
    app.update();
    
    let controller = app.world().get::<CameraController>(camera_id).unwrap();
    assert_eq!(controller.selected_entity, Some(target_id));
    assert_eq!(controller.tracked_entity, Some(target_id));
}

#[test]
fn test_camera_refocus() {
    let mut app = setup_test_app();
    
    let target_id = app.world_mut().spawn(Transform::default()).id();
    let camera_id = app.world_mut().spawn((
        Camera2d,
        MainCamera,
        CameraController {
            selected_entity: Some(target_id),
            tracked_entity: None,
            ..Default::default()
        },
        Transform::from_xyz(0.0, 0.0, 0.0),
    )).id();
    
    let mut keyboard_input = app.world_mut().resource_mut::<ButtonInput<KeyCode>>();
    keyboard_input.press(KeyCode::KeyF);
    
    app.update();
    
    let controller = app.world().get::<CameraController>(camera_id).unwrap();
    assert_eq!(controller.tracked_entity, Some(target_id), "Pressing F should refocus on the selected entity");
}

#[test]
fn test_camera_overshoot_large_dt() {
    let mut app = setup_test_app();
    
    let camera_id = app.world_mut().spawn((
        Camera2d,
        MainCamera,
        CameraController {
            tracked_entity: None,
            selected_entity: None,
            lerp_speed: 5.0, // lerp_speed * dt = 5.0 * 0.5 = 2.5 > 1.0
            ..Default::default()
        },
        Transform::from_xyz(0.0, 0.0, 0.0),
    )).id();
    
    let target_id = app.world_mut().spawn((
        Transform::from_xyz(100.0, 100.0, 0.0),
        Collider::circle(20.0),
    )).id();
    
    app.world_mut().get_mut::<CameraController>(camera_id).unwrap().tracked_entity = Some(target_id);
    
    app.update();
    
    // Set a large dt of 500ms
    app.insert_resource(bevy::time::TimeUpdateStrategy::ManualDuration(std::time::Duration::from_millis(500)));
    app.update();
    
    let camera_transform = app.world().get::<Transform>(camera_id).unwrap();
    // With lerp factor clamped to 1.0, it should not overshoot the target.
    assert!(camera_transform.translation.x <= 100.0, "Camera should not overshoot target position");
    assert_eq!(camera_transform.translation.x, 100.0);
}

#[test]
fn test_camera_negative_zoom_scale() {
    let mut app = setup_test_app();
    
    let camera_id = app.world_mut().spawn((
        Camera2d,
        MainCamera,
        CameraController {
            target_zoom: 1.0,
            zoom_speed: 8.0, // zoom_speed * dt = 8.0 * 0.5 = 4.0
            ..Default::default()
        },
        Transform::from_xyz(0.0, 0.0, 0.0),
        Projection::Orthographic(OrthographicProjection {
            scale: 1.0,
            ..OrthographicProjection::default_2d()
        }),
    )).id();
    
    // Set target_zoom to 0.1 (below minimum zoom 0.5)
    app.world_mut().get_mut::<CameraController>(camera_id).unwrap().target_zoom = 0.1;
    
    app.update();
    
    // Advance virtual time by 500ms
    app.insert_resource(bevy::time::TimeUpdateStrategy::ManualDuration(std::time::Duration::from_millis(500)));
    app.update();
    
    let projection = app.world().get::<Projection>(camera_id).unwrap();
    if let Projection::Orthographic(ref ortho) = *projection {
        assert!(ortho.scale >= 0.5, "Scale should be clamped and not become negative");
        assert_eq!(ortho.scale, 0.5);
    } else {
        panic!("Expected orthographic projection");
    }
}

#[test]
fn test_camera_pan_beyond_boundaries() {
    let mut app = setup_test_app();
    
    let camera_id = app.world_mut().spawn((
        Camera2d,
        MainCamera,
        CameraController::default(),
        Transform::from_xyz(0.0, 0.0, 0.0),
        Projection::Orthographic(OrthographicProjection::default_2d()),
    )).id();
    
    app.update();
    
    // Simulate panning left (A key)
    let mut keyboard_input = app.world_mut().resource_mut::<ButtonInput<KeyCode>>();
    keyboard_input.press(KeyCode::KeyA);
    
    // Advance virtual time by 1000ms
    app.insert_resource(bevy::time::TimeUpdateStrategy::ManualDuration(std::time::Duration::from_millis(1000)));
    app.update();
    
    let camera_transform = app.world().get::<Transform>(camera_id).unwrap();
    // Clamping to [0, 3000] boundaries should keep camera at 0.0
    assert_eq!(camera_transform.translation.x, 0.0, "Camera position should clamp to boundaries");
}

#[test]
fn test_camera_panic_on_negative_world_bounds() {
    let mut app = setup_test_app();
    app.insert_resource(vibecoded_yukkuri_game::ai::WorldSettings {
        width: -500.0,
        height: -500.0,
    });
    
    let camera_id = app.world_mut().spawn((
        Camera2d,
        MainCamera,
        CameraController::default(),
        Transform::from_xyz(0.0, 0.0, 0.0),
    )).id();
    
    let target_id = app.world_mut().spawn((
        Transform::from_xyz(100.0, 100.0, 0.0),
        Collider::circle(20.0),
    )).id();
    
    app.world_mut().get_mut::<CameraController>(camera_id).unwrap().tracked_entity = Some(target_id);
    
    // This should not panic now and clamp bounds to 0.0
    app.update();
    
    let camera_transform = app.world().get::<Transform>(camera_id).unwrap();
    assert_eq!(camera_transform.translation.x, 0.0);
    assert_eq!(camera_transform.translation.y, 0.0);
}

#[test]
fn test_camera_nan_target_position() {
    let mut app = setup_test_app();
    
    let camera_id = app.world_mut().spawn((
        Camera2d,
        MainCamera,
        CameraController::default(),
        Transform::from_xyz(0.0, 0.0, 0.0),
    )).id();
    
    let target_id = app.world_mut().spawn((
        Transform::from_xyz(f32::NAN, 100.0, 0.0),
        Collider::circle(20.0),
    )).id();
    
    app.world_mut().get_mut::<CameraController>(camera_id).unwrap().tracked_entity = Some(target_id);
    
    app.update();
    
    let camera_transform = app.world().get::<Transform>(camera_id).unwrap();
    assert!(!camera_transform.translation.x.is_nan(), "Camera position should not become NaN when tracking NaN target");
    assert_eq!(camera_transform.translation.x, 0.0);
}

#[test]
fn test_camera_update_clears_tracking_on_missing_entity() {
    let mut app = setup_test_app();
    
    let camera_id = app.world_mut().spawn((
        Camera2d,
        MainCamera,
        CameraController::default(),
        Transform::from_xyz(0.0, 0.0, 0.0),
    )).id();
    
    let target_id = app.world_mut().spawn((
        Transform::from_xyz(100.0, 100.0, 0.0),
        Collider::circle(20.0),
    )).id();
    
    app.world_mut().get_mut::<CameraController>(camera_id).unwrap().tracked_entity = Some(target_id);
    
    app.update();
    
    // Despawn target
    app.world_mut().despawn(target_id);
    
    app.update();
    
    let controller = app.world().get::<CameraController>(camera_id).unwrap();
    assert!(controller.tracked_entity.is_none(), "Tracked entity should clear when target is despawned");
}

