use bevy::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::sync::{Arc, RwLock, Mutex};
use std::sync::mpsc::{channel, Sender, Receiver};

// Traversal capability bitmask
pub const TRAVERSAL_WALK: u8 = 1;
pub const TRAVERSAL_FLY: u8 = 2;
pub const TRAVERSAL_SWIM: u8 = 4;

pub const CLUSTER_SIZE: i32 = 8;

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct GridCell {
    pub access_mask: u8,
    pub cost: f32,
}

#[derive(Resource, Debug, Clone)]
pub struct NavigationGrid {
    pub world_width: f32,
    pub world_height: f32,
    pub grid_step_size: f32,
    pub width: usize,
    pub height: usize,
    pub cells: Vec<GridCell>,
}

impl NavigationGrid {
    pub fn new(world_width: f32, world_height: f32, grid_step_size: f32) -> Self {
        let width = (world_width / grid_step_size).ceil() as usize + 1;
        let height = (world_height / grid_step_size).ceil() as usize + 1;
        let default_mask = TRAVERSAL_WALK | TRAVERSAL_FLY | TRAVERSAL_SWIM;
        let cells = vec![GridCell { access_mask: default_mask, cost: 1.0 }; width * height];
        Self {
            world_width,
            world_height,
            grid_step_size,
            width,
            height,
            cells,
        }
    }

    pub fn is_walkable(&self, gx: i32, gy: i32, capability: u8) -> bool {
        if gx >= 0 && gx < self.width as i32 && gy >= 0 && gy < self.height as i32 {
            let idx = (gx as usize) * self.height + (gy as usize);
            (self.cells[idx].access_mask & capability) == capability
        } else {
            false
        }
    }

    pub fn get_cost(&self, gx: i32, gy: i32) -> f32 {
        if gx >= 0 && gx < self.width as i32 && gy >= 0 && gy < self.height as i32 {
            let idx = (gx as usize) * self.height + (gy as usize);
            self.cells[idx].cost
        } else {
            1.0
        }
    }

    pub fn set_obstacle(&mut self, gx: i32, gy: i32, mask: u8, cost: f32) {
        if gx >= 0 && gx < self.width as i32 && gy >= 0 && gy < self.height as i32 {
            let idx = (gx as usize) * self.height + (gy as usize);
            self.cells[idx].access_mask = mask;
            self.cells[idx].cost = cost;
        }
    }

    pub fn update_obstacle_rect(
        &mut self,
        world_x: f32,
        world_y: f32,
        width: f32,
        height: f32,
        is_blocking: bool,
        block_mask: u8,
    ) {
        let min_x = ((world_x - width / 2.0) / self.grid_step_size).floor() as i32;
        let max_x = ((world_x + width / 2.0) / self.grid_step_size).ceil() as i32;
        let min_y = ((world_y - height / 2.0) / self.grid_step_size).floor() as i32;
        let max_y = ((world_y + height / 2.0) / self.grid_step_size).ceil() as i32;

        let min_x = min_x.clamp(0, self.width as i32 - 1) as usize;
        let max_x = max_x.clamp(0, self.width as i32 - 1) as usize;
        let min_y = min_y.clamp(0, self.height as i32 - 1) as usize;
        let max_y = max_y.clamp(0, self.height as i32 - 1) as usize;

        for gx in min_x..=max_x {
            for gy in min_y..=max_y {
                let idx = gx * self.height + gy;
                if is_blocking {
                    self.cells[idx].access_mask &= !block_mask;
                } else {
                    self.cells[idx].access_mask |= block_mask;
                }
            }
        }
    }

    pub fn to_grid(&self, pos: Vec2) -> (i32, i32) {
        let gx = (pos.x / self.grid_step_size).round() as i32;
        let gy = (pos.y / self.grid_step_size).round() as i32;
        (
            gx.clamp(0, self.width as i32 - 1),
            gy.clamp(0, self.height as i32 - 1),
        )
    }

    pub fn to_world(&self, gx: i32, gy: i32) -> Vec2 {
        Vec2::new(
            (gx as f32) * self.grid_step_size,
            (gy as f32) * self.grid_step_size,
        )
    }
}

