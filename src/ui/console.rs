use bevy::prelude::*;
use bevy::input::keyboard::{Key, KeyboardInput};
use pyo3::prelude::*;
use pyo3::types::PyDict;
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

// ---------------------------------------------------------------------------
// PyO3 FFI Helper Functions
// ---------------------------------------------------------------------------

#[pyfunction]
#[pyo3(signature = (type_id, x=None, y=None))]
pub fn spawn_py(type_id: String, x: Option<f32>, y: Option<f32>) {
    queue_console_command(ConsoleCommandEvent::Spawn { type_id, x, y });
}

#[pyfunction]
pub fn add_money_py(amount: i32) {
    queue_console_command(ConsoleCommandEvent::AddMoney(amount));
}

#[pyfunction]
pub fn set_money_py(amount: i32) {
    queue_console_command(ConsoleCommandEvent::SetMoney(amount));
}

#[pyfunction]
pub fn get_money_py() -> i32 {
    CURRENT_MONEY.load(Ordering::Relaxed)
}

#[pyfunction]
pub fn set_speed_py(scale: f32) {
    queue_console_command(ConsoleCommandEvent::SetSpeed(scale));
}

#[pyfunction]
pub fn kill_entity_py(entity_id: u32) {
    queue_console_command(ConsoleCommandEvent::KillEntity(entity_id));
}

#[pyfunction]
pub fn set_need_py(entity_id: u32, need_name: String, value: f32) {
    queue_console_command(ConsoleCommandEvent::SetNeed { entity_id, need_name, value });
}

#[pyfunction]
pub fn get_entities_py() -> Vec<u32> {
    if let Ok(cache) = get_entity_cache().lock() {
        cache.keys().cloned().collect()
    } else {
        Vec::new()
    }
}

#[pyfunction]
pub fn get_component_field_py(entity_id: u32, comp_name: String, field_name: String) -> String {
    if let Ok(cache) = get_entity_cache().lock() {
        if let Some(ent) = cache.get(&entity_id) {
            match comp_name.as_str() {
                "Transform" => match field_name.as_str() {
                    "x" => return ent.x.to_string(),
                    "y" => return ent.y.to_string(),
                    _ => {}
                },
                "Needs" => match field_name.as_str() {
                    "health" => return ent.health.to_string(),
                    "hunger" => return ent.hunger.to_string(),
                    "energy" => return ent.energy.to_string(),
                    "bladder" => return ent.bladder.to_string(),
                    "cleanliness" => return ent.cleanliness.to_string(),
                    "social" => return ent.social.to_string(),
                    "easiness" => return ent.easiness.to_string(),
                    _ => {}
                },
                "YukkuriStats" => match field_name.as_str() {
                    "name" => return ent.name.clone(),
                    "type_id" => return ent.type_id.clone(),
                    "growth_stage" => return ent.growth_stage.clone(),
                    "age" => return ent.age.to_string(),
                    _ => {}
                },
                "EmotionalState" => match field_name.as_str() {
                    "happiness" => return ent.happiness.to_string(),
                    "stress" => return ent.stress.to_string(),
                    _ => {}
                },
                _ => {}
            }
        }
    }
    String::new()
}

pub fn register_console_bindings(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(spawn_py, m)?)?;
    m.add_function(wrap_pyfunction!(add_money_py, m)?)?;
    m.add_function(wrap_pyfunction!(set_money_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_money_py, m)?)?;
    m.add_function(wrap_pyfunction!(set_speed_py, m)?)?;
    m.add_function(wrap_pyfunction!(kill_entity_py, m)?)?;
    m.add_function(wrap_pyfunction!(set_need_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_entities_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_component_field_py, m)?)?;
    Ok(())
}

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
                    Text::new("Developer Console Initialized. Type raw Python statements or expressions.\n"),
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
// Python Setup Constants
// ---------------------------------------------------------------------------

const PYTHON_SETUP_CODE: &std::ffi::CStr = cr#"
import yukkuri_rust

