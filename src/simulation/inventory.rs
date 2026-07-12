use bevy::prelude::*;
use avian2d::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use crate::ai::StableId;
use crate::simulation::mount::GameLayer;

#[derive(Debug, Deserialize, Clone)]
pub struct ItemConfig {
    pub name: String,
    pub image: String,
    pub width: u32,
    pub height: u32,
    pub cost: u32,
    pub nutrition: Option<f32>,
    pub fun: Option<f32>,
    pub comfort: Option<f32>,
    pub quality: Option<f32>,
    pub is_portable: bool,
    pub obstacle_type: Option<String>,
    pub light_radius: Option<f32>,
    pub light_color: Option<Vec<u8>>,
    pub light_intensity: Option<f32>,
}

#[derive(Resource, Debug, Clone, Default)]
pub struct ItemRegistry {
    pub items: HashMap<String, ItemConfig>,
}

#[derive(Reflect, Default, Clone, Debug, Serialize, Deserialize, PartialEq)]
pub struct ItemStack {
    pub item_type_id: String,
    pub quantity: u32,
}

#[derive(Component, Reflect, Default, Clone, Debug)]
#[reflect(Component, Default)]
pub struct InventoryComponent {
    pub capacity: u32,
    pub items: Vec<ItemStack>,
}

impl InventoryComponent {
    pub fn can_add(&self, item_type_id: &str, count: u32, stack_limit: u32) -> bool {
        let mut remaining = count;
        for item in &self.items {
            if item.item_type_id == item_type_id {
                let space = stack_limit.saturating_sub(item.quantity);
                if space > 0 {
                    let taken = remaining.min(space);
                    remaining -= taken;
                }
                if remaining == 0 {
                    return true;
                }
            }
        }
        if remaining > 0 {
            let new_stacks_needed = (remaining as f32 / stack_limit as f32).ceil() as u32;
            let available_slots = self.capacity.saturating_sub(self.items.len() as u32);
            new_stacks_needed <= available_slots
        } else {
            true
        }
    }

    pub fn add(&mut self, item_type_id: &str, count: u32, stack_limit: u32) -> u32 {
        let mut remaining = count;
        for item in &mut self.items {
            if item.item_type_id == item_type_id {
                let space = stack_limit.saturating_sub(item.quantity);
                if space > 0 {
                    let taken = remaining.min(space);
                    item.quantity += taken;
                    remaining -= taken;
                }
                if remaining == 0 {
                    return count;
                }
            }
        }
        while remaining > 0 && (self.items.len() as u32) < self.capacity {
            let take_for_new_stack = remaining.min(stack_limit);
            self.items.push(ItemStack {
                item_type_id: item_type_id.to_string(),
                quantity: take_for_new_stack,
            });
            remaining -= take_for_new_stack;
        }
        count - remaining
    }

    pub fn remove(&mut self, item_type_id: &str, count: u32) -> u32 {
        let mut remaining_to_remove = count;
        let mut indices_to_remove = Vec::new();
        for (i, item) in self.items.iter_mut().enumerate().rev() {
            if item.item_type_id == item_type_id {
                let taken = remaining_to_remove.min(item.quantity);
                item.quantity -= taken;
                remaining_to_remove -= taken;
                if item.quantity == 0 {
                    indices_to_remove.push(i);
                }
                if remaining_to_remove == 0 {
                    break;
                }
            }
        }
        for i in indices_to_remove {
            self.items.remove(i);
        }
        count - remaining_to_remove
    }

    pub fn has(&self, item_type_id: &str, count: u32) -> bool {
        let mut total = 0;
        for item in &self.items {
            if item.item_type_id == item_type_id {
                total += item.quantity;
                if total >= count {
                    return true;
                }
            }
        }
        false
    }

    pub fn get_total(&self, item_type_id: &str) -> u32 {
        self.items.iter()
            .filter(|item| item.item_type_id == item_type_id)
            .map(|item| item.quantity)
            .sum()
    }
}

#[derive(Component, Reflect, Debug, Clone)]
#[reflect(Component)]
pub struct InventoryPickupRequest {
    pub target_entity_id: Entity,
}

