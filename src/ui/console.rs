use bevy::prelude::*;
use bevy::input::keyboard::{Key, KeyboardInput};
use std::collections::HashMap;
use std::sync::{Mutex, OnceLock};
use std::sync::atomic::{AtomicI32, Ordering};
use crate::ai::{Needs, StableId, YukkuriStats, EmotionalState};
use crate::render::TextureAtlasRegistry;
use crate::render::YukkuriTypeRegistry;
use super::ActiveFocus;

// ---------------------------------------------------------------------------
// FFI Registry Cache & Static Queues
// ---------------------------------------------------------------------------

#[derive(Clone, Debug, Default)]
pub struct CachedEntity {
    pub entity_id: u32,
    pub name: String,
    pub type_id: String,
    pub x: f32,
    pub y: f32,
    pub health: f32,
    pub hunger: f32,
    pub energy: f32,
    pub bladder: f32,
    pub cleanliness: f32,
    pub social: f32,
    pub easiness: f32,
    pub happiness: f32,
    pub stress: f32,
    pub growth_stage: String,
    pub age: f32,
}

static ENTITY_CACHE: OnceLock<Mutex<HashMap<u32, CachedEntity>>> = OnceLock::new();
static CURRENT_MONEY: AtomicI32 = AtomicI32::new(1000);

pub fn get_entity_cache() -> &'static Mutex<HashMap<u32, CachedEntity>> {
    ENTITY_CACHE.get_or_init(|| Mutex::new(HashMap::new()))
}

#[derive(Clone, Debug)]
pub enum ConsoleCommandEvent {
    Spawn { type_id: String, x: Option<f32>, y: Option<f32> },
    AddMoney(i32),
    SetMoney(i32),
    SetSpeed(f32),
    KillEntity(u32),
    SetNeed { entity_id: u32, need_name: String, value: f32 },
}

static CONSOLE_COMMANDS: OnceLock<Mutex<Vec<ConsoleCommandEvent>>> = OnceLock::new();

pub fn queue_console_command(event: ConsoleCommandEvent) {
    if let Ok(mut q) = CONSOLE_COMMANDS.get_or_init(|| Mutex::new(Vec::new())).lock() {
        q.push(event);
    }
}

// Removed PyO3 FFI Helper Functions
// ---------------------------------------------------------------------------
// Resources & Setup
// ---------------------------------------------------------------------------

#[derive(Resource, Default, Debug)]
pub struct ConsoleHistory {
    pub inputs: Vec<String>,
    pub current_index: usize,
    pub current_input: String,
}

#[derive(Component)]
pub struct ConsoleRootNode;

#[derive(Component)]
pub struct ConsoleOutputText;

#[derive(Component)]
pub struct ConsoleInputText;

#[derive(Component)]
pub struct ConsoleScrollNode;

#[derive(Component)]
pub struct ConsoleOutputContainer;

