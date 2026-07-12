use bevy::prelude::*;
use bevy::input::keyboard::{Key, KeyboardInput};
use crate::ai::{Needs, StableId, YukkuriStats};
use crate::camera::CameraController;
use super::{ActiveFocus, UiToggleState};

// ---------------------------------------------------------------------------
// Components & Resources
// ---------------------------------------------------------------------------

#[derive(Resource, Default, Debug, Clone)]
pub struct InspectorUiState {
    pub active_filter: String, // "", "yukkuri", "physics"
    pub search_buffer: String,
    pub selected_entity: Option<Entity>,
    // For reactive rebuilds
    pub needs_rebuild: bool,
    pub last_console_open: bool,
}

#[derive(Resource, Default, Debug, Clone)]
pub struct ActiveFieldInputBuffer {
    pub content: String,
}

#[derive(Component)]
pub struct InspectorRootNode;

#[derive(Component)]
pub struct InspectorContentRoot;

#[derive(Component)]
pub struct InspectorSearchText;

#[derive(Component)]
pub enum InspectorButton {
    FilterAll,
    FilterYukkuri,
    FilterPhysics,
    SelectEntity(Entity),
    BackToList,
    RefocusCamera,
    DestroyEntity,
    FieldInput(Entity, String, String), // (Entity, ComponentName, FieldName)
}

// ---------------------------------------------------------------------------
// Setup UI
// ---------------------------------------------------------------------------

pub fn setup_inspector_system(mut commands: Commands) {
    commands.insert_resource(InspectorUiState {
        active_filter: "".to_string(),
        search_buffer: "".to_string(),
        selected_entity: None,
        needs_rebuild: true,
        last_console_open: false,
    });
    commands.insert_resource(ActiveFieldInputBuffer::default());

    // Left sidebar: simple solid dark theme to distinguish from gameplay UI.
    commands
        .spawn((
            InspectorRootNode,
            Node {
                position_type: PositionType::Absolute,
                left: Val::Px(0.0),
                top: Val::Px(260.0), // Below the console (sits at 0..260)
                width: Val::Px(320.0),
                height: Val::Percent(60.0),
                display: Display::None, // Hidden by default
                flex_direction: FlexDirection::Column,
                padding: UiRect::all(Val::Px(10.0)),
                ..default()
            },
            BackgroundColor(Color::srgb(0.1, 0.1, 0.12)),
            BorderColor::all(Color::srgb(0.22, 0.22, 0.25)),
        ))
        .with_children(|root| {
            // Header
            root.spawn(Node {
                margin: UiRect::bottom(Val::Px(10.0)),
                ..default()
            })
            .with_children(|header| {
                header.spawn((
                    Text::new("ECS Entity Inspector (F3)"),
                    TextFont {
                        font_size: FontSize::Px(15.0),
                        ..default()
                    },
                    TextColor(Color::srgb(0.9, 0.9, 0.9)),
                ));
            });

            // Dynamic content root
            root.spawn((
                InspectorContentRoot,
                Node {
                    flex_grow: 1.0,
                    flex_direction: FlexDirection::Column,
                    ..default()
                },
            ));
        });
}

// ---------------------------------------------------------------------------
// Rebuilding UI Elements
// ---------------------------------------------------------------------------

