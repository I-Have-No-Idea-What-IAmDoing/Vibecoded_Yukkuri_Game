use bevy::prelude::*;
use avian2d::prelude::*;
use std::collections::{HashMap, HashSet};
use crate::simulation::hpa::*;
use crate::ai::MoveTarget;

#[derive(Component, Reflect, Debug, Clone, Default)]
#[reflect(Component, Default)]
pub struct MovementPath {
    pub waypoints: Vec<Vec2>,
    pub current_index: usize,
    pub acceptance_radius: f32,
}

pub struct NavigationSimulationPlugin;

impl Plugin for NavigationSimulationPlugin {
    fn build(&self, app: &mut App) {
        app.register_type::<MovementPath>()
            .add_systems(Update, (
                navigation_grid_update_system,
                collect_path_results_system,
                path_follower_system,
            ));
    }
}

/// System to track static colliders (and dynamic obstacle items) and update the NavigationGrid.
pub fn navigation_grid_update_system(
    nav_service: Option<Res<NavigationService>>,
    mut last_obstacles: Local<HashMap<Entity, (Vec2, Vec2, u8)>>,
    query: Query<(Entity, &RigidBody, &ColliderAabb)>,
) {
    let nav_service = match nav_service {
        Some(ns) => ns,
        None => return,
    };

    let mut current_obstacles = HashMap::new();

    // 1. Identify all current obstacles
    for (entity, body, aabb) in query.iter() {
        // We track static bodies as obstacles.
        // (Note: In the future, dynamic obstacle items can be tracked if they match certain criteria).
        if matches!(body, RigidBody::Static) {
            let min_pos = aabb.min;
            let max_pos = aabb.max;
            
            // Default block mask for static walls/obstacles is all capabilities
            let block_mask = TRAVERSAL_WALK | TRAVERSAL_FLY | TRAVERSAL_SWIM;
            current_obstacles.insert(entity, (min_pos, max_pos, block_mask));
        }
    }

    let mut grid = nav_service.grid.write().unwrap();
    let mut affected_clusters = HashSet::new();

    // 2. Handle removed obstacles
    for (entity, (old_min, old_max, old_mask)) in last_obstacles.iter() {
        if !current_obstacles.contains_key(entity) {
            let w = old_max.x - old_min.x;
            let h = old_max.y - old_min.y;
            let cx = old_min.x + w / 2.0;
            let cy = old_min.y + h / 2.0;

            grid.update_obstacle_rect(cx, cy, w, h, false, *old_mask);
            
            // Track affected clusters for rebuild
            add_affected_clusters(&grid, cx, cy, w, h, &mut affected_clusters);
        }
    }

    // 3. Handle added or moved obstacles
    for (entity, (new_min, new_max, new_mask)) in current_obstacles.iter() {
        let mut should_update = false;
        if let Some((old_min, old_max, _)) = last_obstacles.get(entity) {
            // Check if it moved significantly
            if (new_min.distance(*old_min) > 1.0) || (new_max.distance(*old_max) > 1.0) {
                // Clear old rect first
                let old_w = old_max.x - old_min.x;
                let old_h = old_max.y - old_min.y;
                let old_cx = old_min.x + old_w / 2.0;
                let old_cy = old_min.y + old_h / 2.0;
                let old_mask = last_obstacles.get(entity).unwrap().2;
                grid.update_obstacle_rect(old_cx, old_cy, old_w, old_h, false, old_mask);
                add_affected_clusters(&grid, old_cx, old_cy, old_w, old_h, &mut affected_clusters);

                should_update = true;
            }
        } else {
            should_update = true;
        }

        if should_update {
            let w = new_max.x - new_min.x;
            let h = new_max.y - new_min.y;
            let cx = new_min.x + w / 2.0;
            let cy = new_min.y + h / 2.0;

            grid.update_obstacle_rect(cx, cy, w, h, true, *new_mask);
            add_affected_clusters(&grid, cx, cy, w, h, &mut affected_clusters);
        }
    }

    // 4. Send rebuild commands if any clusters were affected
    if !affected_clusters.is_empty() {
        for cap in &[TRAVERSAL_WALK, TRAVERSAL_FLY, TRAVERSAL_SWIM] {
            let _ = nav_service.request_tx.send(NavCommand::RebuildClusters {
                capability: *cap,
                affected_clusters: affected_clusters.clone(),
            });
        }
    }

    // 5. Update local state
    *last_obstacles = current_obstacles;
}

fn add_affected_clusters(
    grid: &NavigationGrid,
    x: f32,
    y: f32,
    width: f32,
    height: f32,
    affected: &mut HashSet<(i32, i32)>,
) {
    let half_w = width / 2.0;
    let half_h = height / 2.0;
    let min_gx = ((x - half_w) / grid.grid_step_size) as i32;
    let max_gx = ((x + half_w) / grid.grid_step_size) as i32 + 1;
    let min_gy = ((y - half_h) / grid.grid_step_size) as i32;
    let max_gy = ((y + half_h) / grid.grid_step_size) as i32 + 1;

    let min_cx = min_gx / CLUSTER_SIZE;
    let max_cx = max_gx / CLUSTER_SIZE;
    let min_cy = min_gy / CLUSTER_SIZE;
    let max_cy = max_gy / CLUSTER_SIZE;

    for cx in min_cx..=max_cx {
        for cy in min_cy..=max_cy {
            if cx >= 0 && cy >= 0 {
                affected.insert((cx, cy));
            }
        }
    }
}

/// Receives completed paths from the background worker and updates entity components.
pub fn collect_path_results_system(
    mut commands: Commands,
    nav_service: Option<Res<NavigationService>>,
) {
    let nav_service = match nav_service {
        Some(ns) => ns,
        None => return,
    };

    let lock_res = nav_service.result_rx.lock();
    if let Ok(rx) = lock_res {
        while let Ok(result) = rx.try_recv() {
            if result.success && !result.path.is_empty() {
                commands.entity(result.entity_id).insert(MovementPath {
                    waypoints: result.path.clone(),
                    current_index: 0,
                    acceptance_radius: 25.0,
                });
                commands.entity(result.entity_id).insert(MoveTarget {
                    position: result.path[0],
                    acceptance_radius: 25.0,
                });
            }
        }
    }
}

/// Progresses the entity to the next waypoint when they reach the current one.
pub fn path_follower_system(
    mut commands: Commands,
    mut query: Query<(Entity, &mut MovementPath), Without<MoveTarget>>,
) {
    for (entity, mut path) in query.iter_mut() {
        if path.current_index + 1 < path.waypoints.len() {
            path.current_index += 1;
            let next_pos = path.waypoints[path.current_index];
            commands.entity(entity).insert(MoveTarget {
                position: next_pos,
                acceptance_radius: path.acceptance_radius,
            });
        } else {
            commands.entity(entity).remove::<MovementPath>();
        }
    }
}