pub struct AStar;

impl AStar {
    pub fn heuristic(a: (i32, i32), b: (i32, i32)) -> f32 {
        let dx = (a.0 - b.0).abs() as f32;
        let dy = (a.1 - b.1).abs() as f32;
        let sqrt2_minus_2 = std::f32::consts::SQRT_2 - 2.0;
        (dx + dy) + sqrt2_minus_2 * dx.min(dy)
    }

    pub fn search(
        grid: &NavigationGrid,
        start: (i32, i32),
        goal: (i32, i32),
        capability: u8,
        bounds: Option<(i32, i32, i32, i32)>,
    ) -> Option<Vec<(i32, i32)>> {
        use std::collections::{BinaryHeap, HashMap, HashSet};
        use std::cmp::Ordering;

        #[derive(Copy, Clone, PartialEq)]
        struct State {
            priority: f32,
            pos: (i32, i32),
        }

        impl Eq for State {}

        impl Ord for State {
            fn cmp(&self, other: &Self) -> Ordering {
                other.priority.partial_cmp(&self.priority).unwrap_or(Ordering::Equal)
            }
        }

        impl PartialOrd for State {
            fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
                Some(self.cmp(other))
            }
        }

        let mut frontier = BinaryHeap::new();
        frontier.push(State { priority: 0.0, pos: start });

        let mut came_from: HashMap<(i32, i32), Option<(i32, i32)>> = HashMap::new();
        came_from.insert(start, None);

        let mut cost_so_far: HashMap<(i32, i32), f32> = HashMap::new();
        cost_so_far.insert(start, 0.0);

        let mut visited = HashSet::new();

        while let Some(State { pos: current, .. }) = frontier.pop() {
            if current == goal {
                break;
            }

            if visited.contains(&current) {
                continue;
            }
            visited.insert(current);

            let (x, y) = current;
            let neighbors = [
                (x + 1, y),
                (x - 1, y),
                (x, y + 1),
                (x, y - 1),
                (x + 1, y + 1),
                (x + 1, y - 1),
                (x - 1, y + 1),
                (x - 1, y - 1),
            ];

            for (i, next_pos) in neighbors.iter().enumerate() {
                let (nx, ny) = *next_pos;

                // Check bounds filter if specified
                if let Some((min_x, min_y, max_x, max_y)) = bounds {
                    if nx < min_x || nx > max_x || ny < min_y || ny > max_y {
                        continue;
                    }
                }

                // Check grid walkability
                if !grid.is_walkable(nx, ny, capability) {
                    continue;
                }

                let dist = if i >= 4 { std::f32::consts::SQRT_2 } else { 1.0 };
                let base_cost = grid.get_cost(nx, ny);
                let current_cost = cost_so_far.get(&current).copied().unwrap_or(0.0);
                let new_cost = current_cost + (base_cost * dist);

                if !cost_so_far.contains_key(next_pos) || new_cost < cost_so_far[next_pos] {
                    cost_so_far.insert(*next_pos, new_cost);
                    let priority = new_cost + Self::heuristic(*next_pos, goal);
                    frontier.push(State { priority, pos: *next_pos });
                    came_from.insert(*next_pos, Some(current));
                }
            }
        }

        if !came_from.contains_key(&goal) {
            return None;
        }

        let mut path = Vec::new();
        let mut curr = Some(goal);
        while let Some(p) = curr {
            path.push(p);
            curr = came_from.get(&p).copied().flatten();
        }
        path.reverse();
        Some(path)
    }
}

#[derive(Debug, Clone)]
pub struct GraphEdge {
    pub target_node_id: String,
    pub weight: f32,
}

#[derive(Debug, Clone)]
pub struct GraphNode {
    pub id: String,
    pub position: (i32, i32),
    pub edges: Vec<GraphEdge>,
    pub cluster_coords: (i32, i32),
}