fn rebuild_inspector_ui(
    commands: &mut Commands,
    content_root: Entity,
    ui_state: &InspectorUiState,
    focus: &ActiveFocus,
    input_buffer: &ActiveFieldInputBuffer,
    entity_query: &Query<(Entity, &StableId, Option<&YukkuriStats>, Option<&Needs>)>,
    selected_camera_entity: Option<Entity>,
) {
    commands.entity(content_root).despawn_related::<Children>();

    let target_entity = ui_state.selected_entity.or(selected_camera_entity);

    if let Some(entity) = target_entity {
        // --- COMPONENT DETAILED VIEW ---
        commands.entity(content_root).with_children(|parent| {
            // Back Button
            parent.spawn((
                Button,
                Node {
                    padding: UiRect::axes(Val::Px(8.0), Val::Px(4.0)),
                    margin: UiRect::bottom(Val::Px(8.0)),
                    align_self: AlignSelf::FlexStart,
                    ..default()
                },
                BackgroundColor(Color::srgb(0.2, 0.2, 0.22)),
                InspectorButton::BackToList,
            ))
            .with_children(|btn| {
                btn.spawn((Text::new("< Back to List"), TextFont { font_size: FontSize::Px(12.0), ..default() }));
            });

            // Entity Info Header
            parent.spawn(Node { margin: UiRect::bottom(Val::Px(8.0)), ..default() })
            .with_children(|h| {
                h.spawn((
                    Text::new(format!("Inspecting: Entity {:?}", entity)),
                    TextFont { font_size: FontSize::Px(13.0), ..default() },
                    TextColor(Color::srgb(0.7, 0.9, 0.7)),
                ));
            });

            // Action Row
            parent.spawn(Node {
                flex_direction: FlexDirection::Row,
                column_gap: Val::Px(8.0),
                margin: UiRect::bottom(Val::Px(12.0)),
                ..default()
            })
            .with_children(|row| {
                row.spawn((
                    Button,
                    Node { padding: UiRect::axes(Val::Px(8.0), Val::Px(4.0)), ..default() },
                    BackgroundColor(Color::srgb(0.15, 0.25, 0.15)),
                    InspectorButton::RefocusCamera,
                ))
                .with_children(|btn| {
                    btn.spawn((Text::new("Track Camera (F)"), TextFont { font_size: FontSize::Px(11.0), ..default() }));
                });

                row.spawn((
                    Button,
                    Node { padding: UiRect::axes(Val::Px(8.0), Val::Px(4.0)), ..default() },
                    BackgroundColor(Color::srgb(0.3, 0.1, 0.1)),
                    InspectorButton::DestroyEntity,
                ))
                .with_children(|btn| {
                    btn.spawn((Text::new("Destroy"), TextFont { font_size: FontSize::Px(11.0), ..default() }));
                });
            });

            // Components List
            if let Ok((_ent, _stable, opt_stats, opt_needs)) = entity_query.get(entity) {
                // YukkuriStats Component
                if let Some(stats) = opt_stats {
                    spawn_component_header(parent, "YukkuriStats");
                    spawn_editable_field(parent, entity, "YukkuriStats", "name", &stats.name, focus, input_buffer);
                    spawn_read_only_field(parent, "type_id", &stats.type_id);
                    spawn_editable_field(parent, entity, "YukkuriStats", "growth_stage", &stats.growth_stage, focus, input_buffer);
                }

                // Needs Component
                if let Some(needs) = opt_needs {
                    spawn_component_header(parent, "Needs");
                    spawn_editable_field(parent, entity, "Needs", "health", &needs.health.to_string(), focus, input_buffer);
                    spawn_editable_field(parent, entity, "Needs", "hunger", &needs.hunger.to_string(), focus, input_buffer);
                    spawn_editable_field(parent, entity, "Needs", "energy", &needs.energy.to_string(), focus, input_buffer);
                    spawn_editable_field(parent, entity, "Needs", "cleanliness", &needs.cleanliness.to_string(), focus, input_buffer);
                    spawn_editable_field(parent, entity, "Needs", "bladder", &needs.bladder.to_string(), focus, input_buffer);
                    spawn_editable_field(parent, entity, "Needs", "social", &needs.social.to_string(), focus, input_buffer);
                    spawn_editable_field(parent, entity, "Needs", "easiness", &needs.easiness.to_string(), focus, input_buffer);
                }
            } else {
                parent.spawn((
                    Text::new("Entity details missing/despawned"),
                    TextFont { font_size: FontSize::Px(12.0), ..default() },
                    TextColor(Color::srgb(0.7, 0.3, 0.3)),
                ));
            }
        });
    } else {
        // --- SEARCHABLE ENTITIES LIST ---
        commands.entity(content_root).with_children(|parent| {
            // Filters Row
            parent.spawn(Node {
                flex_direction: FlexDirection::Row,
                column_gap: Val::Px(6.0),
                margin: UiRect::bottom(Val::Px(8.0)),
                ..default()
            })
            .with_children(|row| {
                spawn_filter_pill(row, "All", ui_state.active_filter.is_empty(), InspectorButton::FilterAll);
                spawn_filter_pill(row, "Yukkuri", ui_state.active_filter == "yukkuri", InspectorButton::FilterYukkuri);
                spawn_filter_pill(row, "Physics", ui_state.active_filter == "physics", InspectorButton::FilterPhysics);
            });

            // Search Bar
            parent.spawn((
                Button,
                Node {
                    height: Val::Px(24.0),
                    margin: UiRect::bottom(Val::Px(8.0)),
                    padding: UiRect::horizontal(Val::Px(6.0)),
                    align_items: AlignItems::Center,
                    ..default()
                },
                BackgroundColor(if *focus == ActiveFocus::InspectorSearch { Color::srgb(0.05, 0.05, 0.06) } else { Color::srgb(0.15, 0.15, 0.17) }),
            ))
            .with_children(|search_btn| {
                let prompt = if ui_state.search_buffer.is_empty() {
                    "Search components..."
                } else {
                    &ui_state.search_buffer
                };
                search_btn.spawn((
                    InspectorSearchText,
                    Text::new(prompt),
                    TextFont { font_size: FontSize::Px(12.0), ..default() },
                    TextColor(if ui_state.search_buffer.is_empty() { Color::srgb(0.5, 0.5, 0.5) } else { Color::srgb(0.9, 0.9, 0.9) }),
                ));
            });

            // Scrollable list container
            parent.spawn(Node {
                flex_direction: FlexDirection::Column,
                flex_grow: 1.0,
                overflow: Overflow::clip(),
                row_gap: Val::Px(4.0),
                ..default()
            })
            .with_children(|list| {
                for (entity, stable, opt_stats, opt_needs) in entity_query.iter() {
                    let id = (stable.0 & 0xFFFFFFFF) as u32;
                    let ent_name = opt_stats.map(|s| s.name.as_str()).unwrap_or("Non-Yukkuri");
                    
                    // Filter match
                    if ui_state.active_filter == "yukkuri" && opt_stats.is_none() {
                        continue;
                    }
                    if ui_state.active_filter == "physics" && opt_needs.is_none() {
                        // Assume physics entities are those with stats/needs in our mock, or extend later
                        continue;
                    }

                    // Search match
                    if !ui_state.search_buffer.is_empty() {
                        let query = ui_state.search_buffer.to_lowercase();
                        let matches = ent_name.to_lowercase().contains(&query) || id.to_string().contains(&query);
                        if !matches {
                            continue;
                        }
                    }

                    // Row Button
                    list.spawn((
                        Button,
                        Node {
                            padding: UiRect::all(Val::Px(6.0)),
                            justify_content: JustifyContent::FlexStart,
                            ..default()
                        },
                        BackgroundColor(Color::srgb(0.18, 0.18, 0.2)),
                        InspectorButton::SelectEntity(entity),
                    ))
                    .with_children(|row| {
                        row.spawn((
                            Text::new(format!("[ID: {}] {}", id, ent_name)),
                            TextFont { font_size: FontSize::Px(12.0), ..default() },
                            TextColor(Color::srgb(0.9, 0.9, 0.9)),
                        ));
                    });
                }
            });
        });
    }
}

