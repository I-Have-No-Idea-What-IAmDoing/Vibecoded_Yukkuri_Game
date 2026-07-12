use bevy::prelude::*;
use crate::ai::{YukkuriStats, Needs, EmotionalState};
use crate::ai::persistence::Economy;
use crate::audio::PlaySoundEvent;
use crate::simulation::needs::FloatingText;

#[derive(bevy::prelude::Message, Debug, Clone)]
pub struct SellEntityRequest {
    pub entity_id: Entity,
}

#[derive(bevy::prelude::Message, Debug, Clone)]
pub struct TrainEntityRequest {
    pub entity_id: Entity,
}

#[derive(bevy::prelude::Message, Debug, Clone)]
pub struct PunishEntityRequest {
    pub entity_id: Entity,
}

pub struct PlayerActionsPlugin;

impl Plugin for PlayerActionsPlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<Economy>()
            .add_message::<SellEntityRequest>()
            .add_message::<TrainEntityRequest>()
            .add_message::<PunishEntityRequest>()
            .add_systems(Update, (
                handle_sell_requests,
                handle_train_requests,
                handle_punish_requests,
            ));
    }
}

pub fn handle_sell_requests(
    mut commands: Commands,
    mut requests: MessageReader<SellEntityRequest>,
    mut economy: ResMut<Economy>,
    query_yukkuri: Query<(&Needs, &EmotionalState, &YukkuriStats, &Transform)>,
    query_item: Query<(&crate::simulation::inventory::ItemStats, &Transform)>,
    mut sound_writer: MessageWriter<PlaySoundEvent>,
) {
    for request in requests.read() {
        let ent = request.entity_id;
        
        if let Ok((needs, emotional, stats, transform)) = query_yukkuri.get(ent) {
            let value = stats.calculate_value(needs, emotional);
            economy.money += value;
            
            // Spawn floating text showing credit value
            commands.spawn((
                FloatingText {
                    velocity: Vec2::new(0.0, 50.0),
                    lifetime: 0.0,
                    max_lifetime: 1.5,
                },
                Text::new(format!("+${value}")),
                TextColor(Color::srgb(0.2, 0.8, 0.2)),
                TextFont {
                    font_size: FontSize::Px(24.0),
                    ..default()
                },
                Transform::from_translation(transform.translation + Vec3::new(0.0, 20.0, 1.0)),
            ));
            
            sound_writer.write(PlaySoundEvent { name: "sell".to_string() });
            commands.entity(ent).despawn();
        } else if let Ok((item_stats, transform)) = query_item.get(ent) {
            // Sell item for full cost/value
            let value = item_stats.value as i32;
            economy.money += value;
            
            // Spawn floating text showing credit value
            commands.spawn((
                FloatingText {
                    velocity: Vec2::new(0.0, 50.0),
                    lifetime: 0.0,
                    max_lifetime: 1.5,
                },
                Text::new(format!("+${value}")),
                TextColor(Color::srgb(0.2, 0.8, 0.2)),
                TextFont {
                    font_size: FontSize::Px(24.0),
                    ..default()
                },
                Transform::from_translation(transform.translation + Vec3::new(0.0, 20.0, 1.0)),
            ));
            
            sound_writer.write(PlaySoundEvent { name: "sell".to_string() });
            commands.entity(ent).despawn();
        }
    }
}

pub fn handle_train_requests(
    mut commands: Commands,
    mut requests: MessageReader<TrainEntityRequest>,
    mut query: Query<(&mut YukkuriStats, &mut EmotionalState, &Transform)>,
    mut sound_writer: MessageWriter<PlaySoundEvent>,
) {
    for request in requests.read() {
        if let Ok((mut stats, mut emotional, transform)) = query.get_mut(request.entity_id) {
            stats.badges += 1;
            emotional.happiness = (emotional.happiness + 10.0).clamp(-100.0, 100.0);
            
            // Spawn floating text "+Badge"
            commands.spawn((
                FloatingText {
                    velocity: Vec2::new(0.0, 50.0),
                    lifetime: 0.0,
                    max_lifetime: 1.5,
                },
                Text::new("+Badge".to_string()),
                TextColor(Color::srgb(1.0, 0.9, 0.1)),
                TextFont {
                    font_size: FontSize::Px(22.0),
                    ..default()
                },
                Transform::from_translation(transform.translation + Vec3::new(0.0, 20.0, 1.0)),
            ));
            
            sound_writer.write(PlaySoundEvent { name: "train".to_string() });
        }
    }
}

pub fn handle_punish_requests(
    mut commands: Commands,
    mut requests: MessageReader<PunishEntityRequest>,
    mut query: Query<(&mut Needs, &mut EmotionalState, &mut YukkuriStats, &Transform)>,
    mut sound_writer: MessageWriter<PlaySoundEvent>,
) {
    for request in requests.read() {
        if let Ok((mut needs, mut emotional, mut stats, transform)) = query.get_mut(request.entity_id) {
            needs.health = (needs.health - 10.0).clamp(0.0, needs.max_health);
            emotional.happiness = (emotional.happiness - 20.0).clamp(-100.0, 100.0);
            emotional.stress = (emotional.stress + 20.0).clamp(0.0, 100.0);
            stats.discipline = (stats.discipline + 10.0).clamp(0.0, 100.0);
            
            // Spawn floating text "Punished!"
            commands.spawn((
                FloatingText {
                    velocity: Vec2::new(0.0, 50.0),
                    lifetime: 0.0,
                    max_lifetime: 1.5,
                },
                Text::new("Punished!".to_string()),
                TextColor(Color::srgb(0.95, 0.2, 0.2)),
                TextFont {
                    font_size: FontSize::Px(22.0),
                    ..default()
                },
                Transform::from_translation(transform.translation + Vec3::new(0.0, 20.0, 1.0)),
            ));
            
            sound_writer.write(PlaySoundEvent { name: "hit".to_string() });
        }
    }
}
