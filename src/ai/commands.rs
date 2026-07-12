use pyo3::prelude::*;
use std::collections::HashMap;
use serde::{Serialize, Deserialize};

#[pyclass(eq, eq_int)]
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum CommandType {
    MoveTo,
    Flee,
    Speak,
    PlayAnimation,
    Attack,
    Interact,
    ModifyStat,
}

#[pyclass]
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Command {
    #[pyo3(get, set)]
    pub cmd_type: CommandType,
    #[pyo3(get, set)]
    pub entity_id: u32,
    #[pyo3(get, set)]
    pub payload: HashMap<String, String>,
}

#[pymethods]
impl Command {
    #[new]
    pub fn new(cmd_type: CommandType, entity_id: u32, payload: HashMap<String, String>) -> Self {
        Self {
            cmd_type,
            entity_id,
            payload,
        }
    }
}

impl Command {
    /// Helper to get a converted coordinate (e.g. "target_x", "target_y") from Python's coordinate system
    /// back to Bevy's coordinate system.
    pub fn get_bevy_coordinate(&self, x_key: &str, y_key: &str, world_height: f32) -> Option<(f32, f32)> {
        let x_str = self.payload.get(x_key)?;
        let y_str = self.payload.get(y_key)?;
        let x = x_str.parse::<f32>().ok()?;
        let py_y = y_str.parse::<f32>().ok()?;
        let bevy_y = world_height - py_y;
        Some((x, bevy_y))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_command_coordinate_conversion() {
        let mut payload = HashMap::new();
        payload.insert("target_x".to_string(), "100.0".to_string());
        payload.insert("target_y".to_string(), "450.0".to_string());
        let cmd = Command::new(CommandType::MoveTo, 1, payload);
        let coords = cmd.get_bevy_coordinate("target_x", "target_y", 600.0);
        assert_eq!(coords, Some((100.0, 150.0))); // 600 - 450 = 150
    }
}

