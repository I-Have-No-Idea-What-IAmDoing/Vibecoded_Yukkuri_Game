# Camera Controller & Automated Integration Tests Design Analysis

This document outlines the architecture, component design, system logic, and test plan for the Bevy 0.19 native Camera Controller System (Milestone 4 / R3) and the Automated Integration Tests (Milestone 5 / R4/R5).

---

## 1. Camera Controller System (Milestone 4 / R3)

The Camera Controller System manages the 2D game camera, facilitating smooth entity tracking (lerp-following), zoom control (via mouse scroll and page keys), panning (keyboard and mouse drag), selection (using physics bounds), and re-focusing.

### 1.1 Data Structures & Components

#### `MainCamera` Tag Component
A simple marker component to identify the primary game camera.
```rust
#[derive(Component, Debug, Default)]
pub struct MainCamera;
```

#### `CameraController` Component
Attached to the camera entity to maintain tracking, selection, panning, and zoom state.
```rust
#[derive(Component, Debug)]
pub struct CameraController {
    /// The entity currently being tracked/followed by the camera.
    pub tracked_entity: Option<Entity>,
    /// The entity currently selected (may remain selected even if tracking lock is broken).
    pub selected_entity: Option<Entity>,
    /// Smooth follow lerp speed multiplier.
    pub lerp_speed: f32,
    /// Target projection scale for zoom smoothing.
    pub target_zoom: f32,
    /// Minimum zoom scale (closest zoom-in).
    pub min_zoom: f32,
    /// Maximum zoom scale (furthest zoom-out).
    pub max_zoom: f32,
    /// Zoom speed multiplier.
    pub zoom_speed: f32,
}

impl Default for CameraController {
    fn default() -> Self {
        Self {
            tracked_entity: None,
            selected_entity: None,
            lerp_speed: 5.0,
            target_zoom: 1.0,
            min_zoom: 0.25,
            max_zoom: 4.0,
            zoom_speed: 8.0,
        }
    }
}
```

---

### 1.2 Systems Architecture

#### A. Setup System (`setup_camera`)
Spawns the 2D orthographic camera with `MainCamera` and `CameraController` components, centered in the world.
```rust
pub fn setup_camera(mut commands: Commands, world_settings: Res<WorldSettings>) {
    let center_x = world_settings.width / 2.0;
    let center_y = world_settings.height / 2.0;
    
    commands.spawn((
        Camera2d::default(),
        MainCamera,
        CameraController::default(),
        Transform::from_xyz(center_x, center_y, 0.0),
    ));
}
```

#### B. Smooth Follow System (`camera_follow_system`)
Lerps the camera's translation towards the tracked entity's position.
```rust
pub fn camera_follow_system(
    time: Res<Time>,
    mut camera_query: Query<(&mut Transform, &CameraController), With<MainCamera>>,
    target_query: Query<&Transform, (With<Collider>, Without<MainCamera>)>,
    world_settings: Res<WorldSettings>,
) {
    let dt = time.delta_secs();
    if let Ok((mut camera_transform, controller)) = camera_query.get_single_mut() {
        if let Some(tracked) = controller.tracked_entity {
            if let Ok(target_transform) = target_query.get(tracked) {
                let target_pos = target_transform.translation.truncate();
                let camera_pos = camera_transform.translation.truncate();
                
                // Lerp formula: camera = camera + (target - camera) * 5.0 * dt
                let new_pos = camera_pos + (target_pos - camera_pos) * controller.lerp_speed * dt;
                
                camera_transform.translation.x = new_pos.x;
                camera_transform.translation.y = new_pos.y;
                
                // Keep the camera center clamped within the world limits
                camera_transform.translation.x = camera_transform.translation.x.clamp(0.0, world_settings.width);
                camera_transform.translation.y = camera_transform.translation.y.clamp(0.0, world_settings.height);
            }
        }
    }
}
```