/// Startup system to spawn the Developer Console UI node structure.
pub fn setup_console_system(mut commands: Commands) {
    // Docked at the top of the screen: simple, solid dark theme.
    commands
        .spawn((
            ConsoleRootNode,
            Node {
                position_type: PositionType::Absolute,
                left: Val::Px(0.0),
                top: Val::Px(0.0),
                width: Val::Percent(100.0),
                height: Val::Px(260.0),
                display: Display::None, // Starts hidden, toggled by shortcut
                flex_direction: FlexDirection::Column,
                padding: UiRect::all(Val::Px(8.0)),
                ..default()
            },
            BackgroundColor(Color::srgb(0.08, 0.08, 0.09)),
            BorderColor::all(Color::srgb(0.2, 0.2, 0.22)),
        ))
        .with_children(|root| {
            // Logs Container
            root.spawn((
                ConsoleOutputContainer,
                Node {
                    flex_grow: 1.0,
                    margin: UiRect::bottom(Val::Px(6.0)),
                    padding: UiRect::all(Val::Px(6.0)),
                    overflow: Overflow::clip(),
                    flex_direction: FlexDirection::Column,
                    ..default()
                },
                BackgroundColor(Color::srgb(0.05, 0.05, 0.06)),
            ))
            .with_children(|logs_container| {
                logs_container.spawn((
                    ConsoleOutputText,
                    ConsoleScrollNode,
                    Text::new("Developer Console Initialized. Type commands (e.g. 'spawn reimu', 'money 500').\n"),
                    TextFont {
                        font_size: FontSize::Px(13.0),
                        ..default()
                    },
                    TextColor(Color::srgb(0.85, 0.85, 0.9)),
                    Node {
                        position_type: PositionType::Relative,
                        top: Val::Px(0.0),
                        ..default()
                    },
                ));
            });

            // Input Row
            root.spawn(Node {
                height: Val::Px(28.0),
                flex_direction: FlexDirection::Row,
                align_items: AlignItems::Center,
                padding: UiRect::horizontal(Val::Px(6.0)),
                ..default()
            })
            .with_children(|input_row| {
                // Prefix
                input_row.spawn((
                    Text::new(">>> "),
                    TextFont {
                        font_size: FontSize::Px(13.0),
                        ..default()
                    },
                    TextColor(Color::srgb(0.4, 0.6, 0.9)),
                ));

                // Buffer Text
                input_row.spawn((
                    ConsoleInputText,
                    Text::new(""),
                    TextFont {
                        font_size: FontSize::Px(13.0),
                        ..default()
                    },
                    TextColor(Color::srgb(0.95, 0.95, 0.95)),
                ));
            });
        });
}

// ---------------------------------------------------------------------------
// Execution logic
// ---------------------------------------------------------------------------

fn run_console_command(code_to_run: &str, output_log: &mut String) {
    let parts: Vec<&str> = code_to_run.split_whitespace().collect();
    if parts.is_empty() { return; }
    match parts[0] {
        "spawn" => {
            if parts.len() >= 2 {
                let type_id = parts[1].to_string();
                let x = parts.get(2).and_then(|s| s.parse().ok());
                let y = parts.get(3).and_then(|s| s.parse().ok());
                queue_console_command(ConsoleCommandEvent::Spawn { type_id, x, y });
                output_log.push_str(&format!("Queued spawn command for {}\n", parts[1]));
            } else {
                output_log.push_str("Usage: spawn <type_id> [x y]\n");
            }
        }
        "money" => {
            if parts.len() >= 2 {
                if let Ok(amount) = parts[1].parse() {
                    queue_console_command(ConsoleCommandEvent::SetMoney(amount));
                    output_log.push_str(&format!("Queued set money to {}\n", amount));
                } else {
                    output_log.push_str("Invalid amount\n");
                }
            } else {
                let money = CURRENT_MONEY.load(Ordering::Relaxed);
                output_log.push_str(&format!("Current money: {}\n", money));
            }
        }
        "speed" => {
            if parts.len() >= 2 {
                if let Ok(scale) = parts[1].parse() {
                    queue_console_command(ConsoleCommandEvent::SetSpeed(scale));
                    output_log.push_str(&format!("Queued set speed to {}\n", scale));
                }
            }
        }
        "kill" => {
            if parts.len() >= 2 {
                if let Ok(id) = parts[1].parse() {
                    queue_console_command(ConsoleCommandEvent::KillEntity(id));
                    output_log.push_str(&format!("Queued kill for {}\n", id));
                }
            }
        }
        "list" => {
            if let Ok(cache) = get_entity_cache().lock() {
                output_log.push_str(&format!("Entities ({}):\n", cache.len()));
                for (id, ent) in cache.iter() {
                    output_log.push_str(&format!("- [{}] {} ({}) at ({:.1}, {:.1})\n", id, ent.name, ent.type_id, ent.x, ent.y));
                }
            }
        }
        _ => {
            output_log.push_str(&format!("Unknown command: {}\n", parts[0]));
        }
    }
}


