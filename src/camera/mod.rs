use bevy::prelude::*;
use bevy::input::mouse::{MouseWheel, MouseScrollUnit, MouseMotion};
use bevy::window::PrimaryWindow;
use avian2d::prelude::Collider;
use crate::ai::WorldSettings;


#[derive(Component, Debug, Default)]
pub struct MainCamera;

#[derive(Component, Debug)]
pub struct CameraController {
    pub tracked_entity: Option<Entity>,
    pub selected_entity: Option<Entity>,
    pub lerp_speed: f32,
    pub target_zoom: f32,
    pub min_zoom: f32,
    pub max_zoom: f32,
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

pub fn setup_camera(mut commands: Commands, world_settings: Option<Res<WorldSettings>>) {
    let (width, height) = if let Some(ref settings) = world_settings {
        (settings.width, settings.height)
    } else {
        (3000.0, 3000.0)
    };
    let center_x = width / 2.0;
    let center_y = height / 2.0;

    // Background clear colour — matches the world rectangle below.
    commands.insert_resource(ClearColor(Color::srgb(0.35, 0.60, 0.25)));

    // World background rectangle (z = -100 so it renders behind everything).
    commands.spawn((
        Sprite {
            color: Color::srgb(0.35, 0.60, 0.25),
            custom_size: Some(Vec2::new(width, height)),
            ..default()
        },
        Transform::from_xyz(center_x, center_y, -100.0),
        GlobalTransform::default(),
        Visibility::default(),
    ));

    commands.spawn((
        Camera2d,
        MainCamera,
        CameraController::default(),
        Transform::from_xyz(center_x, center_y, 0.0),
    ));
}

pub fn camera_follow_system(
    time: Res<Time>,
    mut camera_query: Query<(&mut Transform, &mut CameraController), With<MainCamera>>,
    target_query: Query<&Transform, Without<MainCamera>>,
    world_settings: Option<Res<WorldSettings>>,
) {
    let dt = time.delta_secs();
    let (width, height) = if let Some(settings) = world_settings {
        (settings.width, settings.height)
    } else {
        (3000.0, 3000.0)
    };
    if let Some((mut camera_transform, mut controller)) = camera_query.iter_mut().next() {
        if let Some(tracked) = controller.tracked_entity {
            match target_query.get(tracked) {
                Ok(target_transform) => {
                    if target_transform.translation.x.is_finite() && target_transform.translation.y.is_finite() {
                        let target_pos = target_transform.translation.truncate();
                        let camera_pos = camera_transform.translation.truncate();
                        
                        let lerp_factor = (controller.lerp_speed * dt).min(1.0);
                        let new_pos = camera_pos + (target_pos - camera_pos) * lerp_factor;
                        
                        camera_transform.translation.x = new_pos.x;
                        camera_transform.translation.y = new_pos.y;
                    }
                }
                Err(_) => {
                    controller.tracked_entity = None;
                }
            }
        }
        
        camera_transform.translation.x = camera_transform.translation.x.clamp(0.0, width.max(0.0));
        camera_transform.translation.y = camera_transform.translation.y.clamp(0.0, height.max(0.0));
    }
}

pub fn camera_zoom_system(
    mut mouse_wheel: MessageReader<MouseWheel>,
    keyboard_input: Res<ButtonInput<KeyCode>>,
    time: Res<Time>,
    mut query: Query<(&mut Projection, &mut CameraController), With<MainCamera>>,
) {
    let mut zoom_delta = 0.0;
    
    for event in mouse_wheel.read() {
        let factor = match event.unit {
            MouseScrollUnit::Line => event.y,
            MouseScrollUnit::Pixel => event.y * 0.05,
        };
        zoom_delta -= factor * 0.15;
    }
    
    let dt = time.delta_secs();
    if keyboard_input.pressed(KeyCode::PageUp) {
        zoom_delta -= 1.0 * dt;
    }
    if keyboard_input.pressed(KeyCode::PageDown) {
        zoom_delta += 1.0 * dt;
    }
    
    if let Some((mut projection, mut controller)) = query.iter_mut().next() {
        if zoom_delta != 0.0 {
            controller.target_zoom = (controller.target_zoom + zoom_delta).clamp(controller.min_zoom, controller.max_zoom);
        }
        
        if let Projection::Orthographic(ref mut orthographic) = *projection {
            let zoom_factor = (controller.zoom_speed * dt).min(1.0);
            orthographic.scale += (controller.target_zoom - orthographic.scale) * zoom_factor;
            orthographic.scale = orthographic.scale.clamp(controller.min_zoom, controller.max_zoom);
        }
    }
}

pub fn camera_pan_system(
    keyboard_input: Res<ButtonInput<KeyCode>>,
    mouse_input: Res<ButtonInput<MouseButton>>,
    mut mouse_motion: MessageReader<MouseMotion>,
    time: Res<Time>,
    mut query: Query<(&mut Transform, &mut CameraController, &Projection), With<MainCamera>>,
    world_settings: Option<Res<WorldSettings>>,
) {
    let mut pan_dir = Vec2::ZERO;
    
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
    
    let mut drag_delta = Vec2::ZERO;
    for event in mouse_motion.read() {
        drag_delta.x -= event.delta.x;
        drag_delta.y += event.delta.y;
    }
    let is_dragging = mouse_input.pressed(MouseButton::Middle);
    
    let (width, height) = if let Some(settings) = world_settings {
        (settings.width, settings.height)
    } else {
        (3000.0, 3000.0)
    };
    
    if let Some((mut transform, mut controller, projection)) = query.iter_mut().next() {
        let dt = time.delta_secs();
        let scale = if let Projection::Orthographic(ref ortho) = *projection {
            ortho.scale
        } else {
            1.0
        };
        let keyboard_speed = 400.0 * scale;
        
        let mut final_translation = Vec2::ZERO;
        if pan_dir != Vec2::ZERO {
            final_translation += pan_dir.normalize() * keyboard_speed * dt;
        }
        if is_dragging {
            final_translation += drag_delta * scale;
        }
        
        if final_translation != Vec2::ZERO {
            transform.translation += final_translation.extend(0.0);
            controller.tracked_entity = None;
        }
        
        transform.translation.x = transform.translation.x.clamp(0.0, width.max(0.0));
        transform.translation.y = transform.translation.y.clamp(0.0, height.max(0.0));
    }
}

pub fn camera_select_system(
    mouse_input: Res<ButtonInput<MouseButton>>,
    window_query: Query<&Window, With<PrimaryWindow>>,
    mut camera_query: Query<(&Camera, &GlobalTransform, &mut CameraController), With<MainCamera>>,
    collider_query: Query<(Entity, &GlobalTransform, &Collider)>,
) {
    if mouse_input.just_pressed(MouseButton::Left) {
        let Some(window) = window_query.iter().next() else { return; };
        let Some(cursor_pos) = window.cursor_position() else { return; };
        
        let Some((camera, camera_transform, mut controller)) = camera_query.iter_mut().next() else { return; };
        
        let world_pos = match camera.viewport_to_world_2d(camera_transform, cursor_pos) {
            Ok(pos) => pos,
            Err(_) => return,
        };
        
        let mut closest_entity = None;
        let mut min_distance = f32::MAX;
        
        for (entity, transform, collider) in collider_query.iter() {
            let entity_pos = transform.translation().truncate();
            
            // Check intersection using circle collider radius
            let radius = collider.shape().as_ball().map(|b| b.radius).unwrap_or(20.0);
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
            controller.selected_entity = None;
            controller.tracked_entity = None;
        }
    }
}

pub fn camera_refocus_system(
    keyboard_input: Res<ButtonInput<KeyCode>>,
    mut camera_query: Query<&mut CameraController, With<MainCamera>>,
) {
    if keyboard_input.just_pressed(KeyCode::KeyF) {
        if let Some(mut controller) = camera_query.iter_mut().next() {
            if let Some(selected) = controller.selected_entity {
                controller.tracked_entity = Some(selected);
            }
        }
    }
}

pub struct YukkuriCameraPlugin;

impl Plugin for YukkuriCameraPlugin {
    fn build(&self, app: &mut App) {
        app.add_systems(Startup, setup_camera)
            .add_systems(Update, (
                camera_follow_system,
                camera_zoom_system,
                camera_pan_system,
                camera_select_system,
                camera_refocus_system,
            ));
    }
}
