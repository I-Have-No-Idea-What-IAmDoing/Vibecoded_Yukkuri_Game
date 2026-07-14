use bevy::prelude::*;
use crate::GameState;
use crate::ai::persistence::load_game;

pub struct MainMenuPlugin;

impl Plugin for MainMenuPlugin {
    fn build(&self, app: &mut App) {
        app.add_systems(OnEnter(GameState::MainMenu), spawn_main_menu)
            .add_systems(OnExit(GameState::MainMenu), despawn_main_menu)
            .add_systems(Update, button_system.run_if(in_state(GameState::MainMenu)));
    }
}

#[derive(Component)]
struct MainMenuRoot;

#[derive(Component)]
enum MenuButton {
    Start,
    Load,
    Exit,
}

fn spawn_main_menu(
    mut commands: Commands,
    _asset_server: Res<AssetServer>,
) {
    // Spawn root full screen panel
    commands
        .spawn((
            MainMenuRoot,
            Node {
                width: Val::Percent(100.0),
                height: Val::Percent(100.0),
                flex_direction: FlexDirection::Column,
                align_items: AlignItems::Center,
                justify_content: JustifyContent::Center,
                row_gap: Val::Px(20.0),
                ..default()
            },
            BackgroundColor(Color::srgba(0.05, 0.05, 0.07, 0.95)),
        ))
        .with_children(|parent| {
            // Game Title
            parent.spawn((
                Text::new("Yukkuri Raising Game"),
                TextFont {
                    font_size: FontSize::Px(48.0),
                    ..default()
                },
                TextColor(Color::srgb(0.9, 0.9, 0.95)),
                Node {
                    margin: UiRect::bottom(Val::Px(40.0)),
                    ..default()
                },
            ));

            // Buttons Container
            parent
                .spawn(Node {
                    flex_direction: FlexDirection::Column,
                    row_gap: Val::Px(15.0),
                    align_items: AlignItems::Center,
                    ..default()
                })
                .with_children(|buttons| {
                    spawn_menu_button(buttons, "Start Game", MenuButton::Start);
                    
                    // Only enable Load button if quicksave.sqlite exists
                    let save_exists = std::path::Path::new("saves/quicksave.sqlite").exists();
                    let load_color = if save_exists {
                        Color::srgb(0.95, 0.95, 0.95)
                    } else {
                        Color::srgb(0.5, 0.5, 0.5)
                    };
                    
                    spawn_menu_button_colored(buttons, "Load Quicksave", MenuButton::Load, load_color);
                    spawn_menu_button(buttons, "Exit", MenuButton::Exit);
                });
        });
}

fn spawn_menu_button(parent: &mut ChildSpawnerCommands, label: &str, action: MenuButton) {
    spawn_menu_button_colored(parent, label, action, Color::srgb(0.95, 0.95, 0.95));
}

fn spawn_menu_button_colored(
    parent: &mut ChildSpawnerCommands,
    label: &str,
    action: MenuButton,
    text_color: Color,
) {
    parent
        .spawn((
            Button,
            Node {
                width: Val::Px(200.0),
                height: Val::Px(50.0),
                justify_content: JustifyContent::Center,
                align_items: AlignItems::Center,
                border_radius: BorderRadius::all(Val::Px(8.0)),
                ..default()
            },
            BackgroundColor(Color::srgba(0.15, 0.15, 0.2, 0.8)),
            BorderColor::all(Color::srgba(0.3, 0.3, 0.35, 0.5)),
            action,
        ))
        .with_children(|btn| {
            btn.spawn((
                Text::new(label),
                TextFont {
                    font_size: FontSize::Px(18.0),
                    ..default()
                },
                TextColor(text_color),
            ));
        });
}

fn despawn_main_menu(
    mut commands: Commands,
    query: Query<Entity, With<MainMenuRoot>>,
) {
    for ent in query.iter() {
        commands.entity(ent).despawn();
    }
}

fn button_system(
    mut next_state: ResMut<NextState<GameState>>,
    mut interaction_query: Query<
        (&Interaction, &MenuButton, &mut BackgroundColor),
        (Changed<Interaction>, With<Button>),
    >,
    mut app_exit: MessageWriter<bevy::app::AppExit>,
    mut commands: Commands,
) {
    for (interaction, button_action, mut bg_color) in interaction_query.iter_mut() {
        match *interaction {
            Interaction::Pressed => {
                match button_action {
                    MenuButton::Start => {
                        next_state.set(GameState::Gameplay);
                    }
                    MenuButton::Load => {
                        let save_path = "saves/quicksave.sqlite";
                        if std::path::Path::new(save_path).exists() {
                            // Queue a command that runs exclusive loading logic on the world
                            commands.queue(move |world: &mut World| {
                                if let Err(e) = load_game(world, save_path) {
                                    error!("Failed to load quicksave: {}", e);
                                }
                            });
                            next_state.set(GameState::Gameplay);
                        }
                    }
                    MenuButton::Exit => {
                        app_exit.write(bevy::app::AppExit::Success);
                    }
                }
            }
            Interaction::Hovered => {
                // If it is the Load button and file doesn't exist, we don't change color to make it look disabled
                let is_load_disabled = match button_action {
                    MenuButton::Load => !std::path::Path::new("saves/quicksave.sqlite").exists(),
                    _ => false,
                };
                if !is_load_disabled {
                    *bg_color = BackgroundColor(Color::srgba(0.25, 0.25, 0.32, 0.9));
                }
            }
            Interaction::None => {
                let is_load_disabled = match button_action {
                    MenuButton::Load => !std::path::Path::new("saves/quicksave.sqlite").exists(),
                    _ => false,
                };
                if is_load_disabled {
                    *bg_color = BackgroundColor(Color::srgba(0.1, 0.1, 0.12, 0.5));
                } else {
                    *bg_color = BackgroundColor(Color::srgba(0.15, 0.15, 0.2, 0.8));
                }
            }
        }
    }
}