#### C. Zoom System (`camera_zoom_system`)
Adjusts the target zoom based on mouse scroll wheel or PageUp/PageDown key presses, then smoothly interpolates `OrthographicProjection.scale`.
```rust
use bevy::input::mouse::{MouseWheel, MouseScrollUnit};

pub fn camera_zoom_system(
    mut mouse_wheel: EventReader<MouseWheel>,
    keyboard_input: Res<ButtonInput<KeyCode>>,
    time: Res<Time>,
    mut query: Query<(&mut OrthographicProjection, &mut CameraController), With<MainCamera>>,
) {
    let mut zoom_delta = 0.0;
    
    // Mouse Scroll Wheel input
    for event in mouse_wheel.read() {
        let factor = match event.unit {
            MouseScrollUnit::Line => event.y,
            MouseScrollUnit::Pixel => event.y * 0.05,
        };
        zoom_delta -= factor * 0.15;
    }
    
    // Keyboard inputs
    let dt = time.delta_secs();
    if keyboard_input.pressed(KeyCode::PageUp) {
        zoom_delta -= 1.0 * dt;
    }
    if keyboard_input.pressed(KeyCode::PageDown) {
        zoom_delta += 1.0 * dt;
    }
    
    if let Ok((mut projection, mut controller)) = query.get_single_mut() {
        if zoom_delta != 0.0 {
            controller.target_zoom = (controller.target_zoom + zoom_delta).clamp(controller.min_zoom, controller.max_zoom);
        }
        
        // Smoothly interpolate actual projection scale to target zoom scale
        projection.scale += (controller.target_zoom - projection.scale) * controller.zoom_speed * dt;
    }
}
```

#### D. Panning & Lock-Break System (`camera_pan_system`)
Pans the camera with WASD / Arrow keys or Middle-Mouse Drag, instantly releasing the tracking lock (`tracked_entity = None`).
```rust
use bevy::input::mouse::MouseMotion;

pub fn camera_pan_system(
    keyboard_input: Res<ButtonInput<KeyCode>>,
    mouse_input: Res<ButtonInput<MouseButton>>,
    mut mouse_motion: EventReader<MouseMotion>,
    time: Res<Time>,
    mut query: Query<(&mut Transform, &mut CameraController, &OrthographicProjection), With<MainCamera>>,
) {
    let mut pan_dir = Vec2::ZERO;
    
    // Key inputs (WASD & Arrow Keys)
    if keyboard_input.pressed(KeyCode::KeyW) || keyboard_input.pressed(KeyCode::ArrowUp) {
        pan_dir.y += 1.0;
    }
    if keyboard_input.pressed(KeyCode::KeyS) || keyboard_input.pressed(KeyCode::ArrowDown) {
        pan_dir.y -= 1.0;
    }
    if keyboard_input.pressed(KeyCode::KeyA) || keyboard_input.pressed(KeyCode::ArrowLeft) {
        pan_dir.x -= 1.0;
    }
    if keyboard_input.pressed(KeyCode::KeyD) || keyboard_input.pressed(KeyCode::ArrowRight) {
        pan_dir.x += 1.0;
    }
    
    // Mouse drag input (Middle Button)
    let mut drag_delta = Vec2::ZERO;
    let mut is_dragging = false;
    if mouse_input.pressed(MouseButton::Middle) {
        for event in mouse_motion.read() {
            // Invert delta because dragging moves the camera opposite to mouse motion.
            // Motion Y is down-positive, World Y is up-positive.
            drag_delta.x -= event.delta.x;
            drag_delta.y += event.delta.y;
            is_dragging = true;
        }
    }
    
    if let Ok((mut transform, mut controller, projection)) = query.get_single_mut() {
        let dt = time.delta_secs();
        let keyboard_speed = 400.0 * projection.scale; // Speed scaled with zoom level
        
        let mut final_translation = Vec2::ZERO;
        if pan_dir != Vec2::ZERO {
            final_translation += pan_dir.normalize() * keyboard_speed * dt;
        }
        if is_dragging {
            final_translation += drag_delta * projection.scale;
        }
        
        if final_translation != Vec2::ZERO {
            transform.translation += final_translation.extend(0.0);
            
            // Instantly break tracking lock
            controller.tracked_entity = None;
        }
    }
}
```

