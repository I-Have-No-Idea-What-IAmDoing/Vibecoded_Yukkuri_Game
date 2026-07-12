mod common;

use bevy::prelude::*;
use bevy::ecs::system::RunSystemOnce;
use avian2d::prelude::*;
use std::sync::{Arc, Mutex};
use vibecoded_yukkuri_game::audio::{PlaySoundEvent, YukkuriAudioManager};
use vibecoded_yukkuri_game::ui::{YukkuriDragState, YukkuriUiButton, UiAction};
use vibecoded_yukkuri_game::prefabs::{load_prefab, spawn_yukkuri_prefab};
use vibecoded_yukkuri_game::render::{TextureAtlasRegistry, YukkuriTypeRegistry};

static PYTHON_INIT: std::sync::OnceLock<()> = std::sync::OnceLock::new();
static TEST_MUTEX: Mutex<()> = Mutex::new(());

fn init_python() {
    PYTHON_INIT.get_or_init(|| {
        use vibecoded_yukkuri_game::ai::yukkuri_rust;
        pyo3::append_to_inittab!(yukkuri_rust);
        pyo3::prepare_freethreaded_python();
    });
}

fn make_app() -> App {
    common::create_test_app()
}

fn spawn_one(app: &mut App, position: Vec2) -> Entity {
    let prefab = load_prefab("data/prefabs/reimu.toml")
        .expect("Failed to load reimu.toml prefab");

    let slot = Arc::new(Mutex::new(None));
    let slot_clone = slot.clone();
    let prefab_clone = prefab.clone();

    app.add_systems(
        PostStartup,
        move |mut commands: Commands,
              asset_server: Res<AssetServer>,
              atlas_registry: Res<TextureAtlasRegistry>,
              type_registry: Res<YukkuriTypeRegistry>| {
            let e = spawn_yukkuri_prefab(
                &mut commands,
                &prefab_clone,
                position,
                &asset_server,
                &atlas_registry,
                &type_registry,
            );
            *slot_clone.lock().unwrap() = Some(e);
        },
    );

    app.update(); // fires PostStartup
    let entity = *slot.lock().unwrap();
    entity.expect("PostStartup spawn system did not run")
}

#[test]
fn test_audio_manager_resource_loaded() {
    let _lock = TEST_MUTEX.lock().unwrap_or_else(|e| e.into_inner());
    init_python();

    let mut app = make_app();
    app.update();

    let world = app.world();
    let audio_manager = world
        .get_resource::<YukkuriAudioManager>()
        .expect("YukkuriAudioManager resource missing");

    // Check that expected keys are in the audio manager
    assert!(audio_manager.sounds.contains_key("click"));
    assert!(audio_manager.sounds.contains_key("cry"));
    assert!(audio_manager.sounds.contains_key("place"));
    assert!(audio_manager.sounds.contains_key("cancel"));
    assert!(audio_manager.sounds.contains_key("sell"));
    assert!(audio_manager.sounds.contains_key("train"));
    assert!(audio_manager.sounds.contains_key("eat"));

    // Check volume scaling fields exist (clamp/read from user_settings.toml)
    assert_eq!(audio_manager.master_volume, 0.5);
    assert_eq!(audio_manager.sfx_volume, 0.5);
}

#[test]
fn test_dragging_flow() {
    let _lock = TEST_MUTEX.lock().unwrap_or_else(|e| e.into_inner());
    init_python();

    let mut app = make_app();
    
    let _camera_entity = common::spawn_test_camera(&mut app);

    let entity = spawn_one(&mut app, Vec2::new(0.0, 0.0));

    // Initially RigidBody should be Dynamic
    {
        let world = app.world();
        let rb = world.get::<RigidBody>(entity).expect("RigidBody missing");
        assert_eq!(*rb, RigidBody::Dynamic);
    }

    let window_entity = common::spawn_test_window(&mut app);

    // Send mouse press event via MessageWriter so InputPlugin processes it in PreUpdate,
    // correctly setting just_pressed for the next Update frame.
    let _ = app.world_mut().run_system_once(
        move |mut writer: MessageWriter<bevy::input::mouse::MouseButtonInput>| {
            writer.write(bevy::input::mouse::MouseButtonInput {
                button: MouseButton::Left,
                state: bevy::input::ButtonState::Pressed,
                window: window_entity,
            });
        }
    );

    // Update app so transform propagation runs and drag system responds
    app.update();

    // Check if the entity is being dragged and set to Kinematic
    {
        let world = app.world();
        let drag_state = world.get_resource::<YukkuriDragState>().expect("YukkuriDragState missing");
        assert_eq!(drag_state.dragged_entity, Some(entity));

        let rb = world.get::<RigidBody>(entity).expect("RigidBody missing");
        assert_eq!(*rb, RigidBody::Kinematic);
    }

    // Move cursor to (100, 50) in world coordinates.
    // Viewport coords: center is (400, 300).
    // world_x = 100 -> screen_x = 400 + 100 = 500
    // world_y = 50 -> screen_y = 300 - 50 = 250 (Y is down in viewport)
    if let Some(mut window) = app.world_mut().get_mut::<Window>(window_entity) {
        window.set_cursor_position(Some(Vec2::new(500.0, 250.0)));
    }

    println!("Yukkuri translation before second update: {:?}", app.world().get::<Transform>(entity).unwrap().translation);
    app.update();
    println!("Yukkuri translation after second update: {:?}", app.world().get::<Transform>(entity).unwrap().translation);

    // Check if the entity position was translated
    {
        let world = app.world();
        let transform = world.get::<Transform>(entity).expect("Transform missing");
        assert!((transform.translation.x - 100.0).abs() < 1e-3);
        assert!((transform.translation.y - 50.0).abs() < 1e-3);
    }

    // Send mouse release event via MessageWriter
    let _ = app.world_mut().run_system_once(
        move |mut writer: MessageWriter<bevy::input::mouse::MouseButtonInput>| {
            writer.write(bevy::input::mouse::MouseButtonInput {
                button: MouseButton::Left,
                state: bevy::input::ButtonState::Released,
                window: window_entity,
            });
        }
    );

    app.update();

    // Check if dragging stopped and RigidBody is Dynamic again
    {
        let world = app.world();
        let drag_state = world.get_resource::<YukkuriDragState>().expect("YukkuriDragState missing");
        assert_eq!(drag_state.dragged_entity, None);

        let rb = world.get::<RigidBody>(entity).expect("RigidBody missing");
        assert_eq!(*rb, RigidBody::Dynamic);
    }
}