// ---------------------------------------------------------------------------
// Systems
// ---------------------------------------------------------------------------

/// System that syncs Bevy entity details and economy data to static caches every frame.
pub fn sync_economy_to_py_system(
    economy: Option<Res<crate::ai::persistence::Economy>>,
) {
    if let Some(econ) = economy {
        CURRENT_MONEY.store(econ.money, Ordering::Relaxed);
    }
}

/// System that syncs Bevy entity details to the cache every frame.
pub fn update_entity_cache_system(
    query: Query<(Entity, &StableId, &Transform, &Needs, &EmotionalState, &YukkuriStats)>,
) {
    if let Ok(mut cache) = get_entity_cache().lock() {
        cache.clear();
        for (_entity, stable_id, transform, needs, emotional, stats) in query.iter() {
            let id = (stable_id.0 & 0xFFFFFFFF) as u32;
            cache.insert(id, CachedEntity {
                entity_id: id,
                name: stats.name.clone(),
                type_id: stats.type_id.clone(),
                x: transform.translation.x,
                y: transform.translation.y,
                health: needs.health,
                hunger: needs.hunger,
                energy: needs.energy,
                bladder: needs.bladder,
                cleanliness: needs.cleanliness,
                social: needs.social,
                easiness: needs.easiness,
                happiness: emotional.happiness,
                stress: emotional.stress,
                growth_stage: stats.growth_stage.clone(),
                age: stats.age,
            });
        }
    }
}

/// System applying queued commands from the Developer Console.
pub fn apply_console_commands_system(
    mut commands: Commands,
    mut economy: Option<ResMut<crate::ai::persistence::Economy>>,
    mut virtual_time: Option<ResMut<Time<Virtual>>>,
    asset_server: Res<AssetServer>,
    atlas_registry: Res<TextureAtlasRegistry>,
    type_registry: Res<YukkuriTypeRegistry>,
    world_settings: Res<crate::ai::WorldSettings>,
    stable_query: Query<(Entity, &StableId)>,
    mut needs_query: Query<(Entity, &mut Needs)>,
) {
    if let Ok(mut q) = CONSOLE_COMMANDS.get_or_init(|| Mutex::new(Vec::new())).lock() {
        for event in q.drain(..) {
            match event {
                ConsoleCommandEvent::Spawn { type_id, x, y } => {
                    let prefab_path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
                        .join("data")
                        .join("prefabs")
                        .join(format!("{}.toml", type_id));
                    
                    if let Ok(prefab) = crate::prefabs::load_prefab(prefab_path.to_str().unwrap_or("")) {
                        let center_x = x.unwrap_or(world_settings.width / 2.0);
                        let center_y = y.unwrap_or(world_settings.height / 2.0);
                        crate::prefabs::spawn_yukkuri_prefab(
                            &mut commands,
                            &prefab,
                            Vec2::new(center_x, center_y),
                            &asset_server,
                            &atlas_registry,
                            &type_registry,
                        );
                    }
                }
                ConsoleCommandEvent::AddMoney(amount) => {
                    if let Some(ref mut econ) = economy {
                        econ.money = (econ.money + amount).max(0);
                    }
                }
                ConsoleCommandEvent::SetMoney(amount) => {
                    if let Some(ref mut econ) = economy {
                        econ.money = amount.max(0);
                    }
                }
                ConsoleCommandEvent::SetSpeed(scale) => {
                    if let Some(ref mut time) = virtual_time {
                        time.set_relative_speed(scale);
                    }
                }
                ConsoleCommandEvent::KillEntity(entity_low_id) => {
                    for (entity, stable_id) in stable_query.iter() {
                        let id = (stable_id.0 & 0xFFFFFFFF) as u32;
                        if id == entity_low_id {
                            commands.entity(entity).despawn();
                            break;
                        }
                    }
                }
                ConsoleCommandEvent::SetNeed { entity_id, need_name, value } => {
                    for (entity, stable_id) in stable_query.iter() {
                        let id = (stable_id.0 & 0xFFFFFFFF) as u32;
                        if id == entity_id {
                            if let Ok((_, mut needs)) = needs_query.get_mut(entity) {
                                match need_name.as_str() {
                                    "health" => needs.health = value,
                                    "hunger" => needs.hunger = value,
                                    "energy" => needs.energy = value,
                                    "bladder" => needs.bladder = value,
                                    "cleanliness" => needs.cleanliness = value,
                                    "social" => needs.social = value,
                                    "easiness" => needs.easiness = value,
                                    _ => {}
                                }
                            }
                            break;
                        }
                    }
                }
            }
        }
    }
}