#[derive(Debug, Clone)]
pub struct Cluster {
    pub cx: i32,
    pub cy: i32,
    pub min_x: i32,
    pub min_y: i32,
    pub max_x: i32,
    pub max_y: i32,
    pub nodes: HashMap<(i32, i32), String>,
}

#[derive(Debug, Clone)]
pub struct ClusterGraph {
    pub cluster_w: i32,
    pub cluster_h: i32,
    pub clusters: HashMap<(i32, i32), Cluster>,
    pub graph_nodes: HashMap<String, GraphNode>,
}

impl ClusterGraph {
    pub fn new(grid: &NavigationGrid) -> Self {
        let cluster_w = (grid.width as f32 / CLUSTER_SIZE as f32).ceil() as i32;
        let cluster_h = (grid.height as f32 / CLUSTER_SIZE as f32).ceil() as i32;

        let mut clusters = HashMap::new();
        for cy in 0..cluster_h {
            for cx in 0..cluster_w {
                let min_x = cx * CLUSTER_SIZE;
                let min_y = cy * CLUSTER_SIZE;
                let max_x = ((cx + 1) * CLUSTER_SIZE - 1).min(grid.width as i32 - 1);
                let max_y = ((cy + 1) * CLUSTER_SIZE - 1).min(grid.height as i32 - 1);

                clusters.insert((cx, cy), Cluster {
                    cx,
                    cy,
                    min_x,
                    min_y,
                    max_x,
                    max_y,
                    nodes: HashMap::new(),
                });
            }
        }

        Self {
            cluster_w,
            cluster_h,
            clusters,
            graph_nodes: HashMap::new(),
        }
    }

    pub fn build_graph(&mut self, grid: &NavigationGrid, capability: u8) {
        self.graph_nodes.clear();
        for cluster in self.clusters.values_mut() {
            cluster.nodes.clear();
        }

        // 1. Horizontal borders (Left <-> Right)
        for cy in 0..self.cluster_h {
            for cx in 0..(self.cluster_w - 1) {
                let c1_max_x = self.clusters[&(cx, cy)].max_x;
                self._find_entrances(grid, (cx, cy), (cx + 1, cy), c1_max_x, true, capability);
            }
        }

        // 2. Vertical borders (Top <-> Bottom)
        for cx in 0..self.cluster_w {
            for cy in 0..(self.cluster_h - 1) {
                let c1_max_y = self.clusters[&(cx, cy)].max_y;
                self._find_entrances(grid, (cx, cy), (cx, cy + 1), c1_max_y, false, capability);
            }
        }

        // 3. Connect nodes internally within each cluster
        let coords: Vec<(i32, i32)> = self.clusters.keys().cloned().collect();
        for coord in coords {
            self._connect_internal_nodes(grid, coord, capability);
        }
    }

    fn _find_entrances(
        &mut self,
        grid: &NavigationGrid,
        c1_coord: (i32, i32),
        c2_coord: (i32, i32),
        border_idx: i32,
        is_horizontal: bool,
        capability: u8,
    ) {
        let (shared_len, start_k) = {
            let c1 = self.clusters.get(&c1_coord).unwrap();
            let c2 = self.clusters.get(&c2_coord).unwrap();
            if is_horizontal {
                (c1.max_y.min(c2.max_y) - c1.min_y.max(c2.min_y) + 1, c1.min_y.max(c2.min_y))
            } else {
                (c1.max_x.min(c2.max_x) - c1.min_x.max(c2.min_x) + 1, c1.min_x.max(c2.min_x))
            }
        };

        let mut current_gap_start = -1;

        for k in start_k..(start_k + shared_len) {
            let (pos1, pos2) = if is_horizontal {
                ((border_idx, k), (border_idx + 1, k))
            } else {
                ((k, border_idx), (k, border_idx + 1))
            };

            let walkable = grid.is_walkable(pos1.0, pos1.1, capability)
                && grid.is_walkable(pos2.0, pos2.1, capability);

            if walkable {
                if current_gap_start == -1 {
                    current_gap_start = k;
                }
            } else {
                if current_gap_start != -1 {
                    self._create_inter_cluster_edge(
                        c1_coord,
                        c2_coord,
                        border_idx,
                        current_gap_start,
                        k - 1,
                        is_horizontal,
                    );
                    current_gap_start = -1;
                }
            }
        }

        if current_gap_start != -1 {
            self._create_inter_cluster_edge(
                c1_coord,
                c2_coord,
                border_idx,
                current_gap_start,
                start_k + shared_len - 1,
                is_horizontal,
            );
        }
    }

