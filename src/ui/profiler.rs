use bevy::prelude::*;
use std::time::Instant;
use super::{SystemTimings, UiToggleState};

// ---------------------------------------------------------------------------
// Components & Resources
// ---------------------------------------------------------------------------

#[derive(Component)]
pub struct ProfilerRootNode;

#[derive(Component)]
pub struct ProfilerBudgetText;

#[derive(Component)]
pub struct ProfilerBudgetBarFill;

#[derive(Component)]
pub struct ProfilerTimingsText;

#[derive(Resource)]
pub struct FrameTimeTracker {
    pub last_instant: Instant,
}

impl Default for FrameTimeTracker {
    fn default() -> Self {
        Self {
            last_instant: Instant::now(),
        }
    }
}

// ---------------------------------------------------------------------------
// Setup System
// ---------------------------------------------------------------------------

pub fn setup_profiler_system(mut commands: Commands) {
    commands.insert_resource(FrameTimeTracker::default());

    // Top-right panel: simple, solid dark theme
    commands
        .spawn((
            ProfilerRootNode,
            Node {
                position_type: PositionType::Absolute,
                right: Val::Px(10.0),
                top: Val::Px(280.0), // Below the console top area if extended
                width: Val::Px(280.0),
                height: Val::Px(180.0),
                display: Display::None, // Hidden by default
                flex_direction: FlexDirection::Column,
                padding: UiRect::all(Val::Px(10.0)),
                ..default()
            },
            BackgroundColor(Color::srgb(0.08, 0.08, 0.1)),
            BorderColor::all(Color::srgb(0.2, 0.2, 0.22)),
        ))
        .with_children(|root| {
            // Title
            root.spawn(Node { margin: UiRect::bottom(Val::Px(6.0)), ..default() })
            .with_children(|t| {
                t.spawn((
                    Text::new("System Performance Profiler (F4)"),
                    TextFont {
                        font_size: FontSize::Px(13.0),
                        ..default()
                    },
                    TextColor(Color::srgb(0.9, 0.9, 0.95)),
                ));
            });

            // Budget text
            root.spawn((
                ProfilerBudgetText,
                Text::new("Budget: 0.00 ms / 16.67 ms"),
                TextFont { font_size: FontSize::Px(11.0), ..default() },
                TextColor(Color::srgb(0.65, 0.65, 0.7)),
            ));

            // Budget bar container
            root.spawn(Node {
                width: Val::Percent(100.0),
                height: Val::Px(12.0),
                margin: UiRect::vertical(Val::Px(8.0)),
                ..default()
            })
            .with_children(|bar_bg| {
                bar_bg.spawn((
                    Node {
                        width: Val::Percent(100.0),
                        height: Val::Percent(100.0),
                        ..default()
                    },
                    BackgroundColor(Color::srgb(0.15, 0.15, 0.17)),
                ))
                .with_children(|inner| {
                    inner.spawn((
                        ProfilerBudgetBarFill,
                        Node {
                            width: Val::Percent(0.0),
                            height: Val::Percent(100.0),
                            ..default()
                        },
                        BackgroundColor(Color::srgb(0.2, 0.8, 0.2)),
                    ));
                });
            });

            // Timings breakdown list
            root.spawn((
                ProfilerTimingsText,
                Text::new(
                    "  AI Update: 0.00 ms\n  Physics: 0.00 ms\n  Render: 0.00 ms\n  UI/Layout: 0.00 ms\n  FPS: 0.0"
                ),
                TextFont { font_size: FontSize::Px(11.0), ..default() },
                TextColor(Color::srgb(0.8, 0.8, 0.85)),
            ));
        });
}

// ---------------------------------------------------------------------------
// Update System
// ---------------------------------------------------------------------------

pub fn profiler_update_system(
    mut tracker: ResMut<FrameTimeTracker>,
    mut timings: ResMut<SystemTimings>,
    toggle_state: Res<UiToggleState>,
    mut root_query: Query<&mut Node, With<ProfilerRootNode>>,
    mut budget_text_query: Query<&mut Text, (With<ProfilerBudgetText>, Without<ProfilerTimingsText>)>,
    mut timings_text_query: Query<&mut Text, (With<ProfilerTimingsText>, Without<ProfilerBudgetText>)>,
    mut bar_query: Query<(&mut Node, &mut BackgroundColor), (With<ProfilerBudgetBarFill>, Without<ProfilerRootNode>)>,
) {
    let Ok(mut root_node) = root_query.single_mut() else { return; };

    // Toggle Visibility
    if toggle_state.profiler_open {
        root_node.display = Display::Flex;
    } else {
        root_node.display = Display::None;
        return;
    }

    // Calculate actual elapsed frame time
    let now = Instant::now();
    let frame_time_ms = now.duration_since(tracker.last_instant).as_secs_f64() * 1000.0;
    tracker.last_instant = now;

    // Distribute time dynamically to simulate timings
    // Realistically, Bevy does rendering asynchronously so we estimate rendering,
    // and scale AI, physics, and UI based on frame rate.
    timings.budget_ms = 16.67; // 60 FPS target
    let active_frame_ms = frame_time_ms.min(100.0); // Clamp outliers

    timings.ui_time_ms = active_frame_ms * 0.08; // 8% of frame
    timings.ai_time_ms = active_frame_ms * 0.15; // 15% of frame
    timings.physics_time_ms = active_frame_ms * 0.32; // 32% of frame
    timings.render_time_ms = active_frame_ms * 0.45; // 45% of frame (heaviest)

    let total_time_ms = timings.ui_time_ms + timings.ai_time_ms + timings.physics_time_ms + timings.render_time_ms;
    let fps = 1000.0 / frame_time_ms.max(1.0);

    // Update Budget Text
    if let Ok(mut text) = budget_text_query.single_mut() {
        text.0 = format!("Budget: {:.2} ms / {:.2} ms", total_time_ms, timings.budget_ms);
    }

    // Update Budget Bar
    if let Ok((mut node, mut bg_color)) = bar_query.single_mut() {
        let percent = (total_time_ms / timings.budget_ms * 100.0).clamp(0.0, 100.0) as f32;
        node.width = Val::Percent(percent);

        // Turn red if we overflow the budget
        if total_time_ms > timings.budget_ms {
            bg_color.0 = Color::srgb(0.85, 0.25, 0.25);
        } else {
            bg_color.0 = Color::srgb(0.25, 0.75, 0.25);
        }
    }

    // Update timings text
    if let Ok(mut timings_text) = timings_text_query.single_mut() {
        timings_text.0 = format!(
            "  AI Update: {:.2} ms\n  Physics: {:.2} ms\n  Render: {:.2} ms\n  UI/Layout: {:.2} ms\n  FPS: {:.1}",
            timings.ai_time_ms,
            timings.physics_time_ms,
            timings.render_time_ms,
            timings.ui_time_ms,
            fps
        );
    }
}
