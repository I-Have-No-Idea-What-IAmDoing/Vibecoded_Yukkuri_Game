use bevy::prelude::*;
use serde::Deserialize;
use std::collections::HashMap;
use crate::ai::{
    RelationshipRegistry, GossipQueue,
    GossipPacket, AIState, Needs, EmotionalState, StableId, GossipEvent, YukkuriStats,
};
use crate::ai::persistence::TimeElapsed;
use crate::simulation::needs::SimulationSettings;
use avian2d::prelude::SpatialQuery;

#[derive(Resource, Debug, Clone, Default)]
pub struct InteractionRegistry {
    pub interactions: HashMap<String, InteractionDefinition>,
}

#[derive(Deserialize, Debug, Clone, Default)]
pub struct InteractionDefinition {
    pub base_impact: f32,
    pub social_impact: HashMap<String, f32>,
    #[serde(default)]
    pub physical_impact: HashMap<String, f32>,
    #[serde(default)]
    pub target_physical_impact: HashMap<String, f32>,
    #[serde(default)]
    pub actor_physical_impact: HashMap<String, f32>,
    #[serde(default)]
    pub range_type: Option<String>,
    #[serde(default)]
    pub modifiers: HashMap<String, HashMap<String, f32>>,
}

#[derive(Deserialize, Debug, Clone, Default)]
struct InteractionsFile {
    pub interaction: HashMap<String, InteractionDefinition>,
}

pub fn load_interactions_system(mut commands: Commands) {
    let content = std::fs::read_to_string("data/ai/interactions.toml")
        .expect("Failed to read data/ai/interactions.toml");
    let parsed: InteractionsFile = toml::from_str(&content)
        .expect("Failed to parse interactions.toml");
    commands.insert_resource(InteractionRegistry {
        interactions: parsed.interaction,
    });
}


pub fn family_proximity_benefits_system(
    time: Res<Time<Virtual>>,
    settings: Res<SimulationSettings>,
    mut timer: Local<Timer>,
    mut query: Query<(
        Entity,
        &RelationshipRegistry,
        &Transform,
        &mut Needs,
        &mut EmotionalState,
        &AIState,
    )>,
) {
    if timer.duration() == std::time::Duration::ZERO {
        *timer = Timer::from_seconds(2.0, TimerMode::Repeating);
    }
    timer.tick(time.delta());
    if !timer.just_finished() {
        return;
    }

    let benefit_range_sq = settings.family_benefit_range * settings.family_benefit_range;

    // Collect snapshots to avoid disjoint query borrowing issues
    let mut snapshots = Vec::new();
    for (entity, reg, transform, _, _, ai) in query.iter() {
        if let Some(fam_id) = reg.family_group_id {
            snapshots.push((
                entity,
                transform.translation.truncate(),
                fam_id,
                ai.current_action.clone(),
            ));
        }
    }

    for i in 0..snapshots.len() {
        for j in (i + 1)..snapshots.len() {
            let (ent_a, pos_a, fam_a, act_a) = &snapshots[i];
            let (ent_b, pos_b, fam_b, act_b) = &snapshots[j];
            if fam_a != fam_b {
                continue;
            }
            let dist_sq = (*pos_a - *pos_b).length_squared();
            if dist_sq <= benefit_range_sq {
                if let Ok([a_comps, b_comps]) = query.get_many_mut([*ent_a, *ent_b]) {
                    let (_, _, _, mut a_needs, mut a_emotion, _) = a_comps;
                    let (_, _, _, mut b_needs, mut b_emotion, _) = b_comps;

                    // 1. Togetherness
                    a_emotion.happiness = (a_emotion.happiness + settings.family_happiness_gain).clamp(-100.0, 100.0);
                    a_emotion.stress = (a_emotion.stress - settings.family_stress_reduction).clamp(0.0, 100.0);
                    b_emotion.happiness = (b_emotion.happiness + settings.family_happiness_gain).clamp(-100.0, 100.0);
                    b_emotion.stress = (b_emotion.stress - settings.family_stress_reduction).clamp(0.0, 100.0);

                    // 2. Food sharing
                    if act_a == "Eat" && b_needs.hunger > settings.family_food_sharing_threshold {
                        b_needs.hunger = (b_needs.hunger - settings.family_food_sharing_amount).clamp(0.0, 100.0);
                        b_emotion.happiness = (b_emotion.happiness + settings.family_happiness_gain).clamp(-100.0, 100.0);
                    }
                    if act_b == "Eat" && a_needs.hunger > settings.family_food_sharing_threshold {
                        a_needs.hunger = (a_needs.hunger - settings.family_food_sharing_amount).clamp(0.0, 100.0);
                        a_emotion.happiness = (a_emotion.happiness + settings.family_happiness_gain).clamp(-100.0, 100.0);
                    }

                    // 3. Nest sharing
                    if act_a == "Sleep" {
                        b_needs.energy = (b_needs.energy + settings.family_sleep_energy_gain).clamp(0.0, 100.0);
                        b_emotion.stress = (b_emotion.stress - settings.family_sleep_stress_reduction).clamp(0.0, 100.0);
                    }
                    if act_b == "Sleep" {
                        a_needs.energy = (a_needs.energy + settings.family_sleep_energy_gain).clamp(0.0, 100.0);
                        a_emotion.stress = (a_emotion.stress - settings.family_sleep_stress_reduction).clamp(0.0, 100.0);
                    }
                }
            }
        }
    }
}

