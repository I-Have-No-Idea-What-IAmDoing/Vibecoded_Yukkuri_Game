use bevy::prelude::*;
use avian2d::prelude::*;
use crate::audio::PlaySoundEvent;
use crate::render::{TextureAtlasRegistry, YukkuriTypeRegistry};
use crate::ai::{WorldSettings, Needs, EmotionalState, YukkuriStats};
use crate::camera::CameraController;
use super::YukkuriDragState;

// ---------------------------------------------------------------------------
// Floating Text Component & Event
// ---------------------------------------------------------------------------

#[derive(Message, Debug, Clone)]
pub struct SpawnFloatingTextEvent {
    pub position: Vec2,
    pub text: String,
    pub color: Color,
}

#[derive(Component)]
pub struct FloatingText {
    pub timer: f32,
    pub duration: f32,
    pub velocity: Vec2,
}

pub fn spawn_floating_text_system(
    mut commands: Commands,
    _asset_server: Res<AssetServer>,
    mut event_reader: MessageReader<SpawnFloatingTextEvent>,
) {
    // In Bevy 0.15+, we can just spawn Text2d components
    for ev in event_reader.read() {
        commands.spawn((
            Text2d::new(ev.text.clone()),
            TextFont {
                font_size: FontSize::Px(16.0),
                ..default()
            },
            TextColor(ev.color),
            Transform::from_xyz(ev.position.x, ev.position.y, 90.0),
            FloatingText {
                timer: 0.0,
                duration: 2.0,
                velocity: Vec2::new(0.0, 30.0), // move up 30px per sec
            },
        ));
    }
}