    fn _create_inter_cluster_edge(
        &mut self,
        c1_coord: (i32, i32),
        c2_coord: (i32, i32),
        border_val: i32,
        start_k: i32,
        end_k: i32,
        is_horizontal: bool,
    ) {
        let mid_k = (start_k + end_k) / 2;
        let (pos1, pos2) = if is_horizontal {
            ((border_val, mid_k), (border_val + 1, mid_k))
        } else {
            ((mid_k, border_val), (mid_k, border_val + 1))
        };

        let node1_id = self._get_or_create_node(c1_coord, pos1);
        let node2_id = self._get_or_create_node(c2_coord, pos2);

        let cost = 1.0;
        self.graph_nodes.get_mut(&node1_id).unwrap().edges.push(GraphEdge {
            target_node_id: node2_id.clone(),
            weight: cost,
        });
        self.graph_nodes.get_mut(&node2_id).unwrap().edges.push(GraphEdge {
            target_node_id: node1_id,
            weight: cost,
        });
    }

    fn _get_or_create_node(&mut self, c_coord: (i32, i32), pos: (i32, i32)) -> String {
        let cluster = self.clusters.get(&c_coord).unwrap();
        if let Some(id) = cluster.nodes.get(&pos) {
            return id.clone();
        }

        let node_id = format!("{}_{}", pos.0, pos.1);
        let node = GraphNode {
            id: node_id.clone(),
            position: pos,
            edges: Vec::new(),
            cluster_coords: c_coord,
        };
        self.graph_nodes.insert(node_id.clone(), node);

        let cluster = self.clusters.get_mut(&c_coord).unwrap();
        cluster.nodes.insert(pos, node_id.clone());

        node_id
    }

    fn _connect_internal_nodes(&mut self, grid: &NavigationGrid, c_coord: (i32, i32), capability: u8) {
        let cluster = self.clusters.get(&c_coord).unwrap();
        let nodes_in_cluster: Vec<String> = cluster.nodes.values().cloned().collect();

        for i in 0..nodes_in_cluster.len() {
            for j in (i + 1)..nodes_in_cluster.len() {
                let id1 = &nodes_in_cluster[i];
                let id2 = &nodes_in_cluster[j];

                let pos1 = self.graph_nodes[id1].position;
                let pos2 = self.graph_nodes[id2].position;

                let bounds = Some((cluster.min_x, cluster.min_y, cluster.max_x, cluster.max_y));
                if let Some(path) = AStar::search(grid, pos1, pos2, capability, bounds) {
                    let cost = self._calculate_path_cost(grid, &path);
                    
                    self.graph_nodes.get_mut(id1).unwrap().edges.push(GraphEdge {
                        target_node_id: id2.clone(),
                        weight: cost,
                    });
                    self.graph_nodes.get_mut(id2).unwrap().edges.push(GraphEdge {
                        target_node_id: id1.clone(),
                        weight: cost,
                    });
                }
            }
        }
    }

    fn _calculate_path_cost(&self, grid: &NavigationGrid, path: &[(i32, i32)]) -> f32 {
        let mut cost = 0.0;
        for i in 0..(path.len() - 1) {
            let p_a = path[i];
            let p_b = path[i + 1];
            let dist = (((p_a.0 - p_b.0) as f32).powi(2) + ((p_a.1 - p_b.1) as f32).powi(2)).sqrt();
            cost += grid.get_cost(p_b.0, p_b.1) * dist;
        }
        cost
    }

    pub fn get_cluster_for_pos(&self, pos: (i32, i32)) -> Option<&Cluster> {
        let cx = pos.0 / CLUSTER_SIZE;
        let cy = pos.1 / CLUSTER_SIZE;
        self.clusters.get(&(cx, cy))
    }