/// Updates the Developer Console overlay visibility, input characters, logs buffer, and scrolling.
pub fn console_update_system(
    time: Res<Time>,
    toggle_state: Res<super::UiToggleState>,
    focus: Res<ActiveFocus>,
    mut history: ResMut<ConsoleHistory>,
    log_buffer: Res<super::ConsoleLogBuffer>,
    mut root_query: Query<&mut Node, With<ConsoleRootNode>>,
    mut text_query: Query<&mut Text, (With<ConsoleOutputText>, Without<ConsoleInputText>)>,
    mut input_query: Query<&mut Text, (With<ConsoleInputText>, Without<ConsoleOutputText>)>,
    mut keyboard_evr: MessageReader<KeyboardInput>,
) {
    let Ok(mut root_node) = root_query.single_mut() else { return; };

    // Toggle Visibility
    if toggle_state.console_open {
        root_node.display = Display::Flex;
    } else {
        root_node.display = Display::None;
        return;
    }

    // Sync Captured Log Buffers to Console Text node
    if log_buffer.was_updated {
        if let Ok(mut text) = text_query.single_mut() {
            text.0 = log_buffer.logs.join("\n") + "\n";
        }
    }

    // Only process typing inputs when focus is ConsoleInput
    if *focus != ActiveFocus::ConsoleInput {
        return;
    }

    // Key Actions (Backspace, Enter, Arrows) and typing
    for event in keyboard_evr.read() {
        if !event.state.is_pressed() {
            continue;
        }

        match event.key_code {
            KeyCode::Backspace => {
                history.current_input.pop();
            }
            KeyCode::Enter => {
                let code_to_run = history.current_input.trim().to_string();
                if !code_to_run.is_empty() {
                    history.inputs.push(code_to_run.clone());
                    history.current_index = history.inputs.len();

                    let mut log_output = String::new();
                    run_console_command(&code_to_run, &mut log_output);

                    // Push logs to global log buffer immediately so it updates UI
                    if let Ok(mut global_buf) = super::logging::get_log_buffer().lock() {
                        for line in log_output.lines() {
                            global_buf.push_back(line.to_string());
                        }
                    }
                    history.current_input.clear();
                }
            }
            KeyCode::ArrowUp => {
                if !history.inputs.is_empty() && history.current_index > 0 {
                    history.current_index -= 1;
                    history.current_input = history.inputs[history.current_index].clone();
                }
            }
            KeyCode::ArrowDown => {
                if history.current_index < history.inputs.len() {
                    history.current_index += 1;
                    if history.current_index == history.inputs.len() {
                        history.current_input.clear();
                    } else {
                        history.current_input = history.inputs[history.current_index].clone();
                    }
                }
            }
            _ => {
                // Check logical key for character typing
                match &event.logical_key {
                    Key::Character(character) => {
                        history.current_input.push_str(character.as_str());
                    }
                    Key::Space => {
                        history.current_input.push(' ');
                    }
                    _ => {}
                }
            }
        }
    }

    // Render Input Buffer with Blinking Cursor
    if let Ok(mut text) = input_query.single_mut() {
        let cursor = if (time.elapsed_secs() * 2.0) as i32 % 2 == 0 { "_" } else { "" };
        text.0 = format!("{}{}", history.current_input, cursor);
    }
}
