use bevy::prelude::*;
use crate::audio::PlaySoundEvent;
use crate::ai::persistence::Economy;
use crate::simulation::inventory::{spawn_item_prefab, ItemRegistry};
use crate::camera::CameraController;

#[derive(Resource, Default, Debug, Clone)]
pub struct PlacementState {
    pub active: bool,
    pub current_item_id: String,
    pub cost: i32,
    pub ghost_entity: Option<Entity>,
}

#[derive(Component)]
pub struct PlacementGhost;

pub fn update_placement_system(
    mut commands: Commands,
    asset_server: Res<AssetServer>,
    item_registry: Res<ItemRegistry>,
    mouse_button_input: Res<ButtonInput<MouseButton>>,
    keyboard_input: Res<ButtonInput<KeyCode>>,
    window_query: Query<&Window>,
    camera_query: Query<(&Camera, &GlobalTransform), With<CameraController>>,
    mut placement_state: ResMut<PlacementState>,
    mut economy: ResMut<Economy>,
    mut sound_writer: MessageWriter<PlaySoundEvent>,
    mut nav_service: Option<ResMut<crate::simulation::hpa::NavigationService>>,
    mut query_ghosts: Query<(Entity, &mut Transform), With<PlacementGhost>>,
) {
    if !placement_state.active {
        // If inactive but ghost entity still exists, clean it up
        if let Some(ghost) = placement_state.ghost_entity.take() {
            commands.entity(ghost).despawn();
        }
        for (ghost, _) in query_ghosts.iter() {
            commands.entity(ghost).despawn();
        }
        return;
    }

    // Get cursor position and convert to world coordinates, falling back to Vec2::ZERO in headless environments
    let world_pos = (|| {
        let window = window_query.iter().next()?;
        let (camera, camera_transform) = camera_query.iter().next()?;
        let cursor_position = window.cursor_position()?;
        camera.viewport_to_world_2d(camera_transform, cursor_position).ok()
    })().unwrap_or(Vec2::ZERO);

    // 1. Ensure ghost preview exists and tracks cursor
    if placement_state.ghost_entity.is_none() {
        let item_id = &placement_state.current_item_id;
        if let Some(config) = item_registry.items.get(item_id) {
            let image_handle = asset_server.load(format!("images/{}", config.image));
            let ghost = commands.spawn((
                PlacementGhost,
                Sprite {
                    image: image_handle,
                    color: Color::srgba(1.0, 1.0, 1.0, 0.5),
                    ..default()
                },
                Transform::from_xyz(world_pos.x, world_pos.y, 0.6),
                Visibility::default(),
            )).id();
            placement_state.ghost_entity = Some(ghost);
        }
    } else if let Some(ghost) = placement_state.ghost_entity {
        if let Ok((_, mut trans)) = query_ghosts.get_mut(ghost) {
            trans.translation.x = world_pos.x;
            trans.translation.y = world_pos.y;
        }
    }

    // 2. Handle cancel inputs (Escape, Right-click)
    if keyboard_input.just_pressed(KeyCode::Escape) || mouse_button_input.just_pressed(MouseButton::Right) {
        sound_writer.write(PlaySoundEvent { name: "cancel".to_string() });
        if let Some(ghost) = placement_state.ghost_entity.take() {
            commands.entity(ghost).despawn();
        }
        placement_state.active = false;
        return;
    }

    // 3. Handle confirmed placement (Left-click)
    if mouse_button_input.just_pressed(MouseButton::Left) {
        let cost = placement_state.cost;
        if economy.money >= cost {
            // Spawn item
            spawn_item_prefab(
                &mut commands,
                &placement_state.current_item_id,
                world_pos,
                &asset_server,
                &item_registry,
                nav_service.as_deref_mut(),
            );

            economy.money -= cost;
            sound_writer.write(PlaySoundEvent { name: "place".to_string() });

            // Shift-click enables rapid placing of multiple items
            let shift_held = keyboard_input.pressed(KeyCode::ShiftLeft) || keyboard_input.pressed(KeyCode::ShiftRight);
            if shift_held && economy.money >= cost {
                // Keep placement active and spawn a new ghost in the next tick
                if let Some(ghost) = placement_state.ghost_entity.take() {
                    commands.entity(ghost).despawn();
                }
            } else {
                // Exit placement mode
                if let Some(ghost) = placement_state.ghost_entity.take() {
                    commands.entity(ghost).despawn();
                }
                placement_state.active = false;
            }
        } else {
            // Insufficient funds sound or feedback
            sound_writer.write(PlaySoundEvent { name: "cancel".to_string() });
            if let Some(ghost) = placement_state.ghost_entity.take() {
                commands.entity(ghost).despawn();
            }
            placement_state.active = false;
        }
    }
}