class MockTransform:
    def __init__(self, entity_id):
        self._entity_id = entity_id
    @property
    def x(self): return float(yukkuri_rust.get_component_field_py(self._entity_id, "Transform", "x"))
    @property
    def y(self): return float(yukkuri_rust.get_component_field_py(self._entity_id, "Transform", "y"))

class MockNeeds:
    def __init__(self, entity_id):
        self._entity_id = entity_id
    @property
    def health(self): return float(yukkuri_rust.get_component_field_py(self._entity_id, "Needs", "health"))
    @health.setter
    def health(self, val): yukkuri_rust.set_need_py(self._entity_id, "health", float(val))
    
    @property
    def hunger(self): return float(yukkuri_rust.get_component_field_py(self._entity_id, "Needs", "hunger"))
    @hunger.setter
    def hunger(self, val): yukkuri_rust.set_need_py(self._entity_id, "hunger", float(val))
    
    @property
    def energy(self): return float(yukkuri_rust.get_component_field_py(self._entity_id, "Needs", "energy"))
    @energy.setter
    def energy(self, val): yukkuri_rust.set_need_py(self._entity_id, "energy", float(val))

    @property
    def cleanliness(self): return float(yukkuri_rust.get_component_field_py(self._entity_id, "Needs", "cleanliness"))
    @cleanliness.setter
    def cleanliness(self, val): yukkuri_rust.set_need_py(self._entity_id, "cleanliness", float(val))

    @property
    def bladder(self): return float(yukkuri_rust.get_component_field_py(self._entity_id, "Needs", "bladder"))
    @bladder.setter
    def bladder(self, val): yukkuri_rust.set_need_py(self._entity_id, "bladder", float(val))

    @property
    def social(self): return float(yukkuri_rust.get_component_field_py(self._entity_id, "Needs", "social"))
    @social.setter
    def social(self, val): yukkuri_rust.set_need_py(self._entity_id, "social", float(val))

    @property
    def easiness(self): return float(yukkuri_rust.get_component_field_py(self._entity_id, "Needs", "easiness"))
    @easiness.setter
    def easiness(self, val): yukkuri_rust.set_need_py(self._entity_id, "easiness", float(val))

class MockYukkuriStats:
    def __init__(self, entity_id):
        self._entity_id = entity_id
    @property
    def name(self): return yukkuri_rust.get_component_field_py(self._entity_id, "YukkuriStats", "name")
    @property
    def type_id(self): return yukkuri_rust.get_component_field_py(self._entity_id, "YukkuriStats", "type_id")
    @property
    def growth_stage(self): return yukkuri_rust.get_component_field_py(self._entity_id, "YukkuriStats", "growth_stage")
    @property
    def age(self): return float(yukkuri_rust.get_component_field_py(self._entity_id, "YukkuriStats", "age"))

class MockEmotionalState:
    def __init__(self, entity_id):
        self._entity_id = entity_id
    @property
    def happiness(self): return float(yukkuri_rust.get_component_field_py(self._entity_id, "EmotionalState", "happiness"))
    @property
    def stress(self): return float(yukkuri_rust.get_component_field_py(self._entity_id, "EmotionalState", "stress"))

class ConsoleWorld:
    def __init__(self):
        self.services = self.Services()
    
    class Services:
        def try_get(self, cls):
            name = str(cls)
            if "EconomyService" in name or "Economy" in name:
                return self.MockEconomy()
            return None
        def get(self, cls):
            return self.try_get(cls)
        
        class MockEconomy:
            @property
            def money(self): return yukkuri_rust.get_money_py()
            @money.setter
            def money(self, val): yukkuri_rust.set_money_py(int(val))

    def try_get_component(self, entity_id, comp_type):
        name = comp_type.__name__
        if name == "Transform": return MockTransform(entity_id)
        if name == "Needs": return MockNeeds(entity_id)
        if name == "YukkuriStats": return MockYukkuriStats(entity_id)
        if name == "EmotionalState": return MockEmotionalState(entity_id)
        return None
    
    def get_components(self, comp_type):
        ents = yukkuri_rust.get_entities_py()
        results = []
        for e in ents:
            comp = self.try_get_component(e, comp_type)
            if comp is not None:
                results.append((e, comp))
        return results

    def entity_exists(self, entity_id):
        return entity_id in yukkuri_rust.get_entities_py()

    def destroy_entity(self, entity_id):
        yukkuri_rust.kill_entity_py(entity_id)

