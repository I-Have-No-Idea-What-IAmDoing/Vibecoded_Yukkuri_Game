// Removed PyO3
use std::collections::{HashMap, HashSet};
use serde::{Serialize, Deserialize};

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct TargetInfo {
    pub entity_id: u32,
    pub stable_id: u64,
    pub type_id: String,
    pub growth_stage: String,
    pub x: f32,
    pub y: f32, // Python Y-down coordinate
    pub distance: f32,
    pub affinity: f32,
    pub is_threat: bool,
    pub is_prey: bool,
    pub is_family: bool,
    pub tags: HashSet<String>,
    #[serde(default)]
    pub detected_at: f32,
}

impl TargetInfo {
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        entity_id: u32,
        stable_id: u64,
        type_id: String,
        growth_stage: String,
        x: f32,
        y: f32,
        distance: f32,
        affinity: f32,
        is_threat: bool,
        is_prey: bool,
        is_family: bool,
        tags: HashSet<String>,
    ) -> Self {
        Self {
            entity_id,
            stable_id,
            type_id,
            growth_stage,
            x,
            y,
            distance,
            affinity,
            is_threat,
            is_prey,
            is_family,
            tags,
            detected_at: 0.0,
        }
    }
}

impl TargetInfo {
    /// Creates a TargetInfo converting Bevy coordinates to Python Y-down coordinates.
    #[allow(clippy::too_many_arguments)]
    pub fn from_bevy(
        entity_id: u32,
        stable_id: u64,
        type_id: String,
        growth_stage: String,
        bevy_x: f32,
        bevy_y: f32,
        world_height: f32,
        distance: f32,
        affinity: f32,
        is_threat: bool,
        is_prey: bool,
        is_family: bool,
        tags: HashSet<String>,
        detected_at: f32,
    ) -> Self {
        let python_y = world_height - bevy_y;
        Self {
            entity_id,
            stable_id,
            type_id,
            growth_stage,
            x: bevy_x,
            y: python_y,
            distance,
            affinity,
            is_threat,
            is_prey,
            is_family,
            tags,
            detected_at,
        }
    }
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Blackboard {
    pub entity_id: u32,
    pub stats: HashMap<String, f32>,
    pub x: f32,
    pub y: f32,
    pub altitude: f32,
    pub flight_state: u32,
    pub visible_targets: Vec<TargetInfo>,
    pub current_action: String,
    pub short_term_memory: HashMap<u32, (f32, f32, f32)>,
    pub type_id: String,
    pub growth_stage: String,
    pub traits: Vec<String>,
    pub skills: HashMap<String, u32>,
    pub parent_id: Option<u32>,
    pub children_ids: Vec<u32>,
    pub inventory: Vec<(String, u32)>,
    pub grid_width: usize,
    pub grid_height: usize,
    pub grid_cells: Vec<u8>,
    pub day: u32,
    pub hour_of_day: f32,
    pub is_night: bool,
    pub elapsed: f32,
}

impl Blackboard {
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        entity_id: u32,
        stats: HashMap<String, f32>,
        x: f32,
        y: f32,
        altitude: f32,
        flight_state: u32,
        visible_targets: Vec<TargetInfo>,
        current_action: String,
        short_term_memory: HashMap<u32, (f32, f32, f32)>,
        type_id: String,
        growth_stage: String,
        traits: Vec<String>,
        skills: HashMap<String, u32>,
        parent_id: Option<u32>,
        children_ids: Vec<u32>,
        inventory: Vec<(String, u32)>,
        grid_width: usize,
        grid_height: usize,
        grid_cells: Vec<u8>,
        day: u32,
        hour_of_day: f32,
        is_night: bool,
        elapsed: f32,
     ) -> Self {
        Self {
            entity_id,
            stats,
            x,
            y,
            altitude,
            flight_state,
            visible_targets,
            current_action,
            short_term_memory,
            type_id,
            growth_stage,
            traits,
            skills,
            parent_id,
            children_ids,
            inventory,
            grid_width,
            grid_height,
            grid_cells,
            day,
            hour_of_day,
            is_night,
            elapsed,
        }
    }