#[derive(Component, Reflect, Debug, Clone)]
#[reflect(Component)]
pub struct InventoryDropRequest {
    pub item_type_id: String,
    pub quantity: u32,
}

#[derive(Component, Reflect, Default, Clone, Debug, PartialEq)]
#[reflect(Component, Default)]
pub struct ItemStats {
    pub type_id: String,
    pub value: f32,
    pub name: String,
    pub nutrition: f32,
    pub fun: f32,
    pub comfort: f32,
    pub is_portable: bool,
    pub quality: f32,
}

/// Message emitted when inventory changes.
#[derive(bevy::prelude::Message, Debug, Clone)]
pub struct InventoryChangedMessage {
    pub entity_id: Entity,
    pub item_type_id: String,
    pub delta: i32,
}

pub struct InventorySimulationPlugin;

impl Plugin for InventorySimulationPlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<ItemRegistry>()
            .register_type::<ItemStack>()
            .register_type::<InventoryComponent>()
            .register_type::<InventoryPickupRequest>()
            .register_type::<InventoryDropRequest>()
            .register_type::<ItemStats>()
            .add_message::<InventoryChangedMessage>()
            .add_systems(Startup, load_items_registry_system)
            .add_systems(Update, (
                inventory_pickup_system,
                inventory_drop_system,
            ));
    }
}

pub fn load_items_registry_system(mut item_registry: ResMut<ItemRegistry>) {
    let items_path = "data/items/items.toml";
    match std::fs::read_to_string(items_path) {
        Ok(content) => {
            #[derive(Deserialize)]
            struct TomlItems {
                items: HashMap<String, ItemConfig>,
            }
            match toml::from_str::<TomlItems>(&content) {
                Ok(data) => {
                    item_registry.items = data.items;
                    info!("Loaded {} item configurations", item_registry.items.len());
                }
                Err(err) => {
                    error!("Failed to parse items.toml: {:?}", err);
                }
            }
        }
        Err(err) => {
            error!("Failed to read items.toml: {:?}", err);
        }
    }
}

pub fn inventory_pickup_system(
    mut commands: Commands,
    item_registry: Res<ItemRegistry>,
    mut query_pickup: Query<(Entity, &mut InventoryComponent, &InventoryPickupRequest)>,
    query_items: Query<&ItemStats>,
    mut message_writer: MessageWriter<InventoryChangedMessage>,
) {
    for (entity, mut inventory, request) in query_pickup.iter_mut() {
        let target_id = request.target_entity_id;

        if let Ok(item_stats) = query_items.get(target_id) {
            let item_type_id = &item_stats.type_id;

            // Load stack limit from config if possible
            let stack_limit = if let Some(config) = item_registry.items.get(item_type_id) {
                if config.is_portable { 99 } else { 1 }
            } else {
                99
            };

            if inventory.can_add(item_type_id, 1, stack_limit) {
                let added = inventory.add(item_type_id, 1, stack_limit);
                if added > 0 {
                    // Emit event
                    message_writer.write(InventoryChangedMessage {
                        entity_id: entity,
                        item_type_id: item_type_id.clone(),
                        delta: added as i32,
                    });

                    // Destroy item entity in the world
                    commands.entity(target_id).despawn();
                    info!("Entity {:?} picked up item {}", entity, item_type_id);
                }
            }
        }

        // Clean up request
        commands.entity(entity).remove::<InventoryPickupRequest>();
    }
}