fn spawn_filter_pill(parent: &mut ChildSpawnerCommands, label: &str, active: bool, action: InspectorButton) {
    parent.spawn((
        Button,
        Node {
            padding: UiRect::axes(Val::Px(8.0), Val::Px(4.0)),
            ..default()
        },
        BackgroundColor(if active { Color::srgb(0.2, 0.35, 0.5) } else { Color::srgb(0.15, 0.15, 0.17) }),
        action,
    ))
    .with_children(|btn| {
        btn.spawn((Text::new(label), TextFont { font_size: FontSize::Px(10.0), ..default() }));
    });
}

fn spawn_component_header(parent: &mut ChildSpawnerCommands, name: &str) {
    parent.spawn(Node {
        margin: UiRect::top(Val::Px(10.0)),
        padding: UiRect::vertical(Val::Px(4.0)),
        ..default()
    })
    .with_children(|h| {
        h.spawn((
            Text::new(name),
            TextFont { font_size: FontSize::Px(12.0), ..default() },
            TextColor(Color::srgb(0.4, 0.7, 0.9)),
        ));
    });
}

fn spawn_read_only_field(parent: &mut ChildSpawnerCommands, name: &str, value: &str) {
    parent.spawn(Node {
        flex_direction: FlexDirection::Row,
        justify_content: JustifyContent::SpaceBetween,
        margin: UiRect::bottom(Val::Px(4.0)),
        ..default()
    })
    .with_children(|row| {
        row.spawn((Text::new(format!("{}:", name)), TextFont { font_size: FontSize::Px(11.0), ..default() }, TextColor(Color::srgb(0.6, 0.6, 0.6))));
        row.spawn((Text::new(value), TextFont { font_size: FontSize::Px(11.0), ..default() }, TextColor(Color::srgb(0.7, 0.7, 0.7))));
    });
}