    pub fn is_walkable(&self, gx: i32, gy: i32, capability: u8) -> bool {
        if gx >= 0 && gx < self.grid_width as i32 && gy >= 0 && gy < self.grid_height as i32 {
            let idx = (gx as usize) * self.grid_height + (gy as usize);
            if idx < self.grid_cells.len() {
                (self.grid_cells[idx] & capability) == capability
            } else {
                false
            }
        } else {
            false
        }
    }
}

impl Blackboard {
    /// Creates a Blackboard converting Bevy coordinates to Python Y-down coordinates.
    #[allow(clippy::too_many_arguments)]
    pub fn from_bevy(
        entity_id: u32,
        stats: HashMap<String, f32>,
        bevy_x: f32,
        bevy_y: f32,
        altitude: f32,
        flight_state: u32,
        visible_targets: Vec<TargetInfo>,
        current_action: String,
        bevy_short_term_memory: HashMap<u32, (f32, f32, f32)>,
        world_height: f32,
        type_id: String,
        growth_stage: String,
        traits: Vec<String>,
        skills: HashMap<String, u32>,
        parent_id: Option<u32>,
        children_ids: Vec<u32>,
        inventory: Vec<(String, u32)>,
        grid_width: usize,
        grid_height: usize,
        grid_cells: Vec<u8>,
        day: u32,
        hour_of_day: f32,
        is_night: bool,
        elapsed: f32,
    ) -> Self {
        let python_y = world_height - bevy_y;
        
        // Convert y coordinate in short-term memory too: (x, bevy_y, timestamp) -> (x, python_y, timestamp)
        let python_short_term_memory = bevy_short_term_memory
            .into_iter()
            .map(|(id, (sx, sy, st))| (id, (sx, world_height - sy, st)))
            .collect();

        Self {
            entity_id,
            stats,
            x: bevy_x,
            y: python_y,
            altitude,
            flight_state,
            visible_targets,
            current_action,
            short_term_memory: python_short_term_memory,
            type_id,
            growth_stage,
            traits,
            skills,
            parent_id,
            children_ids,
            inventory,
            grid_width,
            grid_height,
            grid_cells,
            day,
            hour_of_day,
            is_night,
            elapsed,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_target_info_coordinate_conversion() {
        let tags = HashSet::from(["Food".to_string()]);
        let info = TargetInfo::from_bevy(
            1,
            42,
            "reimu".to_string(),
            "Adult".to_string(),
            10.0,
            20.0,
            600.0, // world_height
            5.0,
            1.0,
            false,
            false,
            false,
            tags.clone(),
            0.0,
        );
        assert_eq!(info.x, 10.0);
        assert_eq!(info.y, 580.0); // 600 - 20 = 580
        assert_eq!(info.tags, tags);
    }

    #[test]
    fn test_blackboard_coordinate_conversion() {
        let stats = HashMap::from([("hunger".to_string(), 50.0)]);
        let mut stm = HashMap::new();
        stm.insert(2, (100.0, 150.0, 1.0)); // (sx, sy, st)
        let blackboard = Blackboard::from_bevy(
            1,
            stats,
            50.0,
            100.0,
            0.0,
            0,
            vec![],
            "Idle".to_string(),
            stm,
            600.0, // world_height
            "reimu".to_string(),
            "Adult".to_string(),
            vec![],
            HashMap::new(),
            None,
            vec![],
            vec![],
            0,
            0,
            vec![],
            1,
            12.0,
            false,
            0.0,
        );
        assert_eq!(blackboard.x, 50.0);
        assert_eq!(blackboard.y, 500.0); // 600 - 100 = 500
        assert_eq!(blackboard.short_term_memory.get(&2), Some(&(100.0, 450.0, 1.0))); // 600 - 150 = 450
        assert_eq!(blackboard.day, 1);
        assert_eq!(blackboard.hour_of_day, 12.0);
        assert_eq!(blackboard.is_night, false);
        assert_eq!(blackboard.elapsed, 0.0);
    }
}

