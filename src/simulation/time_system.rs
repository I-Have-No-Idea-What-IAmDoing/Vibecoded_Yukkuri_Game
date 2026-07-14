use bevy::prelude::*;
use crate::ai::persistence::TimeElapsed;

/// Plugin for managing virtual game time ticking.
pub struct TimeSystemPlugin;

impl Plugin for TimeSystemPlugin {
    fn build(&self, app: &mut App) {
        if !app.world().contains_resource::<TimeElapsed>() {
            app.init_resource::<TimeElapsed>();
        }
        app.add_systems(Update, (
            sync_virtual_time_speed_system,
            time_tick_system,
            keyboard_time_speed_system.run_if(in_state(crate::GameState::Gameplay)),
        ));
    }
}

pub fn sync_virtual_time_speed_system(
    time_elapsed: Res<TimeElapsed>,
    mut virtual_time: ResMut<Time<Virtual>>,
) {
    if (virtual_time.relative_speed() - time_elapsed.game_speed).abs() > 0.001 {
        virtual_time.set_relative_speed(time_elapsed.game_speed);
    }
}

/// System to tick virtual game time based on scale and game speed.
pub fn time_tick_system(
    time: Res<Time<Virtual>>,
    mut time_elapsed: ResMut<TimeElapsed>,
) {
    let game_dt = time.delta_secs() * time_elapsed.scale;
    time_elapsed.elapsed += game_dt;
}

pub fn keyboard_time_speed_system(
    keyboard_input: Res<ButtonInput<KeyCode>>,
    mut time_elapsed: ResMut<TimeElapsed>,
    mut sound_writer: MessageWriter<crate::audio::PlaySoundEvent>,
) {
    if keyboard_input.just_pressed(KeyCode::Minus) {
        time_elapsed.game_speed = (time_elapsed.game_speed / 2.0).max(0.25);
        sound_writer.write(crate::audio::PlaySoundEvent { name: "click".to_string() });
    }
    if keyboard_input.just_pressed(KeyCode::NumpadAdd) || keyboard_input.just_pressed(KeyCode::Equal) {
        time_elapsed.game_speed = (time_elapsed.game_speed * 2.0).min(8.0);
        sound_writer.write(crate::audio::PlaySoundEvent { name: "click".to_string() });
    }
}
