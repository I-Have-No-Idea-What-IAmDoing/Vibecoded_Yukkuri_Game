pub mod needs;
pub mod lifecycle;
pub mod social;
pub mod skills;
pub mod hpa;
pub mod navigation;
pub mod mount;
pub mod inventory;
pub mod movement;
pub mod time_system;
pub mod lod;
pub mod player_actions;
pub mod kinematic_controller;

use bevy::prelude::*;
use needs::NeedsSimulationPlugin;
use lifecycle::LifecycleSimulationPlugin;
use social::SocialSimulationPlugin;
use skills::SkillsSimulationPlugin;
use navigation::NavigationSimulationPlugin;
use mount::MountSimulationPlugin;
use inventory::InventorySimulationPlugin;
use movement::MovementSimulationPlugin;
use time_system::TimeSystemPlugin;
use lod::LODPlugin;
use player_actions::PlayerActionsPlugin;
use kinematic_controller::KinematicControllerPlugin;

/// Main simulation plugin that aggregates all simulation modules.
pub struct SimulationPlugin;

impl Plugin for SimulationPlugin {
    fn build(&self, app: &mut App) {
        app.add_plugins((
            NeedsSimulationPlugin,
            LifecycleSimulationPlugin,
            SocialSimulationPlugin,
            SkillsSimulationPlugin,
            NavigationSimulationPlugin,
            MountSimulationPlugin,
            InventorySimulationPlugin,
            MovementSimulationPlugin,
            TimeSystemPlugin,
            LODPlugin,
            PlayerActionsPlugin,
            KinematicControllerPlugin,
        ));
    }
}