pub fn relationship_decay_system(
    time_elapsed: Res<TimeElapsed>,
    mut query: Query<(Entity, &mut RelationshipRegistry, &StableId)>,
) {
    let now = time_elapsed.elapsed;

    // Build a map of stable_id -> family_group_id
    let mut family_map = HashMap::new();
    for (_, reg, sid) in query.iter() {
        family_map.insert(sid.0, reg.family_group_id);
    }

    for (_, mut registry, _sid) in query.iter_mut() {
        let parent_ids = registry.biological_parents.clone();
        let child_ids = registry.biological_children.clone();
        let mate_id = registry.mate_id;
        let fam_id = registry.family_group_id;

        let mut to_remove = Vec::new();
        for (&other_stable_id, rel) in registry.relationships.iter() {
            if now - rel.last_update > 600.0 {
                // Check exemptions:
                if parent_ids.contains(&other_stable_id)
                    || child_ids.contains(&other_stable_id)
                    || Some(other_stable_id) == mate_id
                {
                    continue;
                }
                if let Some(f_id) = fam_id {
                    if let Some(Some(other_f_id)) = family_map.get(&other_stable_id) {
                        if f_id == *other_f_id {
                            continue; // Family group exemption
                        }
                    }
                }
                to_remove.push(other_stable_id);
            }
        }

        for other_stable_id in to_remove {
            registry.relationships.remove(&other_stable_id);
        }
    }
}

fn check_line_of_sight(
    spatial_query: &SpatialQuery,
    actor_entity: Entity,
    actor_pos: Vec2,
    witness_entity: Entity,
    witness_pos: Vec2,
) -> bool {
    let direction = witness_pos - actor_pos;
    let dist = direction.length();
    if dist > 0.0 {
        if let Ok(dir) = Dir2::new(direction) {
            let hits = spatial_query.ray_hits(
                actor_pos,
                dir,
                dist,
                1, // max_hits
                true, // solid
                &avian2d::prelude::SpatialQueryFilter::from_excluded_entities(vec![actor_entity, witness_entity]),
            );
            if !hits.is_empty() {
                return false;
            }
        }
    }
    true
}