#[test]
fn test_ui_button_interaction() {
    let _lock = TEST_MUTEX.lock().unwrap_or_else(|e| e.into_inner());
    init_python();

    let mut app = make_app();
    app.update();

    // Clear messages
    app.world_mut().resource_mut::<Messages<PlaySoundEvent>>().clear();

    // Spawn a button with Press action
    let button_entity = app.world_mut().spawn((
        Button,
        Interaction::None,
        YukkuriUiButton {
            action: UiAction::TestSound("eat".to_string()),
        },
        BackgroundColor(Color::BLACK),
    )).id();

    // Simulate Hover
    *app.world_mut().get_mut::<Interaction>(button_entity).unwrap() = Interaction::Hovered;
    app.update();

    // Simulate Press
    *app.world_mut().get_mut::<Interaction>(button_entity).unwrap() = Interaction::Pressed;
    app.update();

    // Check if PlaySoundEvent was fired
    let messages = app.world().resource::<Messages<PlaySoundEvent>>();
    let mut reader = messages.get_cursor();
    let fired_events: Vec<&PlaySoundEvent> = reader.read(messages).collect();

    assert!(fired_events.iter().any(|e| e.name == "click"));
    assert!(fired_events.iter().any(|e| e.name == "eat"));
}

#[test]
fn test_hover_tooltip_flow() {
    let _lock = TEST_MUTEX.lock().unwrap_or_else(|e| e.into_inner());
    init_python();

    let mut app = make_app();
    
    let camera_entity = common::spawn_test_camera(&mut app);
    app.world_mut().entity_mut(camera_entity).insert(vibecoded_yukkuri_game::camera::MainCamera);
    let _entity = spawn_one(&mut app, Vec2::new(0.0, 0.0));

    // Find tooltip entities spawned by setup_hud_system
    let (tooltip_entity, text_entity) = app.world_mut().run_system_once(|
        tooltip_q: Query<Entity, With<vibecoded_yukkuri_game::ui::hud::HudHoverTooltip>>,
        text_q: Query<Entity, With<vibecoded_yukkuri_game::ui::hud::HudHoverTooltipText>>,
    | -> (Entity, Entity) {
        (tooltip_q.single().unwrap(), text_q.single().unwrap())
    }).unwrap();

    let window_entity = common::spawn_test_window(&mut app);

    // 1. Move cursor close to yukkuri (screen center (400, 300) -> world (0,0))
    if let Some(mut window) = app.world_mut().get_mut::<Window>(window_entity) {
        window.set_cursor_position(Some(Vec2::new(400.0, 300.0)));
    }

    app.update();

    // The tooltip should be active and display the yukkuri name
    {
        let world = app.world();
        let node = world.get::<Node>(tooltip_entity).expect("Node missing");
        assert_eq!(node.display, Display::Flex);
        assert_eq!(node.left, Val::Px(415.0));
        assert_eq!(node.top, Val::Px(315.0));

        let text = world.get::<Text>(text_entity).expect("Text missing");
        assert!(text.0.contains("Reimu")); // Default prefab has name "Reimu Yukkuri"
    }

    // 2. Move cursor far away (screen (0, 0) -> world (-400, 300))
    if let Some(mut window) = app.world_mut().get_mut::<Window>(window_entity) {
        window.set_cursor_position(Some(Vec2::new(0.0, 0.0)));
    }

    app.update();

    // The tooltip should be hidden
    {
        let world = app.world();
        let node = world.get::<Node>(tooltip_entity).expect("Node missing");
        assert_eq!(node.display, Display::None);
    }
}
