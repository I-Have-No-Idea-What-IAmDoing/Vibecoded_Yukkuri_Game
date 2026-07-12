use bevy::prelude::*;
use avian2d::prelude::*;
use crate::audio::PlaySoundEvent;
use crate::render::{TextureAtlasRegistry, YukkuriTypeRegistry};
use crate::ai::{WorldSettings, Needs, EmotionalState, YukkuriStats};
use crate::camera::CameraController;
use super::YukkuriDragState;

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
    ToggleShop,
    SelectShopTab(ShopTab),
    BuyItem { item_id: String, cost: i32 },
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

const BUTTON_NORMAL_COLOR: Color = Color::srgba(0.18, 0.18, 0.22, 0.9);
const BUTTON_HOVER_COLOR: Color = Color::srgba(0.25, 0.25, 0.30, 1.0);
const BUTTON_PRESSED_COLOR: Color = Color::srgba(0.35, 0.35, 0.45, 1.0);

// ---------------------------------------------------------------------------
// Setup System
// ---------------------------------------------------------------------------

pub fn setup_hud_system(mut commands: Commands) {
    // Root HUD panel — anchored to the bottom of the screen.
    // Glassmorphic styling.
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
            // Left Container: Spawn and sound buttons row
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

pub fn hud_interaction_system(
    mut interaction_query: Query<
        (&Interaction, &mut BackgroundColor, &YukkuriUiButton),
        (Changed<Interaction>, With<Button>),
    >,
    mut message_writer: MessageWriter<PlaySoundEvent>,
    mut commands: Commands,
    asset_server: Res<AssetServer>,
    atlas_registry: Res<TextureAtlasRegistry>,
    type_registry: Res<YukkuriTypeRegistry>,
    world_settings: Res<WorldSettings>,
    camera_controller_query: Query<&CameraController>,
    mut sell_writer: MessageWriter<crate::simulation::player_actions::SellEntityRequest>,
    mut train_writer: MessageWriter<crate::simulation::player_actions::TrainEntityRequest>,
    mut punish_writer: MessageWriter<crate::simulation::player_actions::PunishEntityRequest>,
    mut active_tab: ResMut<ActiveShopTab>,
    mut placement_state: ResMut<super::placement::PlacementState>,
    economy: Res<crate::ai::persistence::Economy>,
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
                                world_settings.width / 2.0,
                                world_settings.height / 2.0,
                            );
                            crate::prefabs::spawn_yukkuri_prefab(
                                &mut commands,
                                &prefab,
                                center,
                                &asset_server,
                                &atlas_registry,
                                &type_registry,
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
                        active_tab.open = !active_tab.open;
                    }
                    UiAction::SelectShopTab(tab) => {
                        active_tab.tab = *tab;
                    }
                    UiAction::BuyItem { item_id, cost } => {
                        if economy.money >= *cost {
                            placement_state.active = true;
                            placement_state.current_item_id = item_id.clone();
                            placement_state.cost = *cost;
                            placement_state.ghost_entity = None;
                        } else {
                            message_writer.write(PlaySoundEvent { name: "cancel".to_string() });
                        }
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
pub fn hud_update_system(
    camera_query: Query<&CameraController>,
    yukkuri_query: Query<(&Needs, &EmotionalState, &YukkuriStats, Option<&crate::simulation::inventory::InventoryComponent>)>,
    item_query: Query<&crate::simulation::inventory::ItemStats>,
    mut card_query: Query<&mut Node, With<HudSelectionCard>>,
    mut name_query: Query<&mut Text, (With<HudNameText>, Without<HudBreedText>, Without<HudStageText>, Without<HudInventoryText>)>,
    mut breed_query: Query<&mut Text, (With<HudBreedText>, Without<HudNameText>, Without<HudStageText>, Without<HudInventoryText>)>,
    mut stage_query: Query<&mut Text, (With<HudStageText>, Without<HudNameText>, Without<HudBreedText>, Without<HudInventoryText>)>,
    mut inventory_text_query: Query<&mut Text, (With<HudInventoryText>, Without<HudNameText>, Without<HudBreedText>, Without<HudStageText>)>,
    mut fills_query: Query<(&mut Node, &HudBarFill), (Without<HudSelectionCard>, Without<HudYukkuriOnlyAction>)>,
    mut yukkuri_actions_query: Query<&mut Node, (With<HudYukkuriOnlyAction>, Without<HudSelectionCard>, Without<HudBarFill>)>,
) {
    let Some(controller) = camera_query.iter().next() else { return; };
    let Ok(mut card_node) = card_query.single_mut() else { return; };

    if let Some(selected) = controller.selected_entity {
        if let Ok((needs, emotional, stats, maybe_inventory)) = yukkuri_query.get(selected) {
            card_node.display = Display::Flex;

            // Identity Text Updates
            if let Ok(mut text) = name_query.single_mut() {
                text.0 = format!("Name: {}", stats.name);
            }
            if let Ok(mut text) = breed_query.single_mut() {
                text.0 = format!("Breed: {}", stats.type_id);
            }
            if let Ok(mut text) = stage_query.single_mut() {
                text.0 = format!("Stage: {}", stats.growth_stage);
            }

            // Inventory Text Update
            if let Ok(mut text) = inventory_text_query.single_mut() {
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
            for mut node in &mut yukkuri_actions_query {
                node.display = Display::Flex;
            }

            // Stats Bars Fills Updates
            for (mut node, fill) in fills_query.iter_mut() {
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
            if let Ok(mut text) = name_query.single_mut() {
                text.0 = format!("Name: {}", item_stats.name);
            }
            if let Ok(mut text) = breed_query.single_mut() {
                text.0 = format!("Type: {}", item_stats.type_id);
            }
            if let Ok(mut text) = stage_query.single_mut() {
                text.0 = format!("Value: ${}", item_stats.value as i32);
            }

            // Inventory Text Update
            if let Ok(mut text) = inventory_text_query.single_mut() {
                text.0 = "N/A".to_string();
            }

            // Hide Train & Punish buttons
            for mut node in &mut yukkuri_actions_query {
                node.display = Display::None;
            }

            // Reset Fills to 0
            for (mut node, _fill) in fills_query.iter_mut() {
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
    mut commands: Commands,
    mouse_button_input: Res<ButtonInput<MouseButton>>,
    window_query: Query<&Window>,
    camera_query: Query<(&Camera, &GlobalTransform)>,
    mut drag_state: ResMut<YukkuriDragState>,
    mut yukkuri_queries: ParamSet<(
        Query<(Entity, &Transform), With<YukkuriStats>>,
        Query<
            (&mut Transform, &mut LinearVelocity, &mut AngularVelocity),
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

    if mouse_button_input.just_pressed(MouseButton::Left) {
        let mut closest: Option<(Entity, f32)> = None;
        for (entity, transform) in yukkuri_queries.p0().iter() {
            let dist = (transform.translation.truncate() - world_pos).length();
            if dist < 40.0 {
                match closest {
                    Some((_, d)) if d <= dist => {}
                    _ => closest = Some((entity, dist)),
                }
            }
        }

        if let Some((entity, _)) = closest {
            drag_state.dragged_entity = Some(entity);
            commands.entity(entity).insert(RigidBody::Kinematic);
            if let Ok((_, mut lin_vel, mut ang_vel)) = yukkuri_queries.p1().get_mut(entity) {
                lin_vel.0 = Vec2::ZERO;
                ang_vel.0 = 0.0;
            }
        }
    } else if mouse_button_input.pressed(MouseButton::Left) {
        if let Some(entity) = drag_state.dragged_entity {
            if let Ok((mut transform, mut lin_vel, mut ang_vel)) =
                yukkuri_queries.p1().get_mut(entity)
            {
                transform.translation.x = world_pos.x;
                transform.translation.y = world_pos.y;
                lin_vel.0 = Vec2::ZERO;
                ang_vel.0 = 0.0;
            }
        }
    } else if mouse_button_input.just_released(MouseButton::Left) {
        if let Some(entity) = drag_state.dragged_entity.take() {
            commands.entity(entity).insert(RigidBody::Dynamic);
            if let Ok((_, mut lin_vel, mut ang_vel)) = yukkuri_queries.p1().get_mut(entity) {
                lin_vel.0 = Vec2::ZERO;
                ang_vel.0 = 0.0;
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
