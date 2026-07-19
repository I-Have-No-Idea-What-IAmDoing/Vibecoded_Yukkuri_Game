use bevy::prelude::*;
use bevy::input::mouse::{MouseWheel, MouseScrollUnit, MouseMotion};
use bevy::window::PrimaryWindow;
use crate::ai::WorldSettings;


#[derive(Component, Debug, Default)]
pub struct MainCamera;

#[derive(Component, Debug)]
pub struct CameraController {
    pub tracked_entity: Option<Entity>,
    pub selected_entity: Option<Entity>,
    pub selected_entities: Vec<Entity>,
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
            selected_entities: Vec::new(),
            lerp_speed: 5.0,
            target_zoom: 1.0,
            min_zoom: 0.5,
            max_zoom: 2.0,
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
    commands.insert_resource(ClearColor(Color::BLACK));

    // World background rectangle (z = -100 so it renders behind everything).
    commands.spawn((
        Sprite {
            color: Color::BLACK,
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
    
    let is_ctrl = keyboard_input.pressed(KeyCode::ControlLeft) || keyboard_input.pressed(KeyCode::ControlRight);
    if is_ctrl {
        if keyboard_input.just_pressed(KeyCode::Equal) || keyboard_input.just_pressed(KeyCode::NumpadAdd) {
            zoom_delta -= 0.25;
        }
        if keyboard_input.just_pressed(KeyCode::Minus) || keyboard_input.just_pressed(KeyCode::NumpadSubtract) {
            zoom_delta += 0.25;
        }
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

#[derive(Resource, Default, Debug, Clone)]
pub struct DragSelectionState {
    pub start_pos: Option<Vec2>,
    pub current_pos: Option<Vec2>,
}

pub fn drag_selection_system(
    mouse_button_input: Res<ButtonInput<MouseButton>>,
    keyboard_input: Res<ButtonInput<KeyCode>>,
    window_query: Query<&Window, With<PrimaryWindow>>,
    camera_query: Query<(&Camera, &GlobalTransform), With<MainCamera>>,
    mut camera_controller_query: Query<&mut CameraController, With<MainCamera>>,
    yukkuri_query: Query<(Entity, &GlobalTransform, &avian2d::prelude::Collider), Without<crate::ai::Dead>>,
    mut selection_state: ResMut<DragSelectionState>,
    mut gizmos: Gizmos,
) {
    let Some(window) = window_query.iter().next() else { return; };
    let Some((camera, camera_transform)) = camera_query.iter().next() else { return; };
    let Some(mut controller) = camera_controller_query.iter_mut().next() else { return; };

    if mouse_button_input.just_pressed(MouseButton::Left) {
        if let Some(cursor_pos) = window.cursor_position() {
            let height = window.height();
            let is_over_ui = cursor_pos.y < 40.0 || cursor_pos.y > height - 120.0;
            if !is_over_ui {
                selection_state.start_pos = Some(cursor_pos);
                selection_state.current_pos = Some(cursor_pos);
            }
        }
    }

    if mouse_button_input.pressed(MouseButton::Left) {
        if selection_state.start_pos.is_some() {
            if let Some(cursor_pos) = window.cursor_position() {
                selection_state.current_pos = Some(cursor_pos);
                
                if let (Some(start), Some(end)) = (selection_state.start_pos, selection_state.current_pos) {
                    if start.distance(end) > 5.0 {
                        let start_world = camera.viewport_to_world_2d(camera_transform, start).unwrap_or(Vec2::ZERO);
                        let end_world = camera.viewport_to_world_2d(camera_transform, end).unwrap_or(Vec2::ZERO);
                        
                        let center = (start_world + end_world) / 2.0;
                        let size = (start_world - end_world).abs();
                        
                        gizmos.rect_2d(
                            center,
                            size,
                            Color::srgb(0.2, 0.9, 0.2),
                        );
                    }
                }
            }
        }
    }

    if mouse_button_input.just_released(MouseButton::Left) {
        if let (Some(start), Some(end)) = (selection_state.start_pos.take(), selection_state.current_pos.take()) {
            let start_world = camera.viewport_to_world_2d(camera_transform, start).unwrap_or(Vec2::ZERO);
            let end_world = camera.viewport_to_world_2d(camera_transform, end).unwrap_or(Vec2::ZERO);
            
            let is_drag = start.distance(end) > 5.0;
            let shift = keyboard_input.pressed(KeyCode::ShiftLeft) || keyboard_input.pressed(KeyCode::ShiftRight);
            
            if is_drag {
                let min_x = start_world.x.min(end_world.x);
                let max_x = start_world.x.max(end_world.x);
                let min_y = start_world.y.min(end_world.y);
                let max_y = start_world.y.max(end_world.y);
                
                let mut newly_selected = Vec::new();
                for (entity, g_trans, _) in &yukkuri_query {
                    let pos = g_trans.translation().truncate();
                    if pos.x >= min_x && pos.x <= max_x && pos.y >= min_y && pos.y <= max_y {
                        newly_selected.push(entity);
                    }
                }
                
                if shift {
                    for ent in newly_selected {
                        if !controller.selected_entities.contains(&ent) {
                            controller.selected_entities.push(ent);
                        }
                    }
                } else {
                    controller.selected_entities = newly_selected;
                }
            } else {
                let mut closest_entity = None;
                let mut min_distance = f32::MAX;
                
                for (entity, g_trans, collider) in &yukkuri_query {
                    let entity_pos = g_trans.translation().truncate();
                    let radius = collider.shape().as_ball().map(|b| b.radius).unwrap_or(20.0);
                    let dist = entity_pos.distance(start_world);
                    
                    if dist <= radius && dist < min_distance {
                        closest_entity = Some(entity);
                        min_distance = dist;
                    }
                }
                
                if let Some(target) = closest_entity {
                    if shift {
                        if let Some(pos) = controller.selected_entities.iter().position(|&x| x == target) {
                            controller.selected_entities.remove(pos);
                        } else {
                            controller.selected_entities.push(target);
                        }
                    } else {
                        controller.selected_entities = vec![target];
                    }
                    controller.tracked_entity = Some(target);
                } else {
                    if !shift {
                        controller.selected_entities.clear();
                        controller.tracked_entity = None;
                    }
                }
            }
            
            controller.selected_entity = controller.selected_entities.first().copied();
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

pub fn draw_world_grid_system(
    mut gizmos: Gizmos,
    camera_q: Query<(&Camera, &GlobalTransform, &Projection), With<MainCamera>>,
    world_settings: Option<Res<WorldSettings>>,
) {
    let Some((_camera, cam_transform, proj)) = camera_q.iter().next() else {
        return;
    };
    let Projection::Orthographic(ref ortho) = *proj else { return; };
    let (width, height) = if let Some(ref settings) = world_settings {
        (settings.width, settings.height)
    } else {
        (3000.0, 3000.0)
    };
    
    let grid_color = Color::srgb(0.275, 0.275, 0.275);
    let grid_size = 100.0_f32;
    let margin = 200.0_f32;
    
    let cam_pos = cam_transform.translation().truncate();
    let half_width = ortho.area.width() / 2.0 + margin;
    let half_height = ortho.area.height() / 2.0 + margin;
    
    let x_min = (cam_pos.x - half_width).max(0.0);
    let x_max = (cam_pos.x + half_width).min(width);
    let y_min = (cam_pos.y - half_height).max(0.0);
    let y_max = (cam_pos.y + half_height).min(height);
    
    let first_x = (x_min / grid_size).floor() * grid_size;
    let first_y = (y_min / grid_size).floor() * grid_size;
    
    let mut x = first_x;
    while x <= x_max {
        gizmos.line_2d(Vec2::new(x, y_min), Vec2::new(x, y_max), grid_color);
        x += grid_size;
    }
    
    let mut y = first_y;
    while y <= y_max {
        gizmos.line_2d(Vec2::new(x_min, y), Vec2::new(x_max, y), grid_color);
        y += grid_size;
    }
}

pub struct YukkuriCameraPlugin;

impl Plugin for YukkuriCameraPlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<DragSelectionState>()
            .add_systems(Startup, setup_camera)
            .add_systems(Update, (
                camera_follow_system,
                camera_zoom_system,
                camera_pan_system,
                drag_selection_system,
                camera_refocus_system,
                draw_world_grid_system,
            ).run_if(in_state(crate::GameState::Gameplay)));
    }
}