    pub fn rebuild_clusters(
        &mut self,
        grid: &NavigationGrid,
        affected_clusters: &HashSet<(i32, i32)>,
        capability: u8,
    ) {
        if affected_clusters.is_empty() {
            return;
        }

        let mut expanded = HashSet::new();
        for &(cx, cy) in affected_clusters {
            for dx in -1..=1 {
                for dy in -1..=1 {
                    let coord = (cx + dx, cy + dy);
                    if self.clusters.contains_key(&coord) {
                        expanded.insert(coord);
                    }
                }
            }
        }

        let mut nodes_to_remove = Vec::new();
        for (nid, node) in &self.graph_nodes {
            if expanded.contains(&node.cluster_coords) && !nid.starts_with("temp_") {
                nodes_to_remove.push(nid.clone());
            }
        }

        for nid in &nodes_to_remove {
            self.graph_nodes.remove(nid);
        }

        for coord in &expanded {
            if let Some(cluster) = self.clusters.get_mut(coord) {
                cluster.nodes.clear();
            }
        }

        let removed_set: HashSet<String> = nodes_to_remove.into_iter().collect();
        for node in self.graph_nodes.values_mut() {
            node.edges.retain(|e| !removed_set.contains(&e.target_node_id));
        }

        for &(cx, cy) in &expanded {
            let right_coord = (cx + 1, cy);
            if self.clusters.contains_key(&right_coord) {
                let max_x = self.clusters[&(cx, cy)].max_x;
                self._find_entrances(grid, (cx, cy), right_coord, max_x, true, capability);
            }

            let down_coord = (cx, cy + 1);
            if self.clusters.contains_key(&down_coord) {
                let max_y = self.clusters[&(cx, cy)].max_y;
                self._find_entrances(grid, (cx, cy), down_coord, max_y, false, capability);
            }
        }

        for &coord in &expanded {
            self._connect_internal_nodes(grid, coord, capability);
        }
    }

    pub fn insert_temporary_node(
        &mut self,
        grid: &NavigationGrid,
        pos: (i32, i32),
        capability: u8,
    ) -> Option<GraphNode> {
        if !grid.is_walkable(pos.0, pos.1, capability) {
            return None;
        }

        let cx = pos.0 / CLUSTER_SIZE;
        let cy = pos.1 / CLUSTER_SIZE;
        let cluster_coords = (cx, cy);

        let existing_id = {
            let cluster = self.clusters.get(&cluster_coords)?;
            cluster.nodes.get(&pos).cloned()
        };

        if let Some(id) = existing_id {
            return self.graph_nodes.get(&id).cloned();
        }

        let node_id = format!("temp_{}_{}", pos.0, pos.1);
        let mut node = GraphNode {
            id: node_id.clone(),
            position: pos,
            edges: Vec::new(),
            cluster_coords,
        };

        let cluster = self.clusters.get(&cluster_coords)?;
        let existing_nodes: Vec<(String, (i32, i32))> = cluster.nodes.values()
            .map(|nid| (nid.clone(), self.graph_nodes[nid].position))
            .collect();

        for (exist_id, exist_pos) in existing_nodes {
            let bounds = Some((cluster.min_x, cluster.min_y, cluster.max_x, cluster.max_y));
            if let Some(path) = AStar::search(grid, pos, exist_pos, capability, bounds) {
                let cost = self._calculate_path_cost(grid, &path);
                node.edges.push(GraphEdge {
                    target_node_id: exist_id.clone(),
                    weight: cost,
                });
                self.graph_nodes.get_mut(&exist_id).unwrap().edges.push(GraphEdge {
                    target_node_id: node_id.clone(),
                    weight: cost,
                });
            }
        }

        self.graph_nodes.insert(node_id.clone(), node.clone());
        Some(node)
    }

    pub fn remove_temporary_node(&mut self, node_id: &str) {
        if !self.graph_nodes.contains_key(node_id) {
            return;
        }

        for node in self.graph_nodes.values_mut() {
            node.edges.retain(|e| e.target_node_id != node_id);
        }

        self.graph_nodes.remove(node_id);
    }

