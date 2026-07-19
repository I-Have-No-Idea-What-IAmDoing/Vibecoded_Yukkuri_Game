pub mod logging;
pub mod hud;
pub mod console;
pub mod inspector;
pub mod profiler;
pub mod placement;
pub mod main_menu;

use bevy::prelude::*;

// Re-export key components/resources if needed elsewhere
pub use logging::ConsoleLogBuffer;
pub use mod_impl::{ActiveFocus, SystemTimings, UiToggleState, YukkuriDragState, YukkuriUiPlugin};
pub use hud::{YukkuriUiButton, UiAction};

mod mod_impl {
    use super::*;
    use super::logging::update_console_log_buffer_system;

    /// Tracks which UI element currently intercepts keyboard character typing.
    #[derive(Resource, Default, Debug, Clone, PartialEq, Eq)]
    pub enum ActiveFocus {
        #[default]
        Game,
        ConsoleInput,
        InspectorSearch,
        InspectorField(Entity, String), // (Target Entity, Field Name key)
    }

    /// Holds real-time performance timing measurements for the main systems.
    #[derive(Resource, Default, Debug, Clone)]
    pub struct SystemTimings {
        pub ai_time_ms: f64,
        pub physics_time_ms: f64,
        pub render_time_ms: f64,
        pub ui_time_ms: f64,
        pub budget_ms: f64, // Frame budget (e.g. 16.67 for 60fps)
    }

    /// Resource keeping track of the entity currently being dragged by the mouse.
    #[derive(Resource, Default, Debug)]
    pub struct YukkuriDragState {
        pub dragged_entity: Option<Entity>,
    }

    /// Toggles indicating which developer panels are currently open.
    #[derive(Resource, Default, Debug, Clone)]
    pub struct UiToggleState {
        pub console_open: bool,
        pub inspector_open: bool,
        pub profiler_open: bool,
    }

    pub struct YukkuriUiPlugin;

    impl Plugin for YukkuriUiPlugin {
        fn build(&self, app: &mut App) {
            // Ensure inputs are present
            if !app.world().contains_resource::<ButtonInput<MouseButton>>() {
                app.init_resource::<ButtonInput<MouseButton>>();
            }
            if !app.world().contains_resource::<ButtonInput<KeyCode>>() {
                app.init_resource::<ButtonInput<KeyCode>>();
            }

            // Init resources
            app.init_resource::<YukkuriDragState>()
                .init_resource::<ActiveFocus>()
                .init_resource::<SystemTimings>()
                .init_resource::<UiToggleState>()
                .init_resource::<logging::ConsoleLogBuffer>()
                .init_resource::<super::console::ConsoleHistory>()
                .init_resource::<super::hud::ActiveShopTab>()
                .init_resource::<super::hud::CleanToolActive>()
                .init_resource::<super::hud::TeleportToolActive>()
                .init_resource::<super::placement::PlacementState>();

            // Setup timings budget
            app.world_mut().resource_mut::<SystemTimings>().budget_ms = 16.67;

            // Add the main menu plugin
            app.add_plugins(super::main_menu::MainMenuPlugin);

            // Startup systems
            app.add_systems(Startup, (
                super::console::setup_console_system,
                super::inspector::setup_inspector_system,
                super::profiler::setup_profiler_system,
            ));

            app.add_systems(OnEnter(crate::GameState::Gameplay), super::hud::setup_hud_system);

            app.add_systems(
                Update,
                (
                    toggle_ui_panels_system,
                    update_console_log_buffer_system,
                    screenshot_system,
                ),
            );

            app.add_message::<super::hud::SpawnFloatingTextEvent>();

            app.add_systems(
                Update,
                (
                    super::hud::spawn_floating_text_system,
                    super::hud::update_floating_text_system,
                )
            );

            app.add_systems(
                Update,
                (
                    super::hud::hud_interaction_system,
                    super::hud::hud_update_system,
                    super::hud::yukkuri_drag_system,
                    super::hud::draw_selection_circle_system,
                    super::hud::floating_needs_bars_system,
                    super::hud::update_shop_ui_system,
                    super::placement::update_placement_system,
                    super::hud::hud_hover_tooltip_system,
                ).run_if(in_state(crate::GameState::Gameplay)),
            );

            app.add_systems(
                Update,
                (
                    super::hud::context_menu_system,
                    super::hud::context_menu_button_interaction_system,
                    super::hud::ui_scroll_system,
                ).run_if(in_state(crate::GameState::Gameplay)),
            );

            app.add_systems(
                Update,
                (
                    super::console::console_update_system,
                    super::console::sync_economy_to_py_system,
                    super::console::update_entity_cache_system,
                    super::console::apply_console_commands_system,
                    super::inspector::inspector_update_system,
                    super::profiler::profiler_update_system,
                ),
            );
        }
    }

    /// System that listens for F3/F4/Tilde inputs to toggle panels and adjust focus.
    fn toggle_ui_panels_system(
        keyboard_input: Res<ButtonInput<KeyCode>>,
        mut toggle_state: ResMut<UiToggleState>,
        mut focus: ResMut<ActiveFocus>,
        cursor_light_settings: Option<ResMut<crate::render::lighting::CursorLightSettings>>,
    ) {
        // Tilde / Backquote toggles Developer Console
        if keyboard_input.just_pressed(KeyCode::Backquote) {
            toggle_state.console_open = !toggle_state.console_open;
            if toggle_state.console_open {
                *focus = ActiveFocus::ConsoleInput;
            } else if *focus == ActiveFocus::ConsoleInput {
                *focus = ActiveFocus::Game;
            }
        }

        // F3 toggles Inspector, Ctrl+F3 toggles cursor light
        if keyboard_input.just_pressed(KeyCode::F3) {
            let is_control = keyboard_input.pressed(KeyCode::ControlLeft) || keyboard_input.pressed(KeyCode::ControlRight);
            if is_control {
                if let Some(mut settings) = cursor_light_settings {
                    settings.enabled = !settings.enabled;
                }
            } else {
                toggle_state.inspector_open = !toggle_state.inspector_open;
                if !toggle_state.inspector_open {
                    // Remove field focus if closing
                    match *focus {
                        ActiveFocus::InspectorSearch | ActiveFocus::InspectorField(_, _) => {
                            *focus = ActiveFocus::Game;
                        }
                        _ => {}
                    }
                }
            }
        }

        // F4 toggles Profiler
        if keyboard_input.just_pressed(KeyCode::F4) {
            toggle_state.profiler_open = !toggle_state.profiler_open;
        }
    }

    fn screenshot_system(
        mut commands: Commands,
        keyboard_input: Res<ButtonInput<KeyCode>>,
    ) {
        if keyboard_input.just_pressed(KeyCode::F12) {
            let _ = std::fs::create_dir_all("screenshots");
            let elapsed = std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs();
            let path = format!("screenshots/screenshot_{}.png", elapsed);
            commands.spawn(bevy::render::view::screenshot::Screenshot::primary_window())
                .observe(bevy::render::view::screenshot::save_to_disk(path.clone()));
            info!("Screenshot queued for disk save at: {}", path);
        }
    }
}
