//! Audio management for the Bevy port of Yukkuri Raising Game.
//! Handled via native `bevy_audio` APIs and loaded from TOML configurations.
//!
//! Bevy 0.19 note: `Events<T>` / `EventWriter<T>` / `EventReader<T>` were renamed
//! to `Messages<T>` / `MessageWriter<T>` / `MessageReader<T>`. Types that were
//! previously `#[derive(Event)]` are now `#[derive(Message)]`.

use bevy::prelude::*;
use std::collections::HashMap;
use serde::Deserialize;

/// Message to request playback of a preloaded sound by name.
#[derive(Message, Debug, Clone)]
pub struct PlaySoundEvent {
    /// The key/name of the sound (e.g. "click", "cry").
    pub name: String,
}

/// Resource that caches audio handles and volume parameters.
#[derive(Resource, Clone, Debug)]
pub struct YukkuriAudioManager {
    /// Preloaded audio source handles mapped by sound key.
    pub sounds: HashMap<String, Handle<AudioSource>>,
    /// Master volume scaling factor (0.0 to 1.0).
    pub master_volume: f32,
    /// Background music volume scaling factor (0.0 to 1.0).
    pub bgm_volume: f32,
    /// Sound effects volume scaling factor (0.0 to 1.0).
    pub sfx_volume: f32,
}

#[derive(Deserialize, Debug)]
struct SoundsConfig {
    sounds: HashMap<String, String>,
}

#[derive(Deserialize, Debug)]
struct AudioSettingsToml {
    #[serde(default = "default_volume")]
    master_volume: f32,
    #[serde(default = "default_volume")]
    bgm_volume: f32,
    #[serde(default = "default_volume")]
    sfx_volume: f32,
}

#[derive(Deserialize, Debug)]
struct UserSettingsToml {
    audio: Option<AudioSettingsToml>,
}

fn default_volume() -> f32 {
    1.0
}

/// Helper to translate a file path from Python format (e.g., `data/audio/click.wav`)
/// to Bevy asset format (e.g., `audio/click.wav`).
fn map_path(path: &str) -> String {
    if let Some(stripped) = path.strip_prefix("data/") {
        stripped.to_string()
    } else {
        path.to_string()
    }
}

/// Plugin registering audio loading, preloading, and message playback systems.
pub struct YukkuriAudioPlugin;

impl Plugin for YukkuriAudioPlugin {
    fn build(&self, app: &mut App) {
        if !app.world().contains_resource::<Assets<AudioSource>>() {
            app.init_asset::<AudioSource>();
        }

        app.add_message::<PlaySoundEvent>()
            .add_systems(Startup, setup_audio_system)
            .add_systems(Update, play_sound_event_system);
    }
}

fn setup_audio_system(
    mut commands: Commands,
    asset_server: Res<AssetServer>,
) {
    // 1. Load volume parameters from user_settings.toml
    let settings_path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("data")
        .join("user_settings.toml");

    let mut master_vol = 1.0;
    let mut bgm_vol = 1.0;
    let mut sfx_vol = 1.0;

    if let Ok(contents) = std::fs::read_to_string(&settings_path) {
        if let Ok(settings) = toml::from_str::<UserSettingsToml>(&contents) {
            if let Some(audio) = settings.audio {
                master_vol = audio.master_volume.clamp(0.0, 1.0);
                bgm_vol = audio.bgm_volume.clamp(0.0, 1.0);
                sfx_vol = audio.sfx_volume.clamp(0.0, 1.0);
            }
        }
    }

    // 2. Load sound paths from sounds.toml
    let sounds_path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("data")
        .join("sounds.toml");

    let mut sounds_map = HashMap::new();
    if let Ok(contents) = std::fs::read_to_string(&sounds_path) {
        if let Ok(config) = toml::from_str::<SoundsConfig>(&contents) {
            for (name, filepath) in config.sounds {
                sounds_map.insert(name, map_path(&filepath));
            }
        }
    }

    // 3. Fill in default fallback paths for expected sounds
    let defaults = [
        ("click", "audio/click.wav"),
        ("place", "audio/place.wav"),
        ("cancel", "audio/cancel.wav"),
        ("sell", "audio/sell.wav"),
        ("train", "audio/train.wav"),
        ("eat", "audio/eat.wav"),
        ("cry", "audio/cry.wav"),
    ];
    for (name, fallback_path) in defaults {
        sounds_map
            .entry(name.to_string())
            .or_insert_with(|| fallback_path.to_string());
    }

    // 4. Preload handles
    let mut sounds = HashMap::new();
    for (name, asset_path) in sounds_map {
        let handle: Handle<AudioSource> = asset_server.load(asset_path);
        sounds.insert(name, handle);
    }

    commands.insert_resource(YukkuriAudioManager {
        sounds,
        master_volume: master_vol,
        bgm_volume: bgm_vol,
        sfx_volume: sfx_vol,
    });
}

fn play_sound_event_system(
    mut commands: Commands,
    audio_manager: Res<YukkuriAudioManager>,
    mut message_reader: MessageReader<PlaySoundEvent>,
) {
    for event in message_reader.read() {
        if let Some(handle) = audio_manager.sounds.get(&event.name) {
            let volume = audio_manager.master_volume * audio_manager.sfx_volume;
            commands.spawn((
                AudioPlayer::new(handle.clone()),
                PlaybackSettings {
                    volume: bevy::audio::Volume::Linear(volume),
                    ..PlaybackSettings::DESPAWN
                },
            ));
        } else {
            warn!("Audio key '{}' not found in YukkuriAudioManager", event.name);
        }
    }
}