fn spawn_editable_field(
    parent: &mut ChildSpawnerCommands,
    entity: Entity,
    component_name: &str,
    field_name: &str,
    value: &str,
    focus: &ActiveFocus,
    input_buffer: &ActiveFieldInputBuffer,
) {
    let is_focused = match focus {
        ActiveFocus::InspectorField(focused_ent, ref name) => {
            *focused_ent == entity && name == field_name
        }
        _ => false,
    };

    parent.spawn(Node {
        flex_direction: FlexDirection::Row,
        justify_content: JustifyContent::SpaceBetween,
        align_items: AlignItems::Center,
        margin: UiRect::bottom(Val::Px(4.0)),
        ..default()
    })
    .with_children(|row| {
        row.spawn((Text::new(format!("{}:", field_name)), TextFont { font_size: FontSize::Px(11.0), ..default() }, TextColor(Color::srgb(0.8, 0.8, 0.8))));
        
        let display_val = if is_focused { &input_buffer.content } else { value };

        row.spawn((
            Button,
            Node {
                width: Val::Px(120.0),
                height: Val::Px(20.0),
                padding: UiRect::horizontal(Val::Px(4.0)),
                justify_content: JustifyContent::FlexStart,
                align_items: AlignItems::Center,
                ..default()
            },
            BackgroundColor(if is_focused { Color::srgb(0.04, 0.04, 0.04) } else { Color::srgb(0.16, 0.16, 0.18) }),
            InspectorButton::FieldInput(entity, component_name.to_string(), field_name.to_string()),
        ))
        .with_children(|btn| {
            btn.spawn((
                Text::new(display_val),
                TextFont { font_size: FontSize::Px(11.0), ..default() },
                TextColor(Color::srgb(0.95, 0.95, 0.95)),
            ));
        });
    });
}

// ---------------------------------------------------------------------------
// Update Systems
// ---------------------------------------------------------------------------