    pub fn abstract_search(&self, start_id: &str, goal_id: &str) -> Option<Vec<String>> {
        if start_id == goal_id {
            return Some(vec![start_id.to_string()]);
        }

        use std::collections::{BinaryHeap, HashMap, HashSet};
        use std::cmp::Ordering;

        #[derive(Clone, PartialEq)]
        struct State {
            priority: f32,
            node_id: String,
        }

        impl Eq for State {}

        impl Ord for State {
            fn cmp(&self, other: &Self) -> Ordering {
                other.priority.partial_cmp(&self.priority).unwrap_or(Ordering::Equal)
            }
        }

        impl PartialOrd for State {
            fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
                Some(self.cmp(other))
            }
        }

        let mut frontier = BinaryHeap::new();
        frontier.push(State { priority: 0.0, node_id: start_id.to_string() });

        let mut came_from: HashMap<String, Option<String>> = HashMap::new();
        came_from.insert(start_id.to_string(), None);

        let mut cost_so_far: HashMap<String, f32> = HashMap::new();
        cost_so_far.insert(start_id.to_string(), 0.0);

        let mut visited = HashSet::new();

        let goal_pos = self.graph_nodes.get(goal_id)?.position;

        while let Some(State { node_id: current_id, .. }) = frontier.pop() {
            if current_id == goal_id {
                break;
            }

            if visited.contains(&current_id) {
                continue;
            }
            visited.insert(current_id.clone());

            let current_node = match self.graph_nodes.get(&current_id) {
                Some(n) => n,
                None => continue,
            };

            for edge in &current_node.edges {
                let next_id = &edge.target_node_id;
                let next_node = match self.graph_nodes.get(next_id) {
                    Some(n) => n,
                    None => continue,
                };

                let current_cost = cost_so_far.get(&current_id).copied().unwrap_or(0.0);
                let new_cost = current_cost + edge.weight;

                if !cost_so_far.contains_key(next_id) || new_cost < cost_so_far[next_id] {
                    cost_so_far.insert(next_id.clone(), new_cost);
                    let h = AStar::heuristic(next_node.position, goal_pos);
                    let priority = new_cost + h;
                    frontier.push(State { priority, node_id: next_id.clone() });
                    came_from.insert(next_id.clone(), Some(current_id.clone()));
                }
            }
        }

        if !came_from.contains_key(goal_id) {
            return None;
        }

        let mut path = Vec::new();
        let mut curr = Some(goal_id.to_string());
        while let Some(node_id) = curr {
            path.push(node_id.clone());
            curr = came_from.get(&node_id).cloned().flatten();
        }
        path.reverse();
        Some(path)
    }

    pub fn refine_abstract_path(
        &self,
        grid: &NavigationGrid,
        abstract_path: &[String],
        capability: u8,
    ) -> Option<Vec<(i32, i32)>> {
        if abstract_path.is_empty() {
            return None;
        }
        if abstract_path.len() == 1 {
            let node = self.graph_nodes.get(&abstract_path[0])?;
            return Some(vec![node.position]);
        }

        let mut detailed_path = Vec::new();

        for i in 0..(abstract_path.len() - 1) {
            let node_a = self.graph_nodes.get(&abstract_path[i])?;
            let node_b = self.graph_nodes.get(&abstract_path[i + 1])?;

            let bounds = if node_a.cluster_coords == node_b.cluster_coords {
                let cluster = self.clusters.get(&node_a.cluster_coords)?;
                Some((cluster.min_x, cluster.min_y, cluster.max_x, cluster.max_y))
            } else {
                None
            };

            let mut segment = AStar::search(grid, node_a.position, node_b.position, capability, bounds);
            if segment.is_none() {
                segment = AStar::search(grid, node_a.position, node_b.position, capability, None);
            }

            let segment_points = segment?;
            if !detailed_path.is_empty() && detailed_path[detailed_path.len() - 1] == segment_points[0] {
                detailed_path.extend_from_slice(&segment_points[1..]);
            } else {
                detailed_path.extend_from_slice(&segment_points);
            }
        }

        Some(detailed_path)
    }
}

