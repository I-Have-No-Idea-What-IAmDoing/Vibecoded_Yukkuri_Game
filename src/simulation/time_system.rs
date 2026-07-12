use bevy::prelude::*;
use crate::ai::persistence::TimeElapsed;

/// Plugin for managing virtual game time ticking.
pub struct TimeSystemPlugin;

impl Plugin for TimeSystemPlugin {
    fn build(&self, app: &mut App) {
        if !app.world().contains_resource::<TimeElapsed>() {
            app.init_resource::<TimeElapsed>();
        }
        app.add_systems(Update, time_tick_system);
    }
}

/// System to tick virtual game time based on scale and game speed.
pub fn time_tick_system(
    time: Res<Time>,
    mut time_elapsed: ResMut<TimeElapsed>,
) {
    let game_dt = time.delta_secs() * time_elapsed.scale * time_elapsed.game_speed;
    time_elapsed.elapsed += game_dt;
}