pub fn inventory_drop_system(
    mut commands: Commands,
    asset_server: Res<AssetServer>,
    item_registry: Res<ItemRegistry>,
    mut query_drop: Query<(Entity, &mut InventoryComponent, &Transform, &InventoryDropRequest)>,
    mut message_writer: MessageWriter<InventoryChangedMessage>,
    mut nav_service: Option<ResMut<crate::simulation::hpa::NavigationService>>,
) {
    for (entity, mut inventory, transform, request) in query_drop.iter_mut() {
        let item_type_id = &request.item_type_id;
        let count = request.quantity;

        if inventory.has(item_type_id, count) {
            let removed = inventory.remove(item_type_id, count);
            if removed > 0 {
                // Emit event
                message_writer.write(InventoryChangedMessage {
                    entity_id: entity,
                    item_type_id: item_type_id.clone(),
                    delta: -(removed as i32),
                });

                // Spawn items in the world
                for _i in 0..removed {
                    // Spread dropped items slightly
                    let offset_x = (rand::random::<f32>() - 0.5) * 20.0;
                    let offset_y = 20.0 + (rand::random::<f32>() - 0.5) * 10.0;
                    let spawn_pos = transform.translation.truncate() + Vec2::new(offset_x, offset_y);

                    spawn_item_prefab(
                        &mut commands,
                        item_type_id,
                        spawn_pos,
                        &asset_server,
                        &item_registry,
                        nav_service.as_deref_mut(),
                    );
                }
                info!("Entity {:?} dropped {} x {}", entity, removed, item_type_id);
            }
        }

        // Clean up request
        commands.entity(entity).remove::<InventoryDropRequest>();
    }
}

pub fn spawn_item_prefab(
    commands: &mut Commands,
    item_type_id: &str,
    position: Vec2,
    asset_server: &AssetServer,
    item_registry: &ItemRegistry,
    mut nav_service: Option<&mut crate::simulation::hpa::NavigationService>,
) -> Entity {
    let config = item_registry.items.get(item_type_id)
        .expect("unregistered item_type_id");

    let image_handle = asset_server.load(format!("images/{}", config.image));

    let radius = (config.width as f32 / 2.0).max(config.height as f32 / 2.0).max(10.0);

    let mut entity_builder = commands.spawn((
        ItemStats {
            type_id: item_type_id.to_string(),
            value: config.cost as f32,
            name: config.name.clone(),
            nutrition: config.nutrition.unwrap_or(0.0),
            fun: config.fun.unwrap_or(0.0),
            comfort: config.comfort.unwrap_or(0.0),
            is_portable: config.is_portable,
            quality: config.quality.unwrap_or(0.0),
        },
        Transform::from_xyz(position.x, position.y, 0.5),
        Visibility::default(),
        Sprite {
            image: image_handle,
            ..default()
        },
        RigidBody::Dynamic,
        Collider::circle(radius),
        Mass(1.0),
        Friction::new(0.5),
        Restitution::new(0.1),
        LinearVelocity::default(),
        AngularVelocity::default(),
        CollisionLayers::new(
            GameLayer::Item,
            LayerMask::from(GameLayer::GroundUnit) | LayerMask::from(GameLayer::HighObstacle) | LayerMask::from(GameLayer::Poop) | LayerMask::from(GameLayer::Item),
        ),
    ));

    if let Some(light_rad) = config.light_radius {
        let color = if let Some(ref c) = config.light_color {
            if c.len() == 3 {
                Color::srgb(c[0] as f32 / 255.0, c[1] as f32 / 255.0, c[2] as f32 / 255.0)
            } else {
                Color::WHITE
            }
        } else {
            Color::WHITE
        };
        let intensity = config.light_intensity.unwrap_or(1.0);
        entity_builder.insert(crate::render::lighting::LightSource {
            radius: light_rad,
            color,
            intensity,
            flicker_style: 0,
            base_intensity: intensity,
        });
    }

    if let Some(ref obs_type) = config.obstacle_type {
        if obs_type == "HIGH" {
            if let Some(ref mut ns) = nav_service {
                {
                    let mut grid = ns.grid.write().unwrap();
                    grid.update_obstacle_rect(
                        position.x,
                        position.y,
                        config.width as f32,
                        config.height as f32,
                        true,
                        5, // TRAVERSAL_WALK | TRAVERSAL_SWIM
                    );
                }
                let _ = ns.request_tx.send(crate::simulation::hpa::NavCommand::RebuildAll);
            }
        }
    }

    let entity = entity_builder.id();
    commands.entity(entity).insert(StableId::from_entity(entity));
    entity
}
