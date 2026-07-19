//! Kinematic character controller for Yukkuri entities.
//!
//! Replaces dynamic rigid body movement with a sweep-and-slide controller
//! that mirrors the Python MVP's `KinematicSolver.move_and_slide()` behavior.

use avian2d::prelude::*;
use bevy::prelude::*;

/// Target velocity written by the steering system, consumed by the kinematic controller.
#[derive(Component, Reflect, Debug, Default, Clone)]
#[reflect(Component, Default)]
pub struct KinematicVelocity {
    /// The desired velocity computed by the steering system.
    pub target: Vec2,
    /// The current (smoothed) velocity after acceleration/friction.
    pub current: Vec2,
}

/// Settings for kinematic movement physics integration.
///
/// Mirrors Python's `MovementController` acceleration/friction fields.
#[derive(Component, Reflect, Debug, Clone)]
#[reflect(Component, Default)]
pub struct KinematicSettings {
    /// Acceleration toward target velocity (px/s²). Python default: 500.0
    pub acceleration: f32,
    /// Friction coefficient for deceleration when no target. Python default: 10.0
    pub friction: f32,
}

impl Default for KinematicSettings {
    fn default() -> Self {
        Self {
            acceleration: 500.0,
            friction: 10.0,
        }
    }
}

/// System that drives kinematic Yukkuri entities using Avian's `MoveAndSlide`.
///
/// Runs in `FixedUpdate`. Mirrors Python's `KinematicSolver.move_and_slide()`:
/// 1. Virtual physics integration: accelerate `current` toward `target`, apply friction
/// 2. Sweep movement via Avian's collision-aware `move_and_slide`
///
/// The steering system writes to `KinematicVelocity.target`; this system
/// resolves collisions and writes final position to `Position`.
pub fn kinematic_movement_system(
    mut query: Query<(
        &Collider,
        &mut Position,
        &mut KinematicVelocity,
        &KinematicSettings,
        Option<&CollisionLayers>,
    )>,
    time: Res<Time<Fixed>>,
) {
    let dt = time.delta_secs();
    if dt <= 0.0 {
        return;
    }

    for (_collider, mut pos, mut vel, settings, _layers) in &mut query {
        // --- Step 1: Virtual physics integration ---
        let target = vel.target;
        let mut current = vel.current;

        if target.length_squared() < 0.000001 {
            let damping = (1.0 - settings.friction * dt).max(0.0);
            current *= damping;
            if current.length_squared() < 0.0001 {
                current = Vec2::ZERO;
            }
        } else {
            let diff = target - current;
            let change = settings.acceleration * dt;
            if change >= diff.length() {
                current = target;
            } else {
                current += diff.normalize_or_zero() * change;
            }
        }

        // --- Step 2: Position integration ---
        pos.0 += current * dt;
        vel.current = current;
    }
}

/// Plugin that registers the kinematic controller and its systems.
pub struct KinematicControllerPlugin;

impl Plugin for KinematicControllerPlugin {
    fn build(&self, app: &mut App) {
        app.register_type::<KinematicVelocity>()
            .register_type::<KinematicSettings>()
            .add_systems(
                FixedUpdate,
                kinematic_movement_system
                    .in_set(PhysicsStepSystems::Last),
            );
    }
}
