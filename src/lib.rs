pub mod ai;
pub mod prefabs;
pub mod render;
pub mod camera;
pub mod audio;
pub mod ui;
pub mod simulation;

use bevy::prelude::States;

#[derive(States, Debug, Clone, Copy, Eq, PartialEq, Hash, Default)]
pub enum GameState {
    #[default]
    MainMenu,
    Gameplay,
}