#### E. Selection System (`camera_select_system`)
Translates viewport cursor positions to world space coordinates, finds the closest entity intersecting the click point via Avian 2D colliders, and registers it as selected/tracked.
```rust
use bevy::window::PrimaryWindow;

pub fn camera_select_system(
    mouse_input: Res<ButtonInput<MouseButton>>,
    window_query: Query<&Window, With<PrimaryWindow>>,
    mut camera_query: Query<(&Camera, &GlobalTransform, &mut CameraController), With<MainCamera>>,
    collider_query: Query<(Entity, &GlobalTransform, &Collider)>,
) {
    if mouse_input.just_pressed(MouseButton::Left) {
        let Ok(window) = window_query.get_single() else { return; };
        let Some(cursor_pos) = window.cursor_position() else { return; };
        
        let Ok((camera, camera_transform, mut controller)) = camera_query.get_single_mut() else { return; };
        let Ok(world_pos) = camera.viewport_to_world_2d(camera_transform, cursor_pos) else { return; };
        
        let mut closest_entity = None;
        let mut min_distance = f32::MAX;
        
        for (entity, transform, collider) in collider_query.iter() {
            let entity_pos = transform.translation().truncate();
            
            // Check intersection using circle collider radius
            let radius = collider.shape().as_circle().map(|c| c.radius).unwrap_or(20.0);
            let dist = entity_pos.distance(world_pos);
            
            if dist <= radius && dist < min_distance {
                closest_entity = Some(entity);
                min_distance = dist;
            }
        }
        
        if let Some(target) = closest_entity {
            controller.selected_entity = Some(target);
            controller.tracked_entity = Some(target);
        } else {
            // Clicking empty space clears current selection and tracking lock
            controller.selected_entity = None;
            controller.tracked_entity = None;
        }
    }
}
```

#### F. F-Key Focus System (`camera_refocus_system`)
Re-engages tracking lock and centers the camera on the selected entity when the `F` key is pressed.
```rust
pub fn camera_refocus_system(
    keyboard_input: Res<ButtonInput<KeyCode>>,
    mut camera_query: Query<&mut CameraController, With<MainCamera>>,
) {
    if keyboard_input.just_pressed(KeyCode::KeyF) {
        if let Ok(mut controller) = camera_query.get_single_mut() {
            if let Some(selected) = controller.selected_entity {
                controller.tracked_entity = Some(selected);
            }
        }
    }
}
```

---

## 2. Automated Integration & Verification Tests (Milestone 5 / R4/R5)

Automated verification is implemented as a Rust integration test file at `tests/rendering_camera_test.rs`. It runs in a headless environment and uses mock assets to verify the behaviors of both the **Camera Controller** (Milestone 4) and the **Animator System** (Milestone 2/3).

### 2.1 Headless App Configuration
We configure Bevy in a headless mode by omitting window/audio plugins but enabling `AssetPlugin` and defining mock asset storages to support animations without disk dependencies.

```rust
use bevy::prelude::*;
use avian2d::prelude::*;
use std::collections::HashMap;
use vibecoded_yukkuri_game::ai::{AIPlugin, AIState, StableId, VisibleTargets, Needs, Flight};
use vibecoded_yukkuri_game::prefabs::spawn_yukkuri_prefab;

// Marker components for testing
#[derive(Component)]
struct TestAnimator;

fn setup_test_app() -> App {
    let mut app = App::new();
    app.add_plugins(MinimalPlugins);
    app.add_plugins(AssetPlugin::default());
    app.add_plugins(PhysicsPlugins::default());
    app.add_plugins(AIPlugin);
    
    // Initialize mock assets
    app.init_resource::<Assets<Image>>();
    app.init_resource::<Assets<TextureAtlasLayout>>();
    
    app
}
```

### 2.2 Integration Test Cases

#### Test Case 1: Camera Smooth Follow (`test_camera_follow`)
Verifies that the camera smoothly tracks (lerps towards) the designated entity.
1. Spawn a camera with `CameraController`.
2. Spawn a target Yukkuri entity at `(100.0, 100.0)`.
3. Set `camera_controller.tracked_entity = Some(target_entity)`.
4. Step the simulation and assert that the camera moves closer to the target according to the lerp speed.
```rust
#[test]
fn test_camera_follow() {
    let mut app = setup_test_app();
    
    let camera_id = app.world_mut().spawn((
        Camera2d::default(),
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
    
    // Mock virtual time resource with a fixed delta of 0.1s
    let mut time = Time::default();
    time.advance_by(std::time::Duration::from_millis(100));
    app.insert_resource(time);
    
    app.update();
    
    let camera_transform = app.world().get::<Transform>(camera_id).unwrap();
    // Camera should move from (0,0) towards (100,100)
    assert!(camera_transform.translation.x > 0.0);
    assert!(camera_transform.translation.y > 0.0);
    assert!(camera_transform.translation.x < 100.0);
}
```