world = ConsoleWorld()
"#;

// ---------------------------------------------------------------------------
// Execution logic
// ---------------------------------------------------------------------------

fn run_python_code(code_to_run: &str, output_log: &mut String) {
    Python::with_gil(|py| {
        // Redirection of prints/exceptions
        let sys = match py.import("sys") {
            Ok(s) => s,
            Err(e) => {
                output_log.push_str(&format!("[Python FFI Error] failed to import sys: {:?}\n", e));
                return;
            }
        };
        let io = match py.import("io") {
            Ok(i) => i,
            Err(e) => {
                output_log.push_str(&format!("[Python FFI Error] failed to import io: {:?}\n", e));
                return;
            }
        };
        let string_io = match io.call_method0("StringIO") {
            Ok(s) => s,
            Err(e) => {
                output_log.push_str(&format!("[Python FFI Error] failed to create StringIO: {:?}\n", e));
                return;
            }
        };

        let old_stdout = sys.getattr("stdout").unwrap();
        let old_stderr = sys.getattr("stderr").unwrap();

        let _ = sys.setattr("stdout", &string_io);
        let _ = sys.setattr("stderr", &string_io);

        // Prepare globals
        let globals = PyDict::new(py);
        let _ = globals.set_item("__builtins__", py.eval(c"__builtins__", None, None).unwrap());
        if let Ok(math) = py.import("math") { let _ = globals.set_item("math", math); }
        if let Ok(random) = py.import("random") { let _ = globals.set_item("random", random); }
        if let Ok(sys_module) = py.import("sys") { let _ = globals.set_item("sys", sys_module); }
        if let Ok(time) = py.import("time") { let _ = globals.set_item("time", time); }
        if let Ok(yukkuri_rust) = py.import("yukkuri_rust") { let _ = globals.set_item("yukkuri_rust", yukkuri_rust); }

        // Inject helper methods
        let _ = py.run(PYTHON_SETUP_CODE, Some(&globals), None);

        output_log.push_str(&format!(">>> {}\n", code_to_run));

        let code_cstr = std::ffi::CString::new(code_to_run).unwrap();

        // Evaluate expression first, fall back to exec
        let eval_res = py.eval(&code_cstr, Some(&globals), None);
        match eval_res {
            Ok(val) => {
                if !val.is_none() {
                    if let Ok(repr) = val.repr() {
                        if let Ok(repr_str) = repr.extract::<String>() {
                            output_log.push_str(&format!("{}\n", repr_str));
                        }
                    }
                }
            }
            Err(_) => {
                // Try executing as a script block
                if let Err(exec_err) = py.run(&code_cstr, Some(&globals), None) {
                    let err_type = exec_err.value(py)
                        .get_type()
                        .name()
                        .ok()
                        .and_then(|n| n.to_str().ok().map(|s| s.to_string()))
                        .unwrap_or_else(|| "Exception".to_string());
                    let err_val = exec_err.value(py).to_string();
                    output_log.push_str(&format!("{}: {}\n", err_type, err_val));
                }
            }
        }

        // Get stdout value
        if let Ok(captured) = string_io.call_method0("getvalue") {
            if let Ok(captured_str) = captured.extract::<String>() {
                if !captured_str.is_empty() {
                    output_log.push_str(&captured_str);
                    if !captured_str.ends_with('\n') {
                        output_log.push('\n');
                    }
                }
            }
        }

        // Reset stdout/stderr
        let _ = sys.setattr("stdout", &old_stdout);
        let _ = sys.setattr("stderr", &old_stderr);
    });
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
                    run_python_code(&code_to_run, &mut log_output);

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