pub struct StringPuller;

impl StringPuller {
    pub const LOOKAHEAD_LIMIT: usize = 20;

    pub fn smooth_path(
        path: &[(i32, i32)],
        grid: &NavigationGrid,
        capability: u8,
    ) -> Vec<(i32, i32)> {
        if path.len() <= 2 {
            return path.to_vec();
        }

        let mut smoothed_path = vec![path[0]];
        let mut current_idx = 0;

        while current_idx < path.len() - 1 {
            let look_end = (path.len() - 1).min(current_idx + Self::LOOKAHEAD_LIMIT);
            let mut found_shortcut = false;

            for lookahead_idx in (current_idx + 2..=look_end).rev() {
                if Self::has_line_of_sight(grid, path[current_idx], path[lookahead_idx], capability) {
                    smoothed_path.push(path[lookahead_idx]);
                    current_idx = lookahead_idx;
                    found_shortcut = true;
                    break;
                }
            }

            if !found_shortcut {
                current_idx += 1;
                smoothed_path.push(path[current_idx]);
            }
        }

        smoothed_path
    }

    pub fn has_line_of_sight(
        grid: &NavigationGrid,
        start: (i32, i32),
        end: (i32, i32),
        capability: u8,
    ) -> bool {
        let x0 = start.0;
        let y0 = start.1;
        let x1 = end.0;
        let y1 = end.1;

        let dx = (x1 - x0).abs();
        let dy = (y1 - y0).abs();
        let mut x = x0;
        let mut y = y0;
        let n = 1 + dx + dy;
        let x_inc = if x1 > x0 { 1 } else { -1 };
        let y_inc = if y1 > y0 { 1 } else { -1 };
        let mut error = dx - dy;
        let double_dx = dx * 2;
        let double_dy = dy * 2;

        for _ in 0..n {
            if !grid.is_walkable(x, y, capability) {
                return false;
            }

            if x == x1 && y == y1 {
                break;
            }

            if error > 0 {
                x += x_inc;
                error -= double_dy;
            } else {
                y += y_inc;
                error += double_dx;
            }
        }

        true
    }
}

#[derive(Debug, Clone)]
pub struct PathRequest {
    pub entity_id: Entity,
    pub start: (i32, i32),
    pub end: (i32, i32),
    pub capabilities: u8,
    pub end_world: Option<Vec2>,
}

#[derive(Debug, Clone)]
pub struct PathResult {
    pub entity_id: Entity,
    pub path: Vec<Vec2>,
    pub success: bool,
}

pub enum NavCommand {
    RequestPath(PathRequest),
    RebuildClusters {
        capability: u8,
        affected_clusters: HashSet<(i32, i32)>,
    },
    RebuildAll,
}

#[derive(Resource)]
pub struct NavigationService {
    pub request_tx: Sender<NavCommand>,
    pub result_rx: Mutex<Receiver<PathResult>>,
    pub grid: Arc<RwLock<NavigationGrid>>,
}

impl NavigationService {
    pub fn reset(&self) {
        if let Ok(mut grid) = self.grid.write() {
            let default_mask = TRAVERSAL_WALK | TRAVERSAL_FLY | TRAVERSAL_SWIM;
            for cell in &mut grid.cells {
                cell.access_mask = default_mask;
                cell.cost = 1.0;
            }
        }
        let _ = self.request_tx.send(NavCommand::RebuildAll);
    }

