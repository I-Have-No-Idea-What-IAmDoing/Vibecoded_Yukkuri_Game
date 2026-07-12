use bevy::prelude::*;
use avian2d::prelude::*;
use crate::ai::{Flight, Needs, EmotionalState};
use crate::render::YukkuriSprite;
use crate::simulation::skills::AddXpEvent;
use crate::simulation::mount::GameLayer;

#[derive(Component, Reflect, Debug, Clone)]
#[reflect(Component, Default)]
pub struct MovementController {
    pub visual_bob_timer: f32,
    pub bob_speed: f32,
    pub bob_height: f32,
}

impl Default for MovementController {
    fn default() -> Self {
        Self {
            visual_bob_timer: 0.0,
            bob_speed: 15.0,
            bob_height: 8.0,
        }
    }
}

pub struct MovementSimulationPlugin;

impl Plugin for MovementSimulationPlugin {
    fn build(&self, app: &mut App) {
        app.register_type::<MovementController>()
            .add_systems(Update, (
                visual_bobbing_system,
                flight_system,
                flight_collision_modulation_system,
            ));
    }
}

pub fn visual_bobbing_system(
    time: Res<Time>,
    mut query_parent: Query<(Entity, &mut MovementController, &LinearVelocity, &YukkuriSprite, Option<&Flight>)>,
    mut query_child_transform: Query<&mut Transform>,
    mut message_writer: MessageWriter<AddXpEvent>,
) {
    let dt = time.delta_secs();

    for (parent_ent, mut controller, velocity, sprite, maybe_flight) in query_parent.iter_mut() {
        let speed = velocity.0.length();
        let is_flying = maybe_flight.map(|f| f.flight_state == 1 || f.flight_state == 4).unwrap_or(false);

        if speed > 0.1 && !is_flying {
            controller.visual_bob_timer += dt * controller.bob_speed;

            // Award Athletics XP to the parent entity
            let xp_gain = ((speed / 100.0) * dt).min(5.0 * dt);
            message_writer.write(AddXpEvent {
                entity: parent_ent,
                skill_id: "athletics".to_string(),
                amount: xp_gain,
            });
        }

        let bob_offset = if is_flying {
            0.0 // No bobbing during active flight
        } else {
            controller.visual_bob_timer.sin().abs() * controller.bob_height
        };

        let altitude_offset = maybe_flight.map(|f| f.altitude).unwrap_or(0.0);
        let total_offset = bob_offset + altitude_offset;

        if let Some(sprite_ent) = sprite.sprite_entity {
            if let Ok(mut trans) = query_child_transform.get_mut(sprite_ent) {
                trans.translation.y = total_offset;
            }
        }
    }
}
pub fn flight_system(
    time: Res<Time>,
    mut query: Query<(
        Entity,
        &mut Flight,
        Option<&crate::simulation::skills::Skills>,
        Option<&mut Needs>,
        Option<&mut EmotionalState>,
    )>,
    mut message_writer: MessageWriter<AddXpEvent>,
) {
    let dt = time.delta_secs();

    for (entity, mut flight, maybe_skills, mut maybe_needs, mut maybe_emotional) in query.iter_mut() {
        let agility = maybe_skills
            .and_then(|s| s.states.get("athletics"))
            .map(|s| 1.0 + (s.level as f32 - 1.0) * 0.1)
            .unwrap_or(1.0)
            .max(0.1);

        // 1. Stamina Management & XP Gain
        if flight.flight_state == 1 || flight.flight_state == 2 || flight.flight_state == 3 {
            // FLYING, TAKEOFF, SWOOPING
            flight.stamina -= (flight.fly_cost / agility) * dt;

            // Award athletics XP
            message_writer.write(AddXpEvent {
                entity,
                skill_id: "athletics".to_string(),
                amount: 2.0 * dt,
            });
        } else if flight.flight_state == 4 {
            // HOVERING
            flight.stamina -= (flight.hover_cost / agility) * dt;

            // Award athletics XP
            message_writer.write(AddXpEvent {
                entity,
                skill_id: "athletics".to_string(),
                amount: 1.0 * dt,
            });
        } else if flight.flight_state == 0 {
            // GROUNDED
            flight.stamina += flight.recovery_rate * dt;
        }

        flight.stamina = flight.stamina.clamp(0.0, flight.max_stamina);

        // State logic transitions
        if flight.stamina <= 0.0 && flight.flight_state != 0 && flight.flight_state != 5 {
            flight.flight_state = 5; // Set state to FALLING
        }

        // 2. Altitude updates
        let mut target_altitude = 0.0;

        match flight.flight_state {
            0 => target_altitude = 0.0, // GROUNDED
            2 => { // TAKEOFF
                target_altitude = flight.max_altitude;
                if flight.altitude >= flight.max_altitude * 0.95 {
                    flight.flight_state = 1; // Transitions to FLYING
                }
            }
            1 | 4 => target_altitude = flight.max_altitude, // FLYING or HOVERING
            6 => { // LANDING
                target_altitude = 0.0;
                if flight.altitude <= 0.1 {
                    flight.flight_state = 0; // Transitions to GROUNDED
                    flight.altitude = 0.0;
                }
            }
            3 => target_altitude = 5.0, // SWOOPING target altitude
            5 => { // FALLING
                flight.altitude -= flight.vertical_speed * 2.0 * dt;
                if flight.altitude <= 0.0 {
                    flight.altitude = 0.0;
                    flight.flight_state = 0; // Transitions to GROUNDED

                    // Apply Fall damage
                    if let Some(ref mut needs) = maybe_needs {
                        needs.health = (needs.health - 10.0 / agility).max(0.0);
                    }
                    if let Some(ref mut emotional) = maybe_emotional {
                        emotional.stress = (emotional.stress + 20.0 / agility).min(100.0);
                    }
                }
                continue; // Skip interpolation for falling as it has custom drop speed
            }
            _ => {}
        }

        // Interpolate altitude
        let diff = target_altitude - flight.altitude;
        if diff.abs() > 0.01 {
            let change = flight.vertical_speed * agility * dt;
            if diff.abs() < change {
                flight.altitude = target_altitude;
            } else {
                flight.altitude += if diff > 0.0 { change } else { -change };
            }
        }
    }
}

pub fn flight_collision_modulation_system(
    mut commands: Commands,
    query: Query<(Entity, &Flight), Changed<Flight>>,
) {
    for (entity, flight) in query.iter() {
        let new_layers = if flight.flight_state == 1 || flight.flight_state == 4 {
            // FLYING or HOVERING (high altitude)
            CollisionLayers::new(
                GameLayer::FlyingUnit,
                LayerMask::from(GameLayer::FlyingUnit) | LayerMask::from(GameLayer::HighObstacle),
            )
        } else if flight.flight_state == 3 {
            // SWOOPING (low altitude attack)
            CollisionLayers::new(
                GameLayer::FlyingUnit,
                LayerMask::from(GameLayer::GroundUnit) | LayerMask::from(GameLayer::FlyingUnit) | LayerMask::from(GameLayer::HighObstacle) | LayerMask::from(GameLayer::LowObstacle),
            )
        } else {
            // GROUNDED, TAKEOFF, LANDING, FALLING (normal ground colliders)
            CollisionLayers::new(
                GameLayer::GroundUnit,
                LayerMask::from(GameLayer::GroundUnit) | LayerMask::from(GameLayer::LowObstacle) | LayerMask::from(GameLayer::HighObstacle) | LayerMask::from(GameLayer::Water) | LayerMask::from(GameLayer::Item),
            )
        };
        commands.entity(entity).insert(new_layers);
    }
}