#### Test Case 2: Tracking Lock Break (`test_camera_pan_breaks_lock`)
Verifies that any manual camera panning immediately clears the tracking lock.
1. Spawn camera and target; lock camera onto target.
2. Inject a key press event (e.g. `KeyCode::KeyW` or `KeyCode::ArrowLeft`).
3. Tick the app.
4. Assert that `tracked_entity` is now `None`.
```rust
#[test]
fn test_camera_pan_breaks_lock() {
    let mut app = setup_test_app();
    
    let camera_id = app.world_mut().spawn((
        Camera2d::default(),
        MainCamera,
        CameraController {
            tracked_entity: Some(Entity::PLACEHOLDER),
            ..Default::default()
        },
        Transform::from_xyz(0.0, 0.0, 0.0),
    )).id();
    
    // Simulate pressing KeyW
    let mut keyboard_input = ButtonInput::<KeyCode>::default();
    keyboard_input.press(KeyCode::KeyW);
    app.insert_resource(keyboard_input);
    
    app.update();
    
    let controller = app.world().get::<CameraController>(camera_id).unwrap();
    assert!(controller.tracked_entity.is_none(), "Panning should break camera follow lock");
}
```

#### Test Case 3: Cursor-Based Click Selection (`test_camera_selection`)
Verifies window-to-world conversion, collider checks, and selection logic.
1. Spawn a target at world position `(100.0, 100.0)`.
2. Spawn a camera centered at `(100.0, 100.0)`.
3. Spawn a primary Window entity with a cursor position matching the center `(400.0, 300.0)` for an `800x600` viewport.
4. Inject a Left Mouse Button click event.
5. Tick the app and assert that the target entity was successfully selected and locked into tracking.
```rust
#[test]
fn test_camera_selection() {
    let mut app = setup_test_app();
    
    // Spawn camera centered at target world pos
    let camera_id = app.world_mut().spawn((
        Camera2d::default(),
        MainCamera,
        CameraController::default(),
        Transform::from_xyz(100.0, 100.0, 0.0),
    )).id();
    
    let target_id = app.world_mut().spawn((
        Transform::from_xyz(100.0, 100.0, 0.0),
        Collider::circle(20.0),
    )).id();
    
    // Spawn Primary Window
    let mut window = Window {
        resolution: bevy::window::WindowResolution::new(800.0, 600.0),
        ..Default::default()
    };
    window.set_cursor_position(Some(Vec2::new(400.0, 300.0))); // Center clicks
    app.world_mut().spawn((window, bevy::window::PrimaryWindow));
    
    // Inject Left Click
    let mut mouse_input = ButtonInput::<MouseButton>::default();
    mouse_input.press(MouseButton::Left);
    app.insert_resource(mouse_input);
    
    app.update();
    
    let controller = app.world().get::<CameraController>(camera_id).unwrap();
    assert_eq!(controller.selected_entity, Some(target_id));
    assert_eq!(controller.tracked_entity, Some(target_id));
}
```

#### Test Case 4: Refocus Command (`test_camera_refocus`)
Verifies that pressing `F` re-establishes follow lock on the selected entity.
1. Spawn camera with `selected_entity = Some(target)` and `tracked_entity = None`.
2. Inject a key press event for `KeyCode::KeyF`.
3. Tick the app.
4. Assert that `tracked_entity` is now equal to `selected_entity`.
```rust
#[test]
fn test_camera_refocus() {
    let mut app = setup_test_app();
    
    let target_id = app.world_mut().spawn_empty().id();
    let camera_id = app.world_mut().spawn((
        Camera2d::default(),
        MainCamera,
        CameraController {
            selected_entity: Some(target_id),
            tracked_entity: None,
            ..Default::default()
        },
        Transform::from_xyz(0.0, 0.0, 0.0),
    )).id();
    
    let mut keyboard_input = ButtonInput::<KeyCode>::default();
    keyboard_input.press(KeyCode::KeyF);
    app.insert_resource(keyboard_input);
    
    app.update();
    
    let controller = app.world().get::<CameraController>(camera_id).unwrap();
    assert_eq!(controller.tracked_entity, Some(target_id), "Pressing F should refocus on the selected entity");
}
```

#### Test Case 5: Animation Frame & Event Updates (`test_animation_runtime`)
Verifies animator frame progression (Virtual Time) and frame event emission.
1. Spawn entity with `Animator`, `YukkuriAnimations`, and `TextureAtlas` components.
2. Configure animation definitions with loop and frame events.
3. Advance virtual time and assert that frames advance, loop, and fire animation events in Bevy.
```rust
#[derive(Event, Clone, Debug)]
pub struct AnimationEvent {
    pub entity: Entity,
    pub event_name: String,
}

#[test]
fn test_animation_runtime() {
    let mut app = setup_test_app();
    app.add_event::<AnimationEvent>();
    
    // Spawn animator component
    // ...
}
```