    pub fn new(world_width: f32, world_height: f32, grid_step_size: f32) -> Self {
        let grid = Arc::new(RwLock::new(NavigationGrid::new(world_width, world_height, grid_step_size)));
        let (request_tx, request_rx) = channel::<NavCommand>();
        let (result_tx, result_rx) = channel::<PathResult>();

        let result_rx = Mutex::new(result_rx);

        let grid_clone = Arc::clone(&grid);

        // Spawn background worker thread
        std::thread::spawn(move || {
            let mut cluster_graphs: HashMap<u8, ClusterGraph> = HashMap::new();
            
            // Pre-initialize graphs for capabilities WALK=1, FLY=2, SWIM=4
            for cap in &[TRAVERSAL_WALK, TRAVERSAL_FLY, TRAVERSAL_SWIM] {
                let grid_read = grid_clone.read().unwrap();
                let mut graph = ClusterGraph::new(&grid_read);
                graph.build_graph(&grid_read, *cap);
                cluster_graphs.insert(*cap, graph);
            }

            while let Ok(cmd) = request_rx.recv() {
                match cmd {
                    NavCommand::RequestPath(req) => {
                        let grid_read = grid_clone.read().unwrap();
                        let graph = cluster_graphs.get_mut(&req.capabilities);
                        if let Some(graph) = graph {
                            let result = Self::process_request(&grid_read, graph, &req);
                            let _ = result_tx.send(result);
                        } else {
                            let _ = result_tx.send(PathResult {
                                entity_id: req.entity_id,
                                path: Vec::new(),
                                success: false,
                            });
                        }
                    }
                    NavCommand::RebuildClusters { capability, affected_clusters } => {
                        let grid_read = grid_clone.read().unwrap();
                        if let Some(graph) = cluster_graphs.get_mut(&capability) {
                            graph.rebuild_clusters(&grid_read, &affected_clusters, capability);
                        }
                    }
                    NavCommand::RebuildAll => {
                        let grid_read = grid_clone.read().unwrap();
                        for (cap, graph) in &mut cluster_graphs {
                            graph.build_graph(&grid_read, *cap);
                        }
                    }
                }
            }
        });

        Self {
            request_tx,
            result_rx,
            grid,
        }
    }

    fn process_request(
        grid: &NavigationGrid,
        graph: &mut ClusterGraph,
        req: &PathRequest,
    ) -> PathResult {
        let start_pos = req.start;
        let end_pos = req.end;
        let capability = req.capabilities;

        if start_pos == end_pos {
            let dest_pos = req.end_world.unwrap_or_else(|| grid.to_world(end_pos.0, end_pos.1));
            return PathResult {
                entity_id: req.entity_id,
                path: vec![dest_pos],
                success: true,
            };
        }

        let start_node = match graph.insert_temporary_node(grid, start_pos, capability) {
            Some(n) => n,
            None => {
                return PathResult {
                    entity_id: req.entity_id,
                    path: Vec::new(),
                    success: false,
                };
            }
        };

        let goal_node = match graph.insert_temporary_node(grid, end_pos, capability) {
            Some(n) => n,
            None => {
                graph.remove_temporary_node(&start_node.id);
                return PathResult {
                    entity_id: req.entity_id,
                    path: Vec::new(),
                    success: false,
                };
            }
        };

        let mut path_found = false;
        let mut final_path = Vec::new();

        if start_node.cluster_coords == goal_node.cluster_coords {
            let cluster = graph.clusters.get(&start_node.cluster_coords).unwrap();
            let bounds = Some((cluster.min_x, cluster.min_y, cluster.max_x, cluster.max_y));
            if let Some(local_path) = AStar::search(grid, start_pos, end_pos, capability, bounds) {
                final_path = local_path;
                path_found = true;
            }
        }

        if !path_found {
            if let Some(abstract_path) = graph.abstract_search(&start_node.id, &goal_node.id) {
                if let Some(refined) = graph.refine_abstract_path(grid, &abstract_path, capability) {
                    final_path = refined;
                    path_found = true;
                }
            }
        }

        graph.remove_temporary_node(&start_node.id);
        graph.remove_temporary_node(&goal_node.id);

        if path_found && !final_path.is_empty() {
            let smoothed = StringPuller::smooth_path(&final_path, grid, capability);
            let world_path = smoothed.into_iter().map(|p| grid.to_world(p.0, p.1)).collect();
            PathResult {
                entity_id: req.entity_id,
                path: world_path,
                success: true,
            }
        } else {
            PathResult {
                entity_id: req.entity_id,
                path: Vec::new(),
                success: false,
            }
        }
    }
}
