use bevy::prelude::*;
use avian2d::prelude::*;
use std::collections::HashMap;

#[derive(PhysicsLayer, Copy, Clone, Debug, Default, PartialEq, Eq)]
pub enum GameLayer {
    #[default]
    GroundUnit,
    FlyingUnit,
    Item,
    LowObstacle,
    HighObstacle,
    Water,
    Poop,
    Sensor,
}

#[derive(Component, Reflect, Debug, Clone)]
#[reflect(Component, Default)]
pub struct Mount {
    pub parent_id: Option<Entity>,
    pub children_ids: Vec<Entity>,
    pub mount_point_offset: Vec2,
    pub structure_dirty: bool,
}

impl Default for Mount {
    fn default() -> Self {
        Self {
            parent_id: None,
            children_ids: Vec::new(),
            mount_point_offset: Vec2::new(0.0, 30.0), // Stack vertically
            structure_dirty: false,
        }
    }
}

#[derive(Component, Reflect, Debug, Clone)]
#[reflect(Component)]
pub struct PendingDismount {
    pub parent_id: Entity,
    pub time_in_pending: f32,
}

#[derive(Component, Debug, Clone)]
pub struct HierarchyProxyCollider {
    pub root_entity: Entity,
}

pub struct MountSimulationPlugin;

impl Plugin for MountSimulationPlugin {
    fn build(&self, app: &mut App) {
        app.register_type::<Mount>()
            .register_type::<PendingDismount>()
            .add_systems(Update, (
                process_structure_updates_system,
                process_dismounts_system,
            ));
    }
}

/// System to update root colliders when the hierarchy changes.
pub fn process_structure_updates_system(
    mut commands: Commands,
    mut query_mounts: Query<(Entity, &mut Mount)>,
    query_colliders: Query<&Collider>,
    query_proxies: Query<(Entity, &HierarchyProxyCollider)>,
) {
    // 1. Gather all dirty roots
    let mut dirty_roots = Vec::new();
    for (entity, mount) in query_mounts.iter() {
        if mount.parent_id.is_none() && mount.structure_dirty {
            dirty_roots.push(entity);
        }
    }

    if dirty_roots.is_empty() {
        return;
    }

    // Map of all mounts for fast traversal
    let mounts_map: HashMap<Entity, Mount> = query_mounts.iter().map(|(e, m)| (e, m.clone())).collect();

    for root_entity in dirty_roots {
        // Remove old proxy colliders on the root
        for (proxy_entity, proxy) in query_proxies.iter() {
            if proxy.root_entity == root_entity {
                commands.entity(proxy_entity).despawn();
            }
        }

        // Traverse hierarchy and create new proxy colliders on the root
        let mut stack = vec![(root_entity, Vec2::ZERO)];
        let mut new_proxies = Vec::new();

        while let Some((curr_ent, curr_offset)) = stack.pop() {
            if let Some(mount) = mounts_map.get(&curr_ent) {
                for &child_id in &mount.children_ids {
                    if let Some(child_mount) = mounts_map.get(&child_id) {
                        let child_total_offset = curr_offset + child_mount.mount_point_offset;

                        // Get child collider radius or default to circle with 15.0 radius
                        let radius = if let Ok(collider) = query_colliders.get(child_id) {
                            collider.shape().as_ball().map(|b| b.radius).unwrap_or(15.0)
                        } else {
                            15.0
                        };

                        new_proxies.push((child_total_offset, radius));
                        stack.push((child_id, child_total_offset));
                    }
                }
            }
        }

        // Spawn new proxy collider child entities under the root
        commands.entity(root_entity).with_children(|parent| {
            for (offset, radius) in new_proxies {
                parent.spawn((
                    Collider::circle(radius),
                    Transform::from_translation(offset.extend(0.0)),
                    HierarchyProxyCollider { root_entity },
                    CollisionLayers::new(
                        GameLayer::GroundUnit,
                        LayerMask::from(GameLayer::GroundUnit) | LayerMask::from(GameLayer::LowObstacle) | LayerMask::from(GameLayer::HighObstacle),
                    ),
                ));
            }
        });

        // Clear dirty flag
        if let Ok((_, mut mount)) = query_mounts.get_mut(root_entity) {
            mount.structure_dirty = false;
        }
    }
}

/// System to process dismounting entities via spiral search.
pub fn process_dismounts_system(
    mut commands: Commands,
    time: Res<Time>,
    spatial_query: SpatialQuery,
    mut query_pending: Query<(Entity, &mut PendingDismount, &Transform, &Collider)>,
) {
    let dt = time.delta_secs();

    for (entity, mut pending, transform, collider) in query_pending.iter_mut() {
        pending.time_in_pending += dt;

        let start_pos = transform.translation.truncate();
        let collider_radius = collider.shape().as_ball().map(|b| b.radius).unwrap_or(15.0);

        let found_spot = if pending.time_in_pending < 5.0 {
            find_free_spot(&spatial_query, entity, start_pos, collider_radius)
        } else {
            // Timeout fallback: teleport to safe coordinates (or near 0,0)
            Some(Vec2::new(0.0, 0.0))
        };

        if let Some(spot) = found_spot {
            // Restore dynamic physics body and normal collision
            commands.entity(entity)
                .insert((
                    RigidBody::Dynamic,
                    Transform::from_translation(spot.extend(transform.translation.z)),
                    CollisionLayers::new(
                        GameLayer::GroundUnit,
                        LayerMask::from(GameLayer::GroundUnit)
                            | LayerMask::from(GameLayer::LowObstacle)
                            | LayerMask::from(GameLayer::HighObstacle)
                            | LayerMask::from(GameLayer::Water)
                            | LayerMask::from(GameLayer::Item),
                    ),
                ))
                .remove::<PendingDismount>();
        }
    }
}

fn find_free_spot(
    spatial_query: &SpatialQuery,
    dismounting_entity: Entity,
    start_pos: Vec2,
    collider_radius: f32,
) -> Option<Vec2> {
    let max_radius = 200.0;
    let mut current_r = 0.0;
    let mut theta = rand::random::<f32>() * 2.0 * std::f32::consts::PI;
    let step_size = collider_radius * 2.0;
    let max_checks = 100;
    let mut checks = 0;

    let filter = SpatialQueryFilter::default()
        .with_excluded_entities(vec![dismounting_entity])
        .with_mask(LayerMask::from(GameLayer::GroundUnit) | LayerMask::from(GameLayer::HighObstacle));

    let is_spot_free = |pos: Vec2| -> bool {
        let intersections = spatial_query.shape_intersections(
            &Collider::circle(collider_radius),
            pos,
            0.0,
            &filter,
        );
        intersections.is_empty()
    };

    if is_spot_free(start_pos) {
        return Some(start_pos);
    }

    while current_r < max_radius && checks < max_checks {
        checks += 1;
        let offset = Vec2::new(current_r * theta.cos(), current_r * theta.sin());
        let candidate = start_pos + offset;

        if is_spot_free(candidate) {
            return Some(candidate);
        }

        let arc = collider_radius;
        let d_theta = arc / if current_r > 5.0 { current_r } else { 1.0 };
        theta += d_theta;
        current_r = (step_size / (2.0 * std::f32::consts::PI)) * theta;
    }

    None
}
