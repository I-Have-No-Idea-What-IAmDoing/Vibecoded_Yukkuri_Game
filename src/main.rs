use bevy::prelude::*;
use avian2d::prelude::*;
use serde::Deserialize;
use bevy::render::{
    settings::{InstanceFlags, RenderCreation, WgpuSettings},
    RenderPlugin,
};


use vibecoded_yukkuri_game::ai;
use vibecoded_yukkuri_game::ai::load_world_settings;
use vibecoded_yukkuri_game::prefabs::{load_prefab, spawn_yukkuri_prefab};
use vibecoded_yukkuri_game::render::{TextureAtlasRegistry, YukkuriTypeRegistry};

// ---------------------------------------------------------------------------
// Window config — loaded from data/user_settings.toml at startup.
// ---------------------------------------------------------------------------

/// Deserialisation target for the `[window]` section of `data/user_settings.toml`.
#[derive(Deserialize, Debug)]
struct WindowToml {
    width: f32,
    height: f32,
    #[serde(default)]
    fullscreen: bool,
}

#[derive(Deserialize, Debug)]
struct UserSettingsToml {
    window: WindowToml,
}

/// Reads `data/user_settings.toml` and returns window dimensions.
/// Falls back to 1280×720 windowed if the file is missing or malformed.
fn load_window_settings() -> WindowToml {
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("data")
        .join("user_settings.toml");

    match std::fs::read_to_string(&path) {
        Ok(contents) => match toml::from_str::<UserSettingsToml>(&contents) {
            Ok(cfg) => cfg.window,
            Err(e) => {
                eprintln!(
                    "[WindowSettings] Failed to parse user_settings.toml: {}; \
                     using defaults (1280×720)",
                    e
                );
                WindowToml { width: 1280.0, height: 720.0, fullscreen: false }
            }
        },
        Err(e) => {
            eprintln!(
                "[WindowSettings] Could not read user_settings.toml: {}; \
                 using defaults (1280×720)",
                e
            );
            WindowToml { width: 1280.0, height: 720.0, fullscreen: false }
        }
    }
}

// ---------------------------------------------------------------------------
// Entry point
// ---------------------------------------------------------------------------

fn main() {
    // Read TOML configs before building the App so values can be injected
    // into DefaultPlugins (window) and as resources (world settings).
    let win = load_window_settings();
    let world_settings = load_world_settings();
    let sim_settings = vibecoded_yukkuri_game::simulation::needs::load_simulation_settings();

    println!(
        "Initializing Bevy Yukkuri Raised Game — world {}×{}, window {}×{}",
        world_settings.width, world_settings.height, win.width, win.height
    );

    let window_mode = if win.fullscreen {
        bevy::window::WindowMode::Fullscreen(
            bevy::window::MonitorSelection::Primary,
            bevy::window::VideoModeSelection::Current,
        )
    } else {
        bevy::window::WindowMode::Windowed
    };

    // In release builds, strip the Vulkan validation + debug instance flags to
    // suppress spurious `vulkanMemoryModelDeviceScope` warnings from Bevy's GPU
    // preprocessing shaders on AMD hardware.  Those are driver-capability
    // mismatches that wgpu tolerates at runtime; the validation layer reports
    // them as errors even though rendering proceeds correctly.
    // In debug builds the default flags are kept so real API errors are caught.
    #[cfg(debug_assertions)]
    let instance_flags = InstanceFlags::default();
    #[cfg(not(debug_assertions))]
    let instance_flags = InstanceFlags::empty();

    App::new()
        // ---- Core plugins -----------------------------------------------
        .add_plugins(
            DefaultPlugins
                .set(RenderPlugin {
                    render_creation: RenderCreation::Automatic(Box::new(WgpuSettings {
                        instance_flags,
                        ..default()
                    })),
                    ..default()
                })
                .set(WindowPlugin {
                    primary_window: Some(Window {
                        title: "Yukkuri Raising Game".to_string(),
                        resolution: bevy::window::WindowResolution::new(
                            win.width as u32,
                            win.height as u32,
                        ),
                        mode: window_mode,
                        ..default()
                    }),
                    ..default()
                })
                .set(bevy::log::LogPlugin {
                    custom_layer: vibecoded_yukkuri_game::ui::logging::get_console_layer,
                    ..default()
                }),
        )
        .init_state::<vibecoded_yukkuri_game::GameState>()

        // ---- Physics -------------------------------------------------------
        .add_plugins(PhysicsPlugins::default())
        // ---- Game-specific plugins -----------------------------------------
        // Insert WorldSettings BEFORE AIPlugin so init_resource<WorldSettings>
        // inside AIPlugin::build() is a no-op and our loaded value is kept.
        .insert_resource(world_settings.clone())
        .insert_resource(sim_settings)
        .insert_resource(vibecoded_yukkuri_game::simulation::hpa::NavigationService::new(
            world_settings.width,
            world_settings.height,
            50.0,
        ))
        .add_plugins(ai::AIPlugin)
        .add_plugins(vibecoded_yukkuri_game::render::YukkuriRenderPlugin)
        .add_plugins(vibecoded_yukkuri_game::camera::YukkuriCameraPlugin)
        .add_plugins(vibecoded_yukkuri_game::audio::YukkuriAudioPlugin)
        .add_plugins(vibecoded_yukkuri_game::ui::YukkuriUiPlugin)
        .add_plugins(vibecoded_yukkuri_game::simulation::SimulationPlugin)
        // ---- Systems -------------------------------------------------------
        .add_systems(OnEnter(vibecoded_yukkuri_game::GameState::Gameplay), spawn_initial_yukkuri)
        .run();
}

// ---------------------------------------------------------------------------
// Startup systems
// ---------------------------------------------------------------------------

/// Spawns one Reimu Yukkuri from `data/prefabs/reimu.toml` at the world centre.
///
/// Runs in [`PostStartup`] so that [`YukkuriRenderPlugin`]'s asset-loading
/// startup system (which registers textures and atlas layouts) has already
/// executed when we call [`spawn_yukkuri_prefab`].
fn spawn_initial_yukkuri(
    mut commands: Commands,
    asset_server: Res<AssetServer>,
    atlas_registry: Res<TextureAtlasRegistry>,
    type_registry: Res<YukkuriTypeRegistry>,
    world_settings: Res<ai::WorldSettings>,
    existing_query: Query<Entity, With<ai::Needs>>,
) {
    if !existing_query.is_empty() {
        return; // Already loaded a save or populated game, don't spawn duplicate
    }

    let prefab_path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("data")
        .join("prefabs")
        .join("reimu.toml");

    let prefab = match load_prefab(prefab_path.to_str().unwrap_or("data/prefabs/reimu.toml")) {
        Ok(p) => p,
        Err(e) => {
            eprintln!("[spawn_initial_yukkuri] Failed to load reimu.toml: {}", e);
            return;
        }
    };

    // Spawn at the centre of the game world.
    let center = Vec2::new(world_settings.width / 2.0, world_settings.height / 2.0);

    let entity = spawn_yukkuri_prefab(
        &mut commands,
        &prefab,
        center,
        &asset_server,
        &atlas_registry,
        &type_registry,
    );

    println!(
        "[spawn_initial_yukkuri] Spawned '{}' (type_id={}) at ({}, {}) — entity {:?}",
        prefab.prefab.name,
        prefab.prefab.type_id,
        center.x,
        center.y,
        entity,
    );
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

