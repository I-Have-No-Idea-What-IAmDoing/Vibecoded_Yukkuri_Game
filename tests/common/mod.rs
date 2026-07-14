// INTEGRITY MANDATE:
// DO NOT CHEAT. All implementations must be genuine. Specifically:
// - DO NOT hardcode test results, expected outputs, or verification strings in source code.
// - DO NOT create dummy or facade implementations that produce correct-looking outputs without genuine logic.
// - DO NOT circumvent the intended task by delegating core work to external tools or pre-built solutions when the task requires building from scratch.
// - DO NOT fabricate verification outputs, logs, or attestation artifacts.
// - Every implementation must maintain real state and produce real behavior — not return hardcoded values.
// A Forensic Auditor will independently verify your work. Shortcut strategies WILL be detected and your work WILL be rejected.

use bevy::prelude::*;
use avian2d::prelude::*;
use vibecoded_yukkuri_game::{
    ai::AIPlugin,
    audio::YukkuriAudioPlugin,
    render::YukkuriRenderPlugin,
    ui::YukkuriUiPlugin,
};

/// Initializes a headless Bevy App with minimal plugins, assets, physics, AI, rendering,
/// audio, and UI plugins, and registers all mock resources required to pass system parameter validation.
pub fn create_test_app() -> App {
    let mut app = App::new();
    app.add_plugins(MinimalPlugins);
    app.add_plugins(bevy::asset::AssetPlugin::default());
    app.add_plugins(bevy::transform::TransformPlugin);
    app.add_plugins(bevy::input::InputPlugin);
    app.add_plugins(bevy::gizmos::GizmoPlugin);
    app.init_asset::<Mesh>();
    app.init_asset::<bevy::render::mesh::skinning::SkinnedMeshInverseBindposes>();
    app.init_asset::<bevy::gizmos::GizmoAsset>();
    app.add_plugins(PhysicsPlugins::default());
    app.add_plugins(AIPlugin);
    app.add_plugins(vibecoded_yukkuri_game::simulation::SimulationPlugin);
    app.add_plugins(YukkuriRenderPlugin);
    app.add_plugins(YukkuriAudioPlugin);
    app.add_plugins(YukkuriUiPlugin);
    app.add_plugins(bevy::state::app::StatesPlugin);
    app.init_state::<vibecoded_yukkuri_game::GameState>();

    // Initialize mock resources for headless testing to satisfy system validation
    app.init_resource::<bevy::gizmos::config::GizmoConfigStore>();
    app.init_resource::<avian2d::collider_tree::ColliderTreeDiagnostics>();
    app.init_resource::<avian2d::spatial_query::SpatialQueryDiagnostics>();
    app.init_resource::<avian2d::dynamics::solver::SolverDiagnostics>();
    app.init_resource::<avian2d::collision::CollisionDiagnostics>();

    app
}

/// Spawns a mock 2D Camera with a standard 800x600 viewport, target info, and 2D orthographic
/// projection so that screen-to-world coordinate mapping works correctly in headless tests.
pub fn spawn_test_camera(app: &mut App) -> Entity {
    let mut camera = Camera {
        viewport: Some(bevy::camera::Viewport {
            physical_position: UVec2::ZERO,
            physical_size: UVec2::new(800, 600),
            depth: 0.0..1.0,
        }),
        ..Default::default()
    };
    camera.computed.clip_from_view = Mat4::orthographic_lh(-400.0, 400.0, -300.0, 300.0, 0.0, 1000.0);
    camera.computed.target_info = Some(bevy::camera::RenderTargetInfo {
        physical_size: UVec2::new(800, 600),
        scale_factor: 1.0,
    });

    let camera_transform = Transform::from_xyz(0.0, 0.0, 10.0);
    let camera_global_transform = GlobalTransform::from(camera_transform);

    app.world_mut().spawn((
        Camera2d,
        camera,
        Projection::Orthographic(OrthographicProjection::default_2d()),
        camera_transform,
        camera_global_transform,
    )).id()
}

/// Spawns a mock primary window with an 800x600 resolution and a centered cursor.
pub fn spawn_test_window(app: &mut App) -> Entity {
    let mut window = Window {
        resolution: bevy::window::WindowResolution::new(800, 600),
        ..Default::default()
    };
    window.set_cursor_position(Some(Vec2::new(400.0, 300.0)));
    app.world_mut().spawn((window, bevy::window::PrimaryWindow)).id()
}