pub fn inspector_update_system(
    mut commands: Commands,
    toggle_state: Res<UiToggleState>,
    mut ui_state: ResMut<InspectorUiState>,
    mut focus: ResMut<ActiveFocus>,
    mut input_buffer: ResMut<ActiveFieldInputBuffer>,
    mut camera_query: Query<&mut CameraController>,
    mut root_query: Query<&mut Node, With<InspectorRootNode>>,
    content_root_query: Query<Entity, With<InspectorContentRoot>>,
    buttons_query: Query<(&Interaction, &InspectorButton), (Changed<Interaction>, With<Button>)>,
    mut keyboard_evr: MessageReader<KeyboardInput>,
    mut queries: ParamSet<(
        Query<(Entity, &StableId, Option<&YukkuriStats>, Option<&Needs>)>,
        Query<(Entity, &mut Needs)>,
        Query<(Entity, &mut YukkuriStats)>,
    )>,
) {
    let Ok(mut root_node) = root_query.single_mut() else { return; };
    let Ok(content_root) = content_root_query.single() else { return; };

    // Toggle Visibility
    if toggle_state.inspector_open {
        root_node.display = Display::Flex;
    } else {
        root_node.display = Display::None;
        return;
    }

    let mut force_rebuild = ui_state.needs_rebuild;
    ui_state.needs_rebuild = false;

    // Detect camera controller selection change
    let selected_camera_entity = camera_query.iter().next().and_then(|c| c.selected_entity);
    if ui_state.selected_entity != selected_camera_entity {
        ui_state.selected_entity = selected_camera_entity;
        force_rebuild = true;
    }

    // Process Clicks / Button Interactions
    for (interaction, action) in buttons_query.iter() {
        if *interaction != Interaction::Pressed {
            continue;
        }

        match action {
            InspectorButton::FilterAll => {
                ui_state.active_filter = "".to_string();
                force_rebuild = true;
            }
            InspectorButton::FilterYukkuri => {
                ui_state.active_filter = "yukkuri".to_string();
                force_rebuild = true;
            }
            InspectorButton::FilterPhysics => {
                ui_state.active_filter = "physics".to_string();
                force_rebuild = true;
            }
            InspectorButton::SelectEntity(ent) => {
                ui_state.selected_entity = Some(*ent);
                if let Some(mut controller) = camera_query.iter_mut().next() {
                    controller.selected_entity = Some(*ent);
                }
                force_rebuild = true;
            }
            InspectorButton::BackToList => {
                ui_state.selected_entity = None;
                if let Some(mut controller) = camera_query.iter_mut().next() {
                    controller.selected_entity = None;
                    controller.tracked_entity = None;
                }
                force_rebuild = true;
                *focus = ActiveFocus::Game;
            }
            InspectorButton::RefocusCamera => {
                if let Some(ent) = ui_state.selected_entity {
                    if let Some(mut controller) = camera_query.iter_mut().next() {
                        controller.tracked_entity = Some(ent);
                    }
                }
            }
            InspectorButton::DestroyEntity => {
                if let Some(ent) = ui_state.selected_entity {
                    commands.entity(ent).despawn();
                    ui_state.selected_entity = None;
                    if let Some(mut controller) = camera_query.iter_mut().next() {
                        controller.selected_entity = None;
                        controller.tracked_entity = None;
                    }
                    force_rebuild = true;
                }
            }
            InspectorButton::FieldInput(ent, comp_name, field_name) => {
                *focus = ActiveFocus::InspectorField(*ent, field_name.clone());
                // Initialize input buffer with current value
                let mut current_val = "".to_string();
                match comp_name.as_str() {
                    "Needs" => {
                        if let Ok((_, needs)) = queries.p1().get(*ent) {
                            match field_name.as_str() {
                                "health" => current_val = needs.health.to_string(),
                                "hunger" => current_val = needs.hunger.to_string(),
                                "energy" => current_val = needs.energy.to_string(),
                                "bladder" => current_val = needs.bladder.to_string(),
                                "cleanliness" => current_val = needs.cleanliness.to_string(),
                                "social" => current_val = needs.social.to_string(),
                                "easiness" => current_val = needs.easiness.to_string(),
                                _ => {}
                            }
                        }
                    }
                    "YukkuriStats" => {
                        if let Ok((_, stats)) = queries.p2().get(*ent) {
                            match field_name.as_str() {
                                "name" => current_val = stats.name.clone(),
                                "growth_stage" => current_val = stats.growth_stage.clone(),
                                _ => {}
                            }
                        }
                    }
                    _ => {}
                }
                input_buffer.content = current_val;
                force_rebuild = true;
            }
        }
    }

    // Process Typing/Search inputs via KeyboardInput
    for event in keyboard_evr.read() {
        if !event.state.is_pressed() {
            continue;
        }

        // Search typing
        if *focus == ActiveFocus::InspectorSearch {
            match &event.logical_key {
                Key::Character(character) => {
                    ui_state.search_buffer.push_str(character.as_str());
                    force_rebuild = true;
                }
                Key::Space => {
                    ui_state.search_buffer.push(' ');
                    force_rebuild = true;
                }
                Key::Backspace => {
                    ui_state.search_buffer.pop();
                    force_rebuild = true;
                }
                Key::Enter => {
                    *focus = ActiveFocus::Game;
                    force_rebuild = true;
                }
                _ => {}
            }
        }

        // Field editing typing
        if let ActiveFocus::InspectorField(entity, ref field_name) = *focus {
            match &event.logical_key {
                Key::Character(character) => {
                    input_buffer.content.push_str(character.as_str());
                    force_rebuild = true;
                }
                Key::Space => {
                    input_buffer.content.push(' ');
                    force_rebuild = true;
                }
                Key::Backspace => {
                    input_buffer.content.pop();
                    force_rebuild = true;
                }
                Key::Enter => {
                    // Apply value to ECS component
                    let val_str = input_buffer.content.clone();
                    
                    {
                        let mut needs_q = queries.p1();
                        if let Ok((_, mut needs)) = needs_q.get_mut(entity) {
                            if let Ok(val) = val_str.parse::<f32>() {
                                match field_name.as_str() {
                                    "health" => needs.health = val,
                                    "hunger" => needs.hunger = val,
                                    "energy" => needs.energy = val,
                                    "bladder" => needs.bladder = val,
                                    "cleanliness" => needs.cleanliness = val,
                                    "social" => needs.social = val,
                                    "easiness" => needs.easiness = val,
                                    _ => {}
                                }
                            }
                        }
                    }
                    {
                        let mut stats_q = queries.p2();
                        if let Ok((_, mut stats)) = stats_q.get_mut(entity) {
                            match field_name.as_str() {
                                "name" => stats.name = val_str,
                                "growth_stage" => stats.growth_stage = val_str,
                                _ => {}
                            }
                        }
                    }

                      *focus = ActiveFocus::Game;
                      force_rebuild = true;
                  }
                  _ => {}
              }
          }
      }

    // Rebuild UI Layout if needed
    if force_rebuild {
        let entity_query = queries.p0();
        rebuild_inspector_ui(
            &mut commands,
            content_root,
            &ui_state,
            &focus,
            &input_buffer,
            &entity_query,
            selected_camera_entity,
        );
    }
}