pub fn update_floating_text_system(
    mut commands: Commands,
    time: Res<Time>,
    mut query: Query<(Entity, &mut Transform, &mut TextColor, &mut FloatingText)>,
) {
    let dt = time.delta_secs();
    for (entity, mut transform, mut color, mut float) in query.iter_mut() {
        float.timer += dt;
        if float.timer >= float.duration {
            commands.entity(entity).despawn();
        } else {
            transform.translation.x += float.velocity.x * dt;
            transform.translation.y += float.velocity.y * dt;
            
            // Fade out in the last half of the duration
            let fade_start = float.duration * 0.5;
            if float.timer > fade_start {
                let alpha = 1.0 - ((float.timer - fade_start) / (float.duration - fade_start));
                color.0.set_alpha(alpha);
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Types & Components
// ---------------------------------------------------------------------------

#[derive(Clone, Copy, Debug, PartialEq, Eq, Reflect, Default)]
pub enum ShopTab {
    #[default]
    Food,
    Furniture,
    Toys,
}

#[derive(Clone, Debug, PartialEq)]
pub enum UiAction {
    SpawnReimu,
    TestSound(String),
    SellEntity,
    TrainEntity,
    PunishEntity,
    InspectEntity,
    PickUpEntity,
    FeedEntity,
    PatEntity,
    SlapEntity,
    DeleteEntity,
    ToggleShop,
    SelectShopTab(ShopTab),
    BuyItem { item_id: String, cost: i32 },
    PauseResume,
    SpeedUp,
    SpeedDown,
    SaveGame,
    LoadGame,
    ToggleSettings,
    SelectCleanTool,
    SelectTeleportTool,
    VolumeUp { category: String },
    VolumeDown { category: String },
    ToggleFullscreen,
}

#[derive(Component)]
pub struct YukkuriUiButton {
    pub action: UiAction,
}

#[derive(Component)]
pub struct ShopPanel;

#[derive(Component)]
pub struct ShopTabButton {
    pub tab: ShopTab,
}

#[derive(Component)]
pub struct ShopContentContainer;

#[derive(Resource, Default, Debug, Clone)]
pub struct ActiveShopTab {
    pub tab: ShopTab,
    pub open: bool,
}


#[derive(Component)]
pub struct HudYukkuriOnlyAction;

#[derive(Component)]
pub struct HudSelectionCard;

#[derive(Component)]
pub struct HudNameText;

#[derive(Component)]
pub struct HudBreedText;

#[derive(Component)]
pub struct HudStageText;

#[derive(Component)]
pub struct HudInventoryText;

#[derive(Component)]
pub struct HudBarFill {
    pub need_type: String, // "health", "hunger", "energy", "happiness", "stress"
}

#[derive(Component)]
pub struct HudHoverTooltip;

#[derive(Component)]
pub struct HudHoverTooltipText;

#[derive(Component)]
pub struct HudMoneyText;

#[derive(Component)]
pub struct HudTimeText;

#[derive(Component)]
pub struct HudLogContainer;

#[derive(Component)]
pub struct SettingsPopupNode;

#[derive(Component)]
pub struct SettingsVolumeText {
    pub category: String,
}

#[derive(Resource, Default, Debug, Clone)]
pub struct CleanToolActive(pub bool);

#[derive(Resource, Default, Debug, Clone)]
pub struct TeleportToolActive(pub bool);

const BUTTON_NORMAL_COLOR: Color = Color::srgba(0.18, 0.18, 0.22, 0.9);
const BUTTON_HOVER_COLOR: Color = Color::srgba(0.25, 0.25, 0.30, 1.0);
const BUTTON_PRESSED_COLOR: Color = Color::srgba(0.35, 0.35, 0.45, 1.0);

// ---------------------------------------------------------------------------
// Setup System
// ---------------------------------------------------------------------------

pub fn setup_hud_system(mut commands: Commands) {
    // 1. Root HUD panel — anchored to the bottom of the screen.
    commands
        .spawn((
            Node {
                width: Val::Percent(100.0),
                height: Val::Px(120.0),
                position_type: PositionType::Absolute,
                left: Val::Px(0.0),
                bottom: Val::Px(0.0),
                justify_content: JustifyContent::SpaceBetween,
                align_items: AlignItems::Center,
                padding: UiRect::all(Val::Px(10.0)),
                ..default()
            },
            BackgroundColor(Color::srgba(0.08, 0.08, 0.1, 0.75)),
        ))
        .with_children(|parent| {
            // Left Container: Spawn, Clean, and sound buttons row
            parent
                .spawn((
                    Node {
                        display: Display::Flex,
                        flex_direction: FlexDirection::Row,
                        align_items: AlignItems::Center,
                        column_gap: Val::Px(10.0),
                        padding: UiRect::horizontal(Val::Px(12.0)),
                        height: Val::Percent(100.0),
                        border: UiRect::all(Val::Px(1.0)),
                        border_radius: BorderRadius::all(Val::Px(12.0)),
                        ..default()
                    },
                    BackgroundColor(Color::srgba(0.12, 0.12, 0.16, 0.85)),
                    BorderColor::all(Color::srgba(0.4, 0.4, 0.45, 0.4)),
                ))
                .with_children(|inner| {
                    spawn_hud_button(inner, "Shop", UiAction::ToggleShop);
                    spawn_hud_button(inner, "Clean", UiAction::SelectCleanTool);
                    spawn_hud_button(inner, "Teleport", UiAction::SelectTeleportTool);
                    spawn_hud_button(inner, "Spawn Reimu", UiAction::SpawnReimu);

                    for sound in ["click", "place", "cancel", "sell", "train", "eat", "cry"] {
                        spawn_hud_button(
                            inner,
                            &format!("Play {sound}"),
                            UiAction::TestSound(sound.to_string()),
                        );
                    }
                });

            // Right Container: Detailed selected stats card (starts hidden/empty)
            parent
                .spawn((
                    HudSelectionCard,
                    Node {
                        display: Display::None, // Hidden when nothing is selected
                        flex_direction: FlexDirection::Row,
                        align_items: AlignItems::Center,
                        column_gap: Val::Px(15.0),
                        padding: UiRect::all(Val::Px(10.0)),
                        width: Val::Px(600.0),
                        height: Val::Percent(100.0),
                        border: UiRect::all(Val::Px(1.0)),
                        border_radius: BorderRadius::all(Val::Px(12.0)),
                        ..default()
                    },
                    BackgroundColor(Color::srgba(0.12, 0.12, 0.16, 0.9)),
                    BorderColor::all(Color::srgba(0.4, 0.4, 0.45, 0.4)),
                ))
                .with_children(|card| {
                    // Entity Identity Column
                    card.spawn(Node {
                        flex_direction: FlexDirection::Column,
                        width: Val::Px(120.0),
                        row_gap: Val::Px(4.0),
                        ..default()
                    })
                    .with_children(|id_col| {
                        id_col.spawn((
                            HudNameText,
                            Text::new("Name: "),
                            TextFont { font_size: FontSize::Px(12.0), ..default() },
                            TextColor(Color::srgb(0.9, 0.9, 0.95)),
                        ));
                        id_col.spawn((
                            HudBreedText,
                            Text::new("Breed: "),
                            TextFont { font_size: FontSize::Px(11.0), ..default() },
                            TextColor(Color::srgb(0.65, 0.65, 0.7)),
                        ));
                        id_col.spawn((
                            HudStageText,
                            Text::new("Stage: "),
                            TextFont { font_size: FontSize::Px(11.0), ..default() },
                            TextColor(Color::srgb(0.65, 0.65, 0.7)),
                        ));
                    });

                    // Needs Progress Bars Column
                    card.spawn(Node {
                        flex_direction: FlexDirection::Column,
                        flex_grow: 1.0,
                        row_gap: Val::Px(4.0),
                        ..default()
                    })
                    .with_children(|bars_col| {
                        spawn_needs_progress_bar(bars_col, "Health", "health", Color::srgb(0.2, 0.7, 0.2));
                        spawn_needs_progress_bar(bars_col, "Hunger", "hunger", Color::srgb(0.8, 0.3, 0.1));
                        spawn_needs_progress_bar(bars_col, "Energy", "energy", Color::srgb(0.85, 0.85, 0.1));
                        spawn_needs_progress_bar(bars_col, "Happy", "happiness", Color::srgb(0.9, 0.4, 0.6));
                        spawn_needs_progress_bar(bars_col, "Stress", "stress", Color::srgb(0.6, 0.4, 0.4));
                    });

                    // Inventory Column
                    card.spawn(Node {
                        flex_direction: FlexDirection::Column,
                        width: Val::Px(150.0),
                        row_gap: Val::Px(4.0),
                        ..default()
                    })
                    .with_children(|inv_col| {
                        inv_col.spawn((
                            Text::new("Inventory:"),
                            TextFont { font_size: FontSize::Px(11.0), ..default() },
                            TextColor(Color::srgb(0.9, 0.9, 0.95)),
                        ));
                        inv_col.spawn((
                            HudInventoryText,
                            Text::new("Empty"),
                            TextFont { font_size: FontSize::Px(10.0), ..default() },
                            TextColor(Color::srgb(0.7, 0.7, 0.75)),
                        ));
                    });

                    // Actions Column
                    card.spawn(Node {
                        flex_direction: FlexDirection::Column,
                        width: Val::Px(100.0),
                        row_gap: Val::Px(6.0),
                        justify_content: JustifyContent::Center,
                        align_items: AlignItems::Center,
                        ..default()
                    })
                    .with_children(|actions_col| {
                        spawn_action_button(actions_col, "Sell", UiAction::SellEntity, false);
                        spawn_action_button(actions_col, "Train", UiAction::TrainEntity, true);
                        spawn_action_button(actions_col, "Punish", UiAction::PunishEntity, true);
                    });
                });
        });

    // 2. Root Top Bar panel
    commands
        .spawn((
            Node {
                width: Val::Percent(100.0),
                height: Val::Px(40.0),
                position_type: PositionType::Absolute,
                left: Val::Px(0.0),
                top: Val::Px(0.0),
                justify_content: JustifyContent::SpaceBetween,
                align_items: AlignItems::Center,
                padding: UiRect::horizontal(Val::Px(15.0)),
                ..default()
            },
            BackgroundColor(Color::srgba(0.08, 0.08, 0.1, 0.85)),
        ))
        .with_children(|parent| {
            // Left container: Money and Time
            parent.spawn(Node {
                display: Display::Flex,
                flex_direction: FlexDirection::Row,
                column_gap: Val::Px(20.0),
                align_items: AlignItems::Center,
                ..default()
            })
            .with_children(|left| {
                left.spawn((
                    HudMoneyText,
                    Text::new("Money: $0"),
                    TextFont { font_size: FontSize::Px(14.0), ..default() },
                    TextColor(Color::srgb(0.3, 0.85, 0.3)),
                ));
                left.spawn((
                    HudTimeText,
                    Text::new("Day 1 - 12:00"),
                    TextFont { font_size: FontSize::Px(14.0), ..default() },
                    TextColor(Color::srgb(0.9, 0.9, 0.95)),
                ));
            });

            // Right container: Controls & Buttons
            parent.spawn(Node {
                display: Display::Flex,
                flex_direction: FlexDirection::Row,
                column_gap: Val::Px(10.0),
                align_items: AlignItems::Center,
                ..default()
            })
            .with_children(|right| {
                spawn_hud_button(right, "Pause", UiAction::PauseResume);
                spawn_hud_button(right, "0.5x", UiAction::SpeedDown);
                spawn_hud_button(right, "2x", UiAction::SpeedUp);
                spawn_hud_button(right, "Save", UiAction::SaveGame);
                spawn_hud_button(right, "Load", UiAction::LoadGame);
                spawn_hud_button(right, "Settings", UiAction::ToggleSettings);
            });
        });

    // 3. Log Panel (above bottom HUD)
    commands
        .spawn((
            Node {
                position_type: PositionType::Absolute,
                left: Val::Px(10.0),
                bottom: Val::Px(130.0),
                width: Val::Px(350.0),
                height: Val::Px(200.0),
                flex_direction: FlexDirection::Column,
                padding: UiRect::all(Val::Px(10.0)),
                border_radius: BorderRadius::all(Val::Px(8.0)),
                overflow: Overflow::clip(),
                ..default()
            },
            BackgroundColor(Color::srgba(0.08, 0.08, 0.1, 0.65)),
            BorderColor::all(Color::srgba(0.4, 0.4, 0.45, 0.3)),
        ))
        .with_children(|parent| {
            parent.spawn((
                Text::new("Activity Log"),
                TextFont { font_size: FontSize::Px(12.0), ..default() },
                TextColor(Color::srgb(0.7, 0.7, 0.75)),
                Node {
                    margin: UiRect::bottom(Val::Px(6.0)),
                    ..default()
                },
            ));
            
            // Vertical log items list
            parent.spawn((
                HudLogContainer,
                Node {
                    flex_direction: FlexDirection::Column,
                    flex_grow: 1.0,
                    max_height: Val::Px(130.0),
                    row_gap: Val::Px(4.0),
                    overflow: Overflow::scroll_y(),
                    ..default()
                },
                ScrollPosition::default(),
                Interaction::default(),
            ));
        });

    // 4. Settings Volume Popup Panel (hidden by default)
    commands
        .spawn((
            SettingsPopupNode,
            Node {
                position_type: PositionType::Absolute,
                width: Val::Px(350.0),
                height: Val::Px(280.0),
                left: Val::Percent(35.0),
                top: Val::Percent(25.0),
                display: Display::None, // Hidden initially
                flex_direction: FlexDirection::Column,
                padding: UiRect::all(Val::Px(15.0)),
                row_gap: Val::Px(12.0),
                border_radius: BorderRadius::all(Val::Px(12.0)),
                border: UiRect::all(Val::Px(1.0)),
                ..default()
            },
            BackgroundColor(Color::srgba(0.06, 0.06, 0.08, 0.95)),
            BorderColor::all(Color::srgba(0.4, 0.4, 0.45, 0.5)),
        ))
        .with_children(|parent| {
            // Header
            parent.spawn(Node {
                justify_content: JustifyContent::SpaceBetween,
                align_items: AlignItems::Center,
                ..default()
            })
            .with_children(|header| {
                header.spawn((
                    Text::new("Settings"),
                    TextFont { font_size: FontSize::Px(18.0), ..default() },
                    TextColor(Color::srgb(0.9, 0.9, 0.95)),
                ));
                // Close button
                spawn_hud_button(header, "X", UiAction::ToggleSettings);
            });

            // Master Volume row
            parent.spawn(Node {
                justify_content: JustifyContent::SpaceBetween,
                align_items: AlignItems::Center,
                ..default()
            })
            .with_children(|row| {
                row.spawn((
                    Text::new("Master Volume:"),
                    TextFont { font_size: FontSize::Px(13.0), ..default() },
                    TextColor(Color::srgb(0.8, 0.8, 0.85)),
                ));
                row.spawn(Node {
                    flex_direction: FlexDirection::Row,
                    align_items: AlignItems::Center,
                    column_gap: Val::Px(8.0),
                    ..default()
                })
                .with_children(|ctrl| {
                    spawn_volume_adjust_button(ctrl, "-", UiAction::VolumeDown { category: "master".to_string() });
                    ctrl.spawn((
                        SettingsVolumeText { category: "master".to_string() },
                        Text::new("100%"),
                        TextFont { font_size: FontSize::Px(13.0), ..default() },
                        TextColor(Color::srgb(0.9, 0.9, 0.95)),
                    ));
                    spawn_volume_adjust_button(ctrl, "+", UiAction::VolumeUp { category: "master".to_string() });
                });
            });

            // BGM Volume row
            parent.spawn(Node {
                justify_content: JustifyContent::SpaceBetween,
                align_items: AlignItems::Center,
                ..default()
            })
            .with_children(|row| {
                row.spawn((
                    Text::new("BGM Volume:"),
                    TextFont { font_size: FontSize::Px(13.0), ..default() },
                    TextColor(Color::srgb(0.8, 0.8, 0.85)),
                ));
                row.spawn(Node {
                    flex_direction: FlexDirection::Row,
                    align_items: AlignItems::Center,
                    column_gap: Val::Px(8.0),
                    ..default()
                })
                .with_children(|ctrl| {
                    spawn_volume_adjust_button(ctrl, "-", UiAction::VolumeDown { category: "bgm".to_string() });
                    ctrl.spawn((
                        SettingsVolumeText { category: "bgm".to_string() },
                        Text::new("100%"),
                        TextFont { font_size: FontSize::Px(13.0), ..default() },
                        TextColor(Color::srgb(0.9, 0.9, 0.95)),
                    ));
                    spawn_volume_adjust_button(ctrl, "+", UiAction::VolumeUp { category: "bgm".to_string() });
                });
            });

            // SFX Volume row
            parent.spawn(Node {
                justify_content: JustifyContent::SpaceBetween,
                align_items: AlignItems::Center,
                ..default()
            })
            .with_children(|row| {
                row.spawn((
                    Text::new("SFX Volume:"),
                    TextFont { font_size: FontSize::Px(13.0), ..default() },
                    TextColor(Color::srgb(0.8, 0.8, 0.85)),
                ));
                row.spawn(Node {
                    flex_direction: FlexDirection::Row,
                    align_items: AlignItems::Center,
                    column_gap: Val::Px(8.0),
                    ..default()
                })
                .with_children(|ctrl| {
                    spawn_volume_adjust_button(ctrl, "-", UiAction::VolumeDown { category: "sfx".to_string() });
                    ctrl.spawn((
                        SettingsVolumeText { category: "sfx".to_string() },
                        Text::new("100%"),
                        TextFont { font_size: FontSize::Px(13.0), ..default() },
                        TextColor(Color::srgb(0.9, 0.9, 0.95)),
                    ));
                    spawn_volume_adjust_button(ctrl, "+", UiAction::VolumeUp { category: "sfx".to_string() });
                });
            });

            // Fullscreen toggle row
            parent.spawn(Node {
                justify_content: JustifyContent::SpaceBetween,
                align_items: AlignItems::Center,
                ..default()
            })
            .with_children(|row| {
                row.spawn((
                    Text::new("Screen Mode:"),
                    TextFont { font_size: FontSize::Px(13.0), ..default() },
                    TextColor(Color::srgb(0.8, 0.8, 0.85)),
                ));
                spawn_hud_button(row, "Toggle Fullscreen", UiAction::ToggleFullscreen);
            });
        });

    // Root Shop Panel - positioned above the bottom HUD bar, starts hidden (Display::None).
    commands
        .spawn((
            ShopPanel,
            Node {
                display: Display::None,
                position_type: PositionType::Absolute,
                left: Val::Px(20.0),
                bottom: Val::Px(130.0),
                width: Val::Px(550.0),
                height: Val::Px(280.0),
                flex_direction: FlexDirection::Column,
                border_radius: BorderRadius::all(Val::Px(12.0)),
                border: UiRect::all(Val::Px(1.0)),
                padding: UiRect::all(Val::Px(10.0)),
                ..default()
            },
            BackgroundColor(Color::srgba(0.08, 0.08, 0.1, 0.9)),
            BorderColor::all(Color::srgba(0.4, 0.4, 0.45, 0.4)),
        ))
        .with_children(|shop| {
            // Header with tabs: [Food] [Furniture] [Toys]
            shop.spawn(Node {
                flex_direction: FlexDirection::Row,
                column_gap: Val::Px(8.0),
                height: Val::Px(35.0),
                align_items: AlignItems::Center,
                ..default()
            })
            .with_children(|tabs| {
                spawn_tab_button(tabs, "Food", ShopTab::Food, true);
                spawn_tab_button(tabs, "Furniture", ShopTab::Furniture, false);
                spawn_tab_button(tabs, "Toys", ShopTab::Toys, false);
            });
            
            // Separator line
            shop.spawn((
                Node {
                    width: Val::Percent(100.0),
                    height: Val::Px(1.0),
                    margin: UiRect::vertical(Val::Px(6.0)),
                    ..default()
                },
                BackgroundColor(Color::srgba(0.4, 0.4, 0.45, 0.3)),
            ));

            // Content container: Grid of items for the active tab
            shop.spawn((
                ShopContentContainer,
                Node {
                    display: Display::Flex,
                    flex_direction: FlexDirection::Row,
                    flex_wrap: FlexWrap::Wrap,
                    column_gap: Val::Px(12.0),
                    row_gap: Val::Px(12.0),
                    flex_grow: 1.0,
                    ..default()
                },
            ));
        });

    // Spawn Hover Tooltip Panel (Glassmorphic design)
    commands.spawn((
        HudHoverTooltip,
        Node {
            position_type: PositionType::Absolute,
            display: Display::None,
            flex_direction: FlexDirection::Column,
            padding: UiRect::all(Val::Px(6.0)),
            border: UiRect::all(Val::Px(1.0)),
            border_radius: BorderRadius::all(Val::Px(6.0)),
            ..default()
        },
        BackgroundColor(Color::srgba(0.08, 0.08, 0.12, 0.85)),
        BorderColor::all(Color::srgba(0.4, 0.4, 0.45, 0.5)),
    ))
    .with_children(|parent| {
        parent.spawn((
            HudHoverTooltipText,
            Text::new(""),
            TextFont { font_size: FontSize::Px(11.0), ..default() },
            TextColor(Color::srgb(0.95, 0.95, 1.0)),
        ));
    });
}

fn spawn_tab_button(
    parent: &mut ChildSpawnerCommands,
    label: &str,
    tab: ShopTab,
    _active: bool,
) {
    parent
        .spawn((
            Button,
            ShopTabButton { tab },
            Node {
                padding: UiRect::axes(Val::Px(10.0), Val::Px(4.0)),
                justify_content: JustifyContent::Center,
                align_items: AlignItems::Center,
                border_radius: BorderRadius::all(Val::Px(6.0)),
                ..default()
            },
            BackgroundColor(BUTTON_NORMAL_COLOR),
            BorderColor::all(Color::srgba(0.3, 0.3, 0.35, 0.5)),
            YukkuriUiButton { action: UiAction::SelectShopTab(tab) },
        ))
        .with_children(|btn| {
            btn.spawn((
                Text::new(label),
                TextFont { font_size: FontSize::Px(11.0), ..default() },
                TextColor(Color::srgb(0.95, 0.95, 0.95)),
            ));
        });
}

pub fn update_shop_ui_system(
    mut commands: Commands,
    active_tab: Res<ActiveShopTab>,
    mut query_panel: Query<&mut Node, With<ShopPanel>>,
    query_container: Query<Entity, With<ShopContentContainer>>,
    mut query_tab_btns: Query<(&ShopTabButton, &mut BackgroundColor)>,
) {
    if !active_tab.is_changed() {
        return;
    }

    if let Ok(mut panel_node) = query_panel.single_mut() {
        panel_node.display = if active_tab.open { Display::Flex } else { Display::None };
    }

    if !active_tab.open {
        return;
    }

    for (btn, mut bg) in query_tab_btns.iter_mut() {
        if btn.tab == active_tab.tab {
            *bg = BackgroundColor(Color::srgba(0.3, 0.3, 0.45, 1.0));
        } else {
            *bg = BackgroundColor(BUTTON_NORMAL_COLOR);
        }
    }

    if let Ok(container_ent) = query_container.single() {
        commands.entity(container_ent).despawn_related::<Children>();
        
        let items = match active_tab.tab {
            ShopTab::Food => vec![
                ("cookie", "Cookie", 10, "Restores hunger & joy"),
                ("super_cookie", "Super Cookie", 50, "Restores lots of needs"),
            ],
            ShopTab::Furniture => vec![
                ("bed", "Soft Bed", 100, "Comfortable sleeping spot"),
                ("lamp", "Street Lamp", 50, "Illuminates dark areas"),
                ("wall", "Brick Wall", 20, "Blocks movement and light"),
            ],
            ShopTab::Toys => vec![
                ("toy", "Ball", 25, "Restores fun when played"),
            ],
        };

        commands.entity(container_ent).with_children(|parent| {
            for (id, name, cost, desc) in items {
                parent
                    .spawn((
                        Button,
                        Node {
                            width: Val::Px(160.0),
                            height: Val::Px(65.0),
                            flex_direction: FlexDirection::Column,
                            justify_content: JustifyContent::SpaceBetween,
                            padding: UiRect::all(Val::Px(6.0)),
                            border_radius: BorderRadius::all(Val::Px(8.0)),
                            ..default()
                        },
                        BackgroundColor(BUTTON_NORMAL_COLOR),
                        BorderColor::all(Color::srgba(0.3, 0.3, 0.35, 0.5)),
                        YukkuriUiButton {
                            action: UiAction::BuyItem {
                                item_id: id.to_string(),
                                cost,
                            },
                        },
                    ))
                    .with_children(|btn| {
                        btn.spawn((
                            Text::new(name),
                            TextFont { font_size: FontSize::Px(12.0), ..default() },
                            TextColor(Color::srgb(0.95, 0.95, 0.95)),
                        ));
                        btn.spawn((
                            Text::new(desc),
                            TextFont { font_size: FontSize::Px(9.0), ..default() },
                            TextColor(Color::srgb(0.7, 0.7, 0.75)),
                        ));
                        btn.spawn((
                            Text::new(format!("Cost: ${cost}")),
                            TextFont { font_size: FontSize::Px(10.0), ..default() },
                            TextColor(Color::srgb(0.3, 0.85, 0.3)),
                        ));
                    });
            }
        });
    }
}

fn spawn_action_button(
    parent: &mut ChildSpawnerCommands,
    label: &str,
    action: UiAction,
    yukkuri_only: bool,
) {
    let mut btn = parent.spawn((
        Button,
        Node {
            width: Val::Px(80.0),
            height: Val::Px(24.0),
            justify_content: JustifyContent::Center,
            align_items: AlignItems::Center,
            border_radius: BorderRadius::all(Val::Px(6.0)),
            ..default()
        },
        BackgroundColor(BUTTON_NORMAL_COLOR),
        BorderColor::all(Color::srgba(0.3, 0.3, 0.35, 0.5)),
        YukkuriUiButton { action },
    ));
    if yukkuri_only {
        btn.insert(HudYukkuriOnlyAction);
    }
    btn.with_children(|inner| {
        inner.spawn((
            Text::new(label),
            TextFont {
                font_size: FontSize::Px(11.0),
                ..default()
            },
            TextColor(Color::srgb(0.95, 0.95, 0.95)),
        ));
    });
}

fn spawn_hud_button(parent: &mut ChildSpawnerCommands, label: &str, action: UiAction) {
    parent
        .spawn((
            Button,
            Node {
                padding: UiRect::axes(Val::Px(12.0), Val::Px(8.0)),
                justify_content: JustifyContent::Center,
                align_items: AlignItems::Center,
                border: UiRect::all(Val::Px(1.0)),
                border_radius: BorderRadius::all(Val::Px(8.0)),
                ..default()
            },
            BackgroundColor(BUTTON_NORMAL_COLOR),
            BorderColor::all(Color::srgba(0.3, 0.3, 0.35, 0.5)),
            YukkuriUiButton { action },
        ))
        .with_children(|btn| {
            btn.spawn((
                Text::new(label),
                TextFont {
                    font_size: FontSize::Px(12.0),
                    ..default()
                },
                TextColor(Color::srgb(0.95, 0.95, 0.95)),
            ));
        });
}

fn spawn_volume_adjust_button(parent: &mut ChildSpawnerCommands, label: &str, action: UiAction) {
    parent
        .spawn((
            Button,
            Node {
                width: Val::Px(24.0),
                height: Val::Px(24.0),
                justify_content: JustifyContent::Center,
                align_items: AlignItems::Center,
                border_radius: BorderRadius::all(Val::Px(4.0)),
                ..default()
            },
            BackgroundColor(BUTTON_NORMAL_COLOR),
            BorderColor::all(Color::srgba(0.3, 0.3, 0.35, 0.5)),
            YukkuriUiButton { action },
        ))
        .with_children(|btn| {
            btn.spawn((
                Text::new(label),
                TextFont { font_size: FontSize::Px(12.0), ..default() },
                TextColor(Color::srgb(0.95, 0.95, 0.95)),
            ));
        });
}

pub fn save_user_settings(
    audio_manager: &crate::audio::YukkuriAudioManager,
    width: f32,
    height: f32,
    fullscreen: bool,
) {
    use serde::Serialize;
    
    #[derive(Serialize)]
    struct AudioOut {
        master_volume: f32,
        bgm_volume: f32,
        sfx_volume: f32,
    }
    
    #[derive(Serialize)]
    struct WindowOut {
        width: f32,
        height: f32,
        fullscreen: bool,
    }
    
    #[derive(Serialize)]
    struct SettingsOut {
        audio: AudioOut,
        window: WindowOut,
    }
    
    let out = SettingsOut {
        audio: AudioOut {
            master_volume: audio_manager.master_volume,
            bgm_volume: audio_manager.bgm_volume,
            sfx_volume: audio_manager.sfx_volume,
        },
        window: WindowOut {
            width,
            height,
            fullscreen,
        },
    };
    
    let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("data")
        .join("user_settings.toml");
        
    if let Ok(contents) = toml::to_string(&out) {
        let _ = std::fs::write(path, contents);
    }
}

fn spawn_needs_progress_bar(
    parent: &mut ChildSpawnerCommands,
    label: &str,
    need_type: &str,
    color: Color,
) {
    parent.spawn(Node {
        flex_direction: FlexDirection::Row,
        align_items: AlignItems::Center,
        justify_content: JustifyContent::SpaceBetween,
        ..default()
    })
    .with_children(|row| {
        // Label
        row.spawn((
            Text::new(label),
            TextFont { font_size: FontSize::Px(10.0), ..default() },
            TextColor(Color::srgb(0.8, 0.8, 0.8)),
        ));

        // Bar container
        row.spawn(Node {
            width: Val::Px(180.0),
            height: Val::Px(8.0),
            ..default()
        })
        .with_children(|bar_container| {
            // Background
            bar_container.spawn((
                Node {
                    width: Val::Percent(100.0),
                    height: Val::Percent(100.0),
                    ..default()
                },
                BackgroundColor(Color::srgba(0.2, 0.2, 0.25, 0.6)),
            ))
            .with_children(|inner| {
                // Fill
                inner.spawn((
                    HudBarFill { need_type: need_type.to_string() },
                    Node {
                        width: Val::Percent(50.0), // Starts middle
                        height: Val::Percent(100.0),
                        ..default()
                    },
                    BackgroundColor(color),
                ));
            });
        });
    });
}

// ---------------------------------------------------------------------------
// HUD Interaction & Logic
// ---------------------------------------------------------------------------

#[derive(bevy::ecs::system::SystemParam)]
pub struct HudInteractionParams<'w, 's> {
    pub commands: Commands<'w, 's>,
    pub asset_server: Res<'w, AssetServer>,
    pub atlas_registry: Res<'w, TextureAtlasRegistry>,
    pub type_registry: Res<'w, YukkuriTypeRegistry>,
    pub world_settings: Res<'w, WorldSettings>,
    pub active_tab: ResMut<'w, ActiveShopTab>,
    pub placement_state: ResMut<'w, super::placement::PlacementState>,
    pub economy: Res<'w, crate::ai::persistence::Economy>,
    pub clean_tool_active: Option<ResMut<'w, CleanToolActive>>,
    pub teleport_tool_active: Option<ResMut<'w, TeleportToolActive>>,
    pub audio_manager: Option<ResMut<'w, crate::audio::YukkuriAudioManager>>,
}

pub fn hud_interaction_system(
    mut interaction_query: Query<
        (&Interaction, &mut BackgroundColor, &YukkuriUiButton),
        (Changed<Interaction>, With<Button>),
    >,
    mut message_writer: MessageWriter<PlaySoundEvent>,
    mut params: HudInteractionParams,
    camera_controller_query: Query<&CameraController>,
    mut sell_writer: MessageWriter<crate::simulation::player_actions::SellEntityRequest>,
    mut train_writer: MessageWriter<crate::simulation::player_actions::TrainEntityRequest>,
    mut punish_writer: MessageWriter<crate::simulation::player_actions::PunishEntityRequest>,
    mut time_elapsed: Option<ResMut<crate::ai::persistence::TimeElapsed>>,
    mut settings_popup_query: Query<&mut Node, (With<SettingsPopupNode>, Without<HudSelectionCard>, Without<ShopPanel>)>,
    mut window_query: Query<&mut Window, With<bevy::window::PrimaryWindow>>,
) {
    for (interaction, mut bg_color, ui_btn) in &mut interaction_query {
        match *interaction {
            Interaction::Pressed => {
                *bg_color = BackgroundColor(BUTTON_PRESSED_COLOR);
                message_writer.write(PlaySoundEvent { name: "click".to_string() });

                match &ui_btn.action {
                    UiAction::SpawnReimu => {
                        let prefab_path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
                            .join("data")
                            .join("prefabs")
                            .join("reimu.toml");

                        let path_str = prefab_path.to_str().unwrap_or("data/prefabs/reimu.toml");

                        if let Ok(prefab) = crate::prefabs::load_prefab(path_str) {
                            let center = Vec2::new(
                                params.world_settings.width / 2.0,
                                params.world_settings.height / 2.0,
                            );
                            crate::prefabs::spawn_yukkuri_prefab(
                                &mut params.commands,
                                &prefab,
                                center,
                                &params.asset_server,
                                &params.atlas_registry,
                                &params.type_registry,
                            );
                            message_writer.write(PlaySoundEvent { name: "place".to_string() });
                        } else {
                            eprintln!("[HUD UI] Failed to load reimu prefab: {path_str}");
                        }
                    }
                    UiAction::TestSound(sound_name) => {
                        message_writer.write(PlaySoundEvent { name: sound_name.clone() });
                    }
                    UiAction::SellEntity => {
                        if let Some(selected) = camera_controller_query.iter().next().and_then(|c| c.selected_entity) {
                            sell_writer.write(crate::simulation::player_actions::SellEntityRequest { entity_id: selected });
                        }
                    }
                    UiAction::TrainEntity => {
                        if let Some(selected) = camera_controller_query.iter().next().and_then(|c| c.selected_entity) {
                            train_writer.write(crate::simulation::player_actions::TrainEntityRequest { entity_id: selected });
                        }
                    }
                    UiAction::PunishEntity => {
                        if let Some(selected) = camera_controller_query.iter().next().and_then(|c| c.selected_entity) {
                            punish_writer.write(crate::simulation::player_actions::PunishEntityRequest { entity_id: selected });
                        }
                    }
                    UiAction::ToggleShop => {
                        params.active_tab.open = !params.active_tab.open;
                        if params.active_tab.open {
                            if let Some(ref mut clean) = params.clean_tool_active {
                                clean.0 = false;
                            }
                            if let Some(ref mut teleport) = params.teleport_tool_active {
                                teleport.0 = false;
                            }
                        }
                    }
                    UiAction::SelectShopTab(tab) => {
                        params.active_tab.tab = *tab;
                    }
                    UiAction::BuyItem { item_id, cost } => {
                        if params.economy.money >= *cost {
                            params.placement_state.active = true;
                            params.placement_state.current_item_id = item_id.clone();
                            params.placement_state.cost = *cost;
                            params.placement_state.ghost_entity = None;
                            if let Some(ref mut clean) = params.clean_tool_active {
                                clean.0 = false;
                            }
                            if let Some(ref mut teleport) = params.teleport_tool_active {
                                teleport.0 = false;
                            }
                        } else {
                            message_writer.write(PlaySoundEvent { name: "cancel".to_string() });
                        }
                    }
                    UiAction::PauseResume => {
                        if let Some(ref mut time) = time_elapsed {
                            if time.game_speed > 0.0 {
                                time.game_speed = 0.0;
                            } else {
                                time.game_speed = 1.0;
                            }
                        }
                    }
                    UiAction::SpeedUp => {
                        if let Some(ref mut time) = time_elapsed {
                            time.game_speed = (time.game_speed + 0.5).min(5.0);
                        }
                    }
                    UiAction::SpeedDown => {
                        if let Some(ref mut time) = time_elapsed {
                            time.game_speed = (time.game_speed - 0.5).max(0.5);
                        }
                    }
                    UiAction::SaveGame => {
                        let filepath = "saves/quicksave.sqlite";
                        params.commands.queue(move |world: &mut World| {
                            if let Err(e) = crate::ai::persistence::save_game(world, filepath) {
                                error!("Failed to save game: {}", e);
                            } else {
                                info!("Game saved successfully.");
                            }
                        });
                    }
                    UiAction::LoadGame => {
                        let filepath = "saves/quicksave.sqlite";
                        if std::path::Path::new(filepath).exists() {
                            params.commands.queue(move |world: &mut World| {
                                if let Err(e) = crate::ai::persistence::load_game(world, filepath) {
                                    error!("Failed to load game: {}", e);
                                } else {
                                    info!("Game loaded successfully.");
                                }
                            });
                        }
                    }
                    UiAction::ToggleSettings => {
                        for mut node in &mut settings_popup_query {
                            node.display = match node.display {
                                Display::None => Display::Flex,
                                _ => Display::None,
                            };
                        }
                    }
                    UiAction::SelectCleanTool => {
                        if let Some(ref mut clean) = params.clean_tool_active {
                            clean.0 = !clean.0;
                            if clean.0 {
                                params.placement_state.active = false;
                                params.active_tab.open = false;
                                if let Some(ref mut teleport) = params.teleport_tool_active {
                                    teleport.0 = false;
                                }
                            }
                        }
                    }
                    UiAction::SelectTeleportTool => {
                        if let Some(ref mut teleport) = params.teleport_tool_active {
                            teleport.0 = !teleport.0;
                            if teleport.0 {
                                params.placement_state.active = false;
                                params.active_tab.open = false;
                                if let Some(ref mut clean) = params.clean_tool_active {
                                    clean.0 = false;
                                }
                            }
                        }
                    }
                    UiAction::VolumeUp { category } => {
                        if let Some(ref mut manager) = params.audio_manager {
                            match category.as_str() {
                                "master" => manager.master_volume = (manager.master_volume + 0.1).clamp(0.0, 1.0),
                                "bgm" => manager.bgm_volume = (manager.bgm_volume + 0.1).clamp(0.0, 1.0),
                                "sfx" => manager.sfx_volume = (manager.sfx_volume + 0.1).clamp(0.0, 1.0),
                                _ => {}
                            }
                            let primary_window = window_query.iter().next();
                            let (width, height, is_fullscreen) = if let Some(w) = primary_window {
                                (w.width(), w.height(), w.mode != bevy::window::WindowMode::Windowed)
                            } else {
                                (1280.0, 720.0, false)
                            };
                            save_user_settings(manager, width, height, is_fullscreen);
                        }
                    }
                    UiAction::VolumeDown { category } => {
                        if let Some(ref mut manager) = params.audio_manager {
                            match category.as_str() {
                                "master" => manager.master_volume = (manager.master_volume - 0.1).clamp(0.0, 1.0),
                                "bgm" => manager.bgm_volume = (manager.bgm_volume - 0.1).clamp(0.0, 1.0),
                                "sfx" => manager.sfx_volume = (manager.sfx_volume - 0.1).clamp(0.0, 1.0),
                                _ => {}
                            }
                            let primary_window = window_query.iter().next();
                            let (width, height, is_fullscreen) = if let Some(w) = primary_window {
                                (w.width(), w.height(), w.mode != bevy::window::WindowMode::Windowed)
                            } else {
                                (1280.0, 720.0, false)
                            };
                            save_user_settings(manager, width, height, is_fullscreen);
                        }
                    }
                    UiAction::ToggleFullscreen => {
                        // Avoid holding references by finding first window
                        let is_fullscreen = if let Some(mut window) = window_query.iter_mut().next() {
                            if window.mode == bevy::window::WindowMode::Windowed {
                                window.mode = bevy::window::WindowMode::Fullscreen(
                                    bevy::window::MonitorSelection::Primary,
                                    bevy::window::VideoModeSelection::Current,
                                );
                                true
                            } else {
                                window.mode = bevy::window::WindowMode::Windowed;
                                false
                            }
                        } else {
                            false
                        };
                        if let Some(ref manager) = params.audio_manager {
                            save_user_settings(manager, 1280.0, 720.0, is_fullscreen);
                        }
                    }
                    UiAction::InspectEntity
                    | UiAction::PickUpEntity
                    | UiAction::FeedEntity
                    | UiAction::PatEntity
                    | UiAction::SlapEntity
                    | UiAction::DeleteEntity => {
                        // Handled by context menu system
                    }
                }
            }
            Interaction::Hovered => {
                *bg_color = BackgroundColor(BUTTON_HOVER_COLOR);
            }
            Interaction::None => {
                *bg_color = BackgroundColor(BUTTON_NORMAL_COLOR);
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Selected Entity Stats Card & Selection Circles
// ---------------------------------------------------------------------------

/// System that draws a 2D selection circle around the currently selected entity.
pub fn draw_selection_circle_system(
    camera_query: Query<&CameraController>,
    collider_query: Query<(&Transform, &Collider)>,
    mut gizmos: Gizmos,
) {
    let Some(controller) = camera_query.iter().next() else { return; };
    if let Some(selected) = controller.selected_entity {
        if let Ok((transform, collider)) = collider_query.get(selected) {
            let pos = transform.translation.truncate();
            let radius = collider.shape().as_ball().map(|b| b.radius).unwrap_or(32.0);
            
            // Draw yellow circle around entity in 2D
            gizmos.circle_2d(pos, radius + 4.0, Color::srgb(1.0, 0.9, 0.1));
        }
    }
}

/// System that projects and renders small needs indicators floating above selected entity.
pub fn floating_needs_bars_system(
    camera_query: Query<&CameraController>,
    yukkuri_query: Query<(&Transform, &Needs, &Collider)>,
    mut gizmos: Gizmos,
) {
    let Some(controller) = camera_query.iter().next() else { return; };
    if let Some(selected) = controller.selected_entity {
        if let Ok((transform, needs, collider)) = yukkuri_query.get(selected) {
            let pos = transform.translation.truncate();
            let radius = collider.shape().as_ball().map(|b| b.radius).unwrap_or(24.0);

            let bar_y = pos.y + radius + 15.0;
            let bar_width = 40.0;
            let half_w = bar_width / 2.0;

            // 1. Health Bar (Green)
            let hp_percent = (needs.health / needs.max_health).clamp(0.0, 1.0);
            // Gray Background
            gizmos.line_2d(Vec2::new(pos.x - half_w, bar_y), Vec2::new(pos.x + half_w, bar_y), Color::srgb(0.2, 0.2, 0.22));
            // Green Fill
            gizmos.line_2d(Vec2::new(pos.x - half_w, bar_y), Vec2::new(pos.x - half_w + bar_width * hp_percent, bar_y), Color::srgb(0.2, 0.8, 0.2));

            // 2. Hunger Bar (Red/Orange)
            let hunger_percent = (needs.hunger / 100.0).clamp(0.0, 1.0);
            let hunger_y = bar_y - 4.0;
            // Gray Background
            gizmos.line_2d(Vec2::new(pos.x - half_w, hunger_y), Vec2::new(pos.x + half_w, hunger_y), Color::srgb(0.2, 0.2, 0.22));
            // Red Fill
            gizmos.line_2d(Vec2::new(pos.x - half_w, hunger_y), Vec2::new(pos.x - half_w + bar_width * hunger_percent, hunger_y), Color::srgb(0.8, 0.3, 0.1));
        }
    }
}

/// Updates the bottom HUD selection details panel based on camera selected entity.
#[derive(bevy::ecs::system::SystemParam)]
pub struct HudUpdateParams<'w, 's> {
    pub name_query: Query<'w, 's, &'static mut Text, (With<HudNameText>, Without<HudBreedText>, Without<HudStageText>, Without<HudInventoryText>, Without<HudMoneyText>, Without<HudTimeText>, Without<SettingsVolumeText>)>,
    pub breed_query: Query<'w, 's, &'static mut Text, (With<HudBreedText>, Without<HudNameText>, Without<HudStageText>, Without<HudInventoryText>, Without<HudMoneyText>, Without<HudTimeText>, Without<SettingsVolumeText>)>,
    pub stage_query: Query<'w, 's, &'static mut Text, (With<HudStageText>, Without<HudNameText>, Without<HudBreedText>, Without<HudInventoryText>, Without<HudMoneyText>, Without<HudTimeText>, Without<SettingsVolumeText>)>,
    pub inventory_text_query: Query<'w, 's, &'static mut Text, (With<HudInventoryText>, Without<HudNameText>, Without<HudBreedText>, Without<HudStageText>, Without<HudMoneyText>, Without<HudTimeText>, Without<SettingsVolumeText>)>,
    pub fills_query: Query<'w, 's, (&'static mut Node, &'static HudBarFill), (Without<HudSelectionCard>, Without<HudYukkuriOnlyAction>, Without<SettingsPopupNode>)>,
    pub yukkuri_actions_query: Query<'w, 's, &'static mut Node, (With<HudYukkuriOnlyAction>, Without<HudSelectionCard>, Without<HudBarFill>, Without<SettingsPopupNode>)>,
}

/// Updates the bottom HUD selection details panel based on camera selected entity.
pub fn hud_update_system(
    mut commands: Commands,
    camera_query: Query<&CameraController>,
    yukkuri_query: Query<(&Needs, &EmotionalState, &YukkuriStats, Option<&crate::simulation::inventory::InventoryComponent>)>,
    mut card_query: Query<&mut Node, (With<HudSelectionCard>, Without<SettingsPopupNode>)>,
    mut text_params: HudUpdateParams,
    item_query: Query<&crate::simulation::inventory::ItemStats>,
    
    // New parameters
    economy: Option<Res<crate::ai::persistence::Economy>>,
    time_elapsed: Option<Res<crate::ai::persistence::TimeElapsed>>,
    mut money_text_query: Query<&mut Text, (With<HudMoneyText>, Without<HudTimeText>, Without<HudNameText>, Without<SettingsVolumeText>)>,
    mut time_text_query: Query<&mut Text, (With<HudTimeText>, Without<HudMoneyText>, Without<HudNameText>, Without<SettingsVolumeText>)>,
    log_buffer: Option<Res<super::logging::ConsoleLogBuffer>>,
    log_container_query: Query<Entity, With<HudLogContainer>>,
    mut scroll_query: Query<&mut ScrollPosition, With<HudLogContainer>>,
    audio_manager: Option<Res<crate::audio::YukkuriAudioManager>>,
    mut settings_volume_query: Query<(&mut Text, &SettingsVolumeText), (Without<HudMoneyText>, Without<HudTimeText>, Without<HudNameText>)>,
) {
    if let Some(ref econ) = economy {
        if let Ok(mut text) = money_text_query.single_mut() {
            text.0 = format!("Money: ${}", econ.money);
        }
    }

    if let Some(ref t_el) = time_elapsed {
        if let Ok(mut text) = time_text_query.single_mut() {
            let day = t_el.day();
            let hours = t_el.hour_of_day() as i32;
            let minutes = ((t_el.hour_of_day() % 1.0) * 60.0) as i32;
            let speed = t_el.game_speed;
            let speed_str = if speed == 0.0 {
                " (Paused)".to_string()
            } else if speed != 1.0 {
                format!(" ({:.1}x)", speed)
            } else {
                "".to_string()
            };
            text.0 = format!("Day {} - {:02}:{:02}{}", day, hours, minutes, speed_str);
        }
    }

    if let Some(ref buffer) = log_buffer {
        if buffer.was_updated {
            if let Ok(container_ent) = log_container_query.single() {
                commands.entity(container_ent).despawn_children();
                let start = if buffer.logs.len() > 100 { buffer.logs.len() - 100 } else { 0 };
                for log_msg in &buffer.logs[start..] {
                    let clean_msg = if log_msg.len() > 60 { format!("{}...", &log_msg[..57]) } else { log_msg.clone() };
                    commands.entity(container_ent).with_children(|c| {
                        c.spawn((
                            Text::new(clean_msg),
                            TextFont { font_size: FontSize::Px(10.0), ..default() },
                            TextColor(Color::srgb(0.85, 0.85, 0.9)),
                        ));
                    });
                }
                if let Ok(mut scroll_pos) = scroll_query.single_mut() {
                    scroll_pos.y = f32::MAX;
                }
            }
        }
    }

    if let Some(ref manager) = audio_manager {
        for (mut text, vol_text) in &mut settings_volume_query {
            let pct = match vol_text.category.as_str() {
                "master" => (manager.master_volume * 100.0) as i32,
                "bgm" => (manager.bgm_volume * 100.0) as i32,
                "sfx" => (manager.sfx_volume * 100.0) as i32,
                _ => 100,
            };
            text.0 = format!("{}%", pct);
        }
    }

    let Some(controller) = camera_query.iter().next() else { return; };
    let Ok(mut card_node) = card_query.single_mut() else { return; };

    if let Some(selected) = controller.selected_entity {
        if let Ok((needs, emotional, stats, maybe_inventory)) = yukkuri_query.get(selected) {
            card_node.display = Display::Flex;

            // Identity Text Updates
            if let Ok(mut text) = text_params.name_query.single_mut() {
                text.0 = format!("Name: {}", stats.name);
            }
            if let Ok(mut text) = text_params.breed_query.single_mut() {
                text.0 = format!("Breed: {}", stats.type_id);
            }
            if let Ok(mut text) = text_params.stage_query.single_mut() {
                text.0 = format!("Stage: {}", stats.growth_stage);
            }

            // Inventory Text Update
            if let Ok(mut text) = text_params.inventory_text_query.single_mut() {
                if let Some(inventory) = maybe_inventory {
                    if inventory.items.is_empty() {
                        text.0 = "Empty".to_string();
                    } else {
                        let lines: Vec<String> = inventory.items.iter()
                            .map(|item| format!("{} x{}", item.item_type_id, item.quantity))
                            .collect();
                        text.0 = lines.join("\n");
                    }
                } else {
                    text.0 = "Empty".to_string();
                }
            }

            // Show Train & Punish buttons
            for mut node in &mut text_params.yukkuri_actions_query {
                node.display = Display::Flex;
            }

            // Stats Bars Fills Updates
            for (mut node, fill) in text_params.fills_query.iter_mut() {
                let percent = match fill.need_type.as_str() {
                    "health" => (needs.health / needs.max_health).clamp(0.0, 1.0),
                    "hunger" => (needs.hunger / 100.0).clamp(0.0, 1.0),
                    "energy" => (needs.energy / 100.0).clamp(0.0, 1.0),
                    "happiness" => (emotional.happiness / 100.0).clamp(0.0, 1.0),
                    "stress" => (emotional.stress / 100.0).clamp(0.0, 1.0),
                    _ => 0.0,
                };
                node.width = Val::Percent(percent as f32 * 100.0);
            }
        } else if let Ok(item_stats) = item_query.get(selected) {
            card_node.display = Display::Flex;

            // Identity Text Updates
            if let Ok(mut text) = text_params.name_query.single_mut() {
                text.0 = format!("Name: {}", item_stats.name);
            }
            if let Ok(mut text) = text_params.breed_query.single_mut() {
                text.0 = format!("Type: {}", item_stats.type_id);
            }
            if let Ok(mut text) = text_params.stage_query.single_mut() {
                text.0 = format!("Value: ${}", item_stats.value as i32);
            }

            // Inventory Text Update
            if let Ok(mut text) = text_params.inventory_text_query.single_mut() {
                text.0 = "N/A".to_string();
            }

            // Hide Train & Punish buttons
            for mut node in &mut text_params.yukkuri_actions_query {
                node.display = Display::None;
            }

            // Reset Fills to 0
            for (mut node, _fill) in text_params.fills_query.iter_mut() {
                node.width = Val::Percent(0.0);
            }
        } else {
            card_node.display = Display::None;
        }
    } else {
        card_node.display = Display::None;
    }
}

// ---------------------------------------------------------------------------
// Yukkuri dragging
// ---------------------------------------------------------------------------

pub fn yukkuri_drag_system(
    _commands: Commands,
    mouse_button_input: Res<ButtonInput<MouseButton>>,
    keyboard_input: Res<ButtonInput<KeyCode>>,
    window_query: Query<&Window>,
    camera_query: Query<(&Camera, &GlobalTransform)>,
    camera_controller_query: Query<&CameraController, With<crate::camera::MainCamera>>,
    mut drag_state: ResMut<YukkuriDragState>,
    mut yukkuri_queries: ParamSet<(
        Query<(Entity, &Transform), With<YukkuriStats>>,
        Query<
            (&mut Transform, &mut crate::simulation::kinematic_controller::KinematicVelocity),
            With<YukkuriStats>,
        >,
    )>,
) {
    let Some(window) = window_query.iter().next() else { return; };
    let Some((camera, camera_transform)) = camera_query.iter().next() else { return; };

    let Some(cursor_position) = window.cursor_position() else { return; };
    let Ok(world_pos) = camera.viewport_to_world_2d(camera_transform, cursor_position) else {
        return;
    };

    let mut world_pos_mut = world_pos;
    if keyboard_input.pressed(KeyCode::ControlLeft) || keyboard_input.pressed(KeyCode::ControlRight) {
        world_pos_mut.x = (world_pos_mut.x / 50.0).round() * 50.0;
        world_pos_mut.y = (world_pos_mut.y / 50.0).round() * 50.0;
    }

    if keyboard_input.pressed(KeyCode::AltLeft) || keyboard_input.pressed(KeyCode::AltRight) {
        if mouse_button_input.just_pressed(MouseButton::Right) {
            if let Some(controller) = camera_controller_query.iter().next() {
                for selected in &controller.selected_entities {
                    if let Ok((mut transform, mut kin_vel)) = yukkuri_queries.p1().get_mut(*selected) {
                        transform.translation.x = world_pos_mut.x;
                        transform.translation.y = world_pos_mut.y;
                        kin_vel.target = Vec2::ZERO;
                        kin_vel.current = Vec2::ZERO;
                    }
                }
            }
        }
    }

    if mouse_button_input.just_pressed(MouseButton::Left) {
        let mut closest: Option<(Entity, f32)> = None;
        for (entity, transform) in yukkuri_queries.p0().iter() {
            let dist = (transform.translation.truncate() - world_pos_mut).length();
            if dist < 40.0 {
                match closest {
                    Some((_, d)) if d <= dist => {}
                    _ => closest = Some((entity, dist)),
                }
            }
        }

        if let Some((entity, _)) = closest {
            drag_state.dragged_entity = Some(entity);
            if let Ok((_, mut kin_vel)) = yukkuri_queries.p1().get_mut(entity) {
                kin_vel.target = Vec2::ZERO;
                kin_vel.current = Vec2::ZERO;
            }
        }
    } else if mouse_button_input.pressed(MouseButton::Left) {
        if let Some(entity) = drag_state.dragged_entity {
            if let Ok((mut transform, mut kin_vel)) =
                yukkuri_queries.p1().get_mut(entity)
            {
                transform.translation.x = world_pos_mut.x;
                transform.translation.y = world_pos_mut.y;
                kin_vel.target = Vec2::ZERO;
                kin_vel.current = Vec2::ZERO;
            }
        }
    } else if mouse_button_input.just_released(MouseButton::Left) {
        if let Some(entity) = drag_state.dragged_entity.take() {
            if let Ok((_, mut kin_vel)) = yukkuri_queries.p1().get_mut(entity) {
                kin_vel.target = Vec2::ZERO;
                kin_vel.current = Vec2::ZERO;
            }
        }
    }
}

pub fn hud_hover_tooltip_system(
    window_query: Query<&Window, With<bevy::window::PrimaryWindow>>,
    camera_query: Query<(&Camera, &GlobalTransform), With<crate::camera::MainCamera>>,
    drag_state: Res<YukkuriDragState>,
    yukkuri_query: Query<(Entity, &Transform, &YukkuriStats, Option<&Needs>), Without<crate::ai::Dead>>,
    item_query: Query<(Entity, &Transform, &crate::simulation::inventory::ItemStats)>,
    mut tooltip_query: Query<&mut Node, (With<HudHoverTooltip>, Without<HudHoverTooltipText>)>,
    mut text_query: Query<&mut Text, With<HudHoverTooltipText>>,
) {
    let Some(window) = window_query.iter().next() else { return; };
    let Some((camera, camera_transform)) = camera_query.iter().next() else { return; };

    let mut tooltip_node = tooltip_query.iter_mut().next();
    let mut tooltip_text = text_query.iter_mut().next();


    let Some(ref mut node) = tooltip_node else {
        return;
    };
    let Some(ref mut text) = tooltip_text else {
        return;
    };

    // If dragging or cursor is not in window, hide tooltip
    let cursor_position = window.cursor_position();
    if drag_state.dragged_entity.is_some() || cursor_position.is_none() {
        node.display = Display::None;
        return;
    }

    let cursor_pos = cursor_position.unwrap();
    let Ok(world_pos) = camera.viewport_to_world_2d(camera_transform, cursor_pos) else {
        node.display = Display::None;
        return;
    };

    let hover_radius = 32.0;
    let mut closest_entity = None;
    let mut min_distance = f32::MAX;
    let mut tooltip_content = String::new();

    // Check Yukkuri
    for (entity, transform, stats, maybe_needs) in yukkuri_query.iter() {
        let pos = transform.translation.truncate();
        let dist = pos.distance(world_pos);
        if dist < hover_radius && dist < min_distance {
            min_distance = dist;
            closest_entity = Some(entity);
            if let Some(needs) = maybe_needs {
                tooltip_content = format!("{}\nHP: {}", stats.name, needs.health as i32);
            } else {
                tooltip_content = stats.name.clone();
            }
        }
    }

    // Check Items
    for (entity, transform, item_stats) in item_query.iter() {
        let pos = transform.translation.truncate();
        let dist = pos.distance(world_pos);
        if dist < hover_radius && dist < min_distance {
            min_distance = dist;
            closest_entity = Some(entity);
            tooltip_content = item_stats.name.clone();
        }
    }

    if closest_entity.is_some() && !tooltip_content.is_empty() {
        text.0 = tooltip_content;
        node.display = Display::Flex;
        // Position offset: 15px right, 15px down from cursor
        node.left = Val::Px(cursor_pos.x + 15.0);
        node.top = Val::Px(cursor_pos.y + 15.0);
    } else {
        node.display = Display::None;
    }
}

#[derive(Component)]
pub struct ContextMenuRoot;

#[derive(Component)]
pub struct ContextMenuButton {
    pub action: UiAction,
    pub target: Entity,
}

pub fn context_menu_system(
    mut commands: Commands,
    mouse_button_input: Res<ButtonInput<MouseButton>>,
    keyboard_input: Res<ButtonInput<KeyCode>>,
    window_query: Query<&Window, With<bevy::window::PrimaryWindow>>,
    camera_query: Query<(&Camera, &GlobalTransform), With<crate::camera::MainCamera>>,
    yukkuri_query: Query<(Entity, &Transform, &YukkuriStats), Without<crate::ai::Dead>>,
    poop_query: Query<(Entity, &Transform), With<crate::simulation::needs::Poop>>,
    menu_query: Query<Entity, With<ContextMenuRoot>>,
    mut message_writer: MessageWriter<PlaySoundEvent>,
) {
    let mut should_close = false;

    // Close on escape
    if keyboard_input.just_pressed(KeyCode::Escape) {
        should_close = true;
    }

    if mouse_button_input.just_pressed(MouseButton::Left) {
        // Menu closes on left-click (buttons will trigger their interaction before this runs/completes)
        should_close = true;
    }

    if should_close {
        for ent in &menu_query {
            commands.entity(ent).despawn();
        }
    }

    if mouse_button_input.just_pressed(MouseButton::Right) {
        // Despawn existing menu
        for ent in &menu_query {
            commands.entity(ent).despawn();
        }

        let Some(window) = window_query.iter().next() else { return; };
        let Some(cursor_pos) = window.cursor_position() else { return; };
        
        let camera_node = camera_query.iter().next();
        let world_pos = if let Some((cam, cam_trans)) = camera_node {
            cam.viewport_to_world_2d(cam_trans, cursor_pos).unwrap_or(Vec2::ZERO)
        } else {
            Vec2::ZERO
        };

        let click_radius = 40.0;
        let mut target_yukkuri = None;
        let mut target_poop = None;

        // Check Yukkuri
        let mut min_dist = click_radius;
        for (entity, transform, _) in &yukkuri_query {
            let dist = transform.translation.truncate().distance(world_pos);
            if dist < min_dist {
                min_dist = dist;
                target_yukkuri = Some(entity);
            }
        }

        // Check Poop if no Yukkuri
        if target_yukkuri.is_none() {
            let mut min_dist = click_radius;
            for (entity, transform) in &poop_query {
                let dist = transform.translation.truncate().distance(world_pos);
                if dist < min_dist {
                    min_dist = dist;
                    target_poop = Some(entity);
                }
            }
        }

        if let Some(target) = target_yukkuri {
            message_writer.write(PlaySoundEvent { name: "click".to_string() });
            spawn_context_menu(&mut commands, cursor_pos, target, vec![
                ("Inspect", UiAction::InspectEntity),
                ("Pick up", UiAction::PickUpEntity),
                ("Feed", UiAction::FeedEntity),
                ("Pat", UiAction::PatEntity),
                ("Slap", UiAction::SlapEntity),
                ("Delete", UiAction::DeleteEntity),
            ]);
        } else if let Some(target) = target_poop {
            message_writer.write(PlaySoundEvent { name: "click".to_string() });
            spawn_context_menu(&mut commands, cursor_pos, target, vec![
                ("Clean Poop", UiAction::SelectCleanTool),
            ]);
        }
    }
}

fn spawn_context_menu(
    commands: &mut Commands,
    screen_pos: Vec2,
    target_entity: Entity,
    options: Vec<(&str, UiAction)>,
) {
    commands
        .spawn((
            ContextMenuRoot,
            Node {
                position_type: PositionType::Absolute,
                left: Val::Px(screen_pos.x),
                top: Val::Px(screen_pos.y),
                flex_direction: FlexDirection::Column,
                row_gap: Val::Px(4.0),
                padding: UiRect::all(Val::Px(4.0)),
                border_radius: BorderRadius::all(Val::Px(6.0)),
                border: UiRect::all(Val::Px(1.0)),
                ..default()
            },
            GlobalZIndex(100),
            BackgroundColor(Color::srgba(0.08, 0.08, 0.1, 0.95)),
            BorderColor::all(Color::srgba(0.4, 0.4, 0.45, 0.5)),
        ))
        .with_children(|parent| {
            for (label, action) in options {
                parent.spawn((
                    Button,
                    Node {
                        padding: UiRect::new(Val::Px(12.0), Val::Px(12.0), Val::Px(6.0), Val::Px(6.0)),
                        justify_content: JustifyContent::Center,
                        align_items: AlignItems::Center,
                        border_radius: BorderRadius::all(Val::Px(4.0)),
                        ..default()
                    },
                    BackgroundColor(Color::srgba(0.18, 0.18, 0.22, 0.9)),
                    ContextMenuButton { action, target: target_entity },
                ))
                .with_children(|btn| {
                    btn.spawn((
                        Text::new(label),
                        TextFont { font_size: FontSize::Px(11.0), ..default() },
                        TextColor(Color::srgb(0.9, 0.9, 0.95)),
                    ));
                });
            }
        });
}

pub fn context_menu_button_interaction_system(
    mut interaction_query: Query<
        (&Interaction, &mut BackgroundColor, &ContextMenuButton),
        (Changed<Interaction>, With<Button>),
    >,
    mut commands: Commands,
    mut message_writer: MessageWriter<PlaySoundEvent>,
    mut sell_writer: MessageWriter<crate::simulation::player_actions::SellEntityRequest>,
    mut train_writer: MessageWriter<crate::simulation::player_actions::TrainEntityRequest>,
    mut punish_writer: MessageWriter<crate::simulation::player_actions::PunishEntityRequest>,
    menu_query: Query<Entity, With<ContextMenuRoot>>,
) {
    for (interaction, mut bg_color, btn) in &mut interaction_query {
        match *interaction {
            Interaction::Pressed => {
                *bg_color = BackgroundColor(BUTTON_PRESSED_COLOR);
                message_writer.write(PlaySoundEvent { name: "click".to_string() });

                match &btn.action {
                    UiAction::SellEntity => {
                        sell_writer.write(crate::simulation::player_actions::SellEntityRequest { entity_id: btn.target });
                    }
                    UiAction::TrainEntity => {
                        train_writer.write(crate::simulation::player_actions::TrainEntityRequest { entity_id: btn.target });
                    }
                    UiAction::PunishEntity => {
                        punish_writer.write(crate::simulation::player_actions::PunishEntityRequest { entity_id: btn.target });
                    }
                    UiAction::SelectCleanTool => {
                        commands.entity(btn.target).despawn();
                    }
                    UiAction::InspectEntity => {
                        // Implement select logic (could be done via event or directly manipulating CameraController)
                    }
                    UiAction::PickUpEntity => {
                        // Logic implemented in drag state
                    }
                    UiAction::FeedEntity => {
                        // Add food need logic via event or component query
                    }
                    UiAction::PatEntity => {
                        // Add happiness logic via event or component query
                    }
                    UiAction::SlapEntity => {
                        punish_writer.write(crate::simulation::player_actions::PunishEntityRequest { entity_id: btn.target });
                    }
                    UiAction::DeleteEntity => {
                        commands.entity(btn.target).despawn();
                    }
                    _ => {}
                }

                // Despawn the menu
                for ent in &menu_query {
                    commands.entity(ent).despawn();
                }
            }
            Interaction::Hovered => {
                *bg_color = BackgroundColor(BUTTON_HOVER_COLOR);
            }
            Interaction::None => {
                *bg_color = BackgroundColor(Color::srgba(0.18, 0.18, 0.22, 0.9));
            }
        }
    }
}

pub fn ui_scroll_system(
    mut mouse_wheel_reader: MessageReader<bevy::input::mouse::MouseWheel>,
    mut scroll_query: Query<(&Interaction, &mut ScrollPosition)>,
    children_query: Query<&bevy::prelude::ChildOf>,
    interaction_query: Query<(Entity, &Interaction)>,
) {
    let mut any_scroll = false;
    let mut scroll_delta = 0.0;
    for event in mouse_wheel_reader.read() {
        let mut delta = Vec2::new(event.x, event.y);
        if event.unit == bevy::input::mouse::MouseScrollUnit::Line {
            delta *= 21.0;
        }
        scroll_delta -= delta.y;
        any_scroll = true;
    }
    
    if !any_scroll {
        return;
    }
    
    // 1. Scroll directly hovered scroll containers
    for (interaction, mut scroll_pos) in &mut scroll_query {
        if *interaction == Interaction::Hovered {
            scroll_pos.y += scroll_delta;
        }
    }
    
    // 2. Scroll containers when hovering over their children
    for (entity, interaction) in &interaction_query {
        if *interaction == Interaction::Hovered {
            let mut curr = entity;
            while let Ok(child_of) = children_query.get(curr) {
                let parent_ent = child_of.parent();
                if let Ok((_, mut scroll_pos)) = scroll_query.get_mut(parent_ent) {
                    scroll_pos.y += scroll_delta;
                    break;
                }
                curr = parent_ent;
            }
        }
    }
}