pub fn gossip_propagation_system(
    mut message_reader: MessageReader<GossipEvent>,
    spatial_query: SpatialQuery,
    time_elapsed: Res<TimeElapsed>,
    mut query: Query<(
        Entity,
        &StableId,
        &Transform,
        &mut GossipQueue,
        &RelationshipRegistry,
        &YukkuriStats,
    )>,
) {
    let now = time_elapsed.elapsed;

    // Build a map of stable_id -> family_group_id
    let mut family_map = HashMap::new();
    for (_, sid, _, _, reg, _) in query.iter() {
        family_map.insert(sid.0, reg.family_group_id);
    }

    for event in message_reader.read() {
        let range_val = match event.range_type.as_str() {
            "auditory_loud" => 500.0,
            "auditory" => 300.0,
            _ => 300.0,
        };
        let range_sq = range_val * range_val;

        // Collect snapshots of targets to update witness gossip queues
        let mut witnesses_to_update = Vec::new();

        for (witness_entity, _, witness_trans, _, witness_reg, _) in query.iter() {
            if witness_entity == event.initiator_entity || witness_entity == event.target_entity {
                continue;
            }

            let witness_pos = witness_trans.translation.truncate();
            let dist_sq = (event.position - witness_pos).length_squared();
            if dist_sq > range_sq {
                continue;
            }

            // LoS Check for visual
            if event.range_type == "visual"
                && !check_line_of_sight(
                    &spatial_query,
                    event.initiator_entity,
                    event.position,
                    witness_entity,
                    witness_pos,
                )
            {
                continue;
            }

            // Interest Group Bonus
            let mut value = 10.0;
            if let Some(actor_fam) = family_map.get(&event.initiator_stable_id).and_then(|&f| f) {
                if Some(actor_fam) == witness_reg.family_group_id {
                    value += 5.0;
                }
            }

            witnesses_to_update.push((witness_entity, value));
        }

        // Apply witnessing
        for (w_entity, value) in witnesses_to_update {
            if let Ok(mut comps) = query.get_mut(w_entity) {
                comps.3.add_packet(GossipPacket {
                    target_id: event.initiator_stable_id,
                    event_type: event.event_type.clone(),
                    value,
                    timestamp: now,
                });
            }
        }

        // 2. Direct exchange
        if ["Talk", "Greet", "Chat"].contains(&event.event_type.as_str()) {
            if let Ok([init_comps, target_comps]) = query.get_many_mut([event.initiator_entity, event.target_entity]) {
                let (_, init_sid, _, mut init_gossip, init_reg, _) = init_comps;
                let (_, target_sid, _, mut target_gossip, target_reg, _) = target_comps;

                let init_packets = init_gossip.priority_queue.clone();
                let target_packets = target_gossip.priority_queue.clone();

                let is_fam = init_reg.is_family(target_sid.0, target_reg.family_group_id);

                // Share init_packets with target
                for mut packet in init_packets {
                    if packet.target_id == target_sid.0 {
                        continue;
                    }
                    packet.value *= 0.9;
                    if is_fam {
                        packet.value *= 1.2;
                    }
                    if packet.value >= 5.0 {
                        packet.timestamp = now;
                        target_gossip.add_packet(packet);
                    }
                }

                // Share target_packets with init
                for mut packet in target_packets {
                    if packet.target_id == init_sid.0 {
                        continue;
                    }
                    packet.value *= 0.9;
                    if is_fam {
                        packet.value *= 1.2;
                    }
                    if packet.value >= 5.0 {
                        packet.timestamp = now;
                        init_gossip.add_packet(packet);
                    }
                }
            }
        }
    }
}

pub fn family_formation_system(
    time: Res<Time>,
    mut timer: Local<f32>,
    mut query: Query<(Entity, &StableId, &mut RelationshipRegistry)>,
) {
    *timer += time.delta_secs();
    if *timer < 2.0 {
        return;
    }
    *timer = 0.0;

    let mut stable_map = HashMap::new();
    for (entity, sid, reg) in query.iter() {
        stable_map.insert(sid.0, (entity, reg.family_group_id));
    }

    let mut updates = HashMap::new();

    for (entity, _sid, reg) in query.iter() {
        for (&other_sid, rel) in &reg.relationships {
            if rel.affinity > 80.0 && rel.trust > 80.0 {
                if let Some(&(other_entity, other_fam_id)) = stable_map.get(&other_sid) {
                    let a_fam = updates.get(&entity).copied().or(reg.family_group_id);
                    let b_fam = updates.get(&other_entity).copied().or(other_fam_id);

                    if a_fam.is_none() && b_fam.is_none() {
                        let new_fam = rand::random::<u32>() as u64;
                        updates.insert(entity, new_fam);
                        updates.insert(other_entity, new_fam);
                    } else if a_fam.is_some() && b_fam.is_none() {
                        updates.insert(other_entity, a_fam.unwrap());
                    } else if a_fam.is_none() && b_fam.is_some() {
                        updates.insert(entity, b_fam.unwrap());
                    }
                }
            }
        }
    }

    for (entity, _, mut reg) in query.iter_mut() {
        if let Some(&new_fam) = updates.get(&entity) {
            reg.family_group_id = Some(new_fam);
        }
    }
}

pub struct SocialSimulationPlugin;

impl Plugin for SocialSimulationPlugin {
    fn build(&self, app: &mut App) {
        app.insert_resource(InteractionRegistry::default())
            .init_resource::<TimeElapsed>()
            .add_systems(Startup, load_interactions_system)
            .add_systems(
                Update,
                (
                    family_proximity_benefits_system,
                    relationship_decay_system,
                    gossip_propagation_system,
                    family_formation_system,
                ),
            );
    }
}
