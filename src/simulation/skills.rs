use bevy::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use crate::ai::persistence::TimeElapsed;
use crate::ai::{Personality, EmotionalState, YukkuriStats};
use crate::simulation::needs::SimulationSettings;

#[derive(Reflect, Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct SkillState {
    pub level: u32,
    pub current_xp: f32,
    pub passion: f32,
    pub last_used_gametime: f32,
}

impl Default for SkillState {
    fn default() -> Self {
        Self {
            level: 1,
            current_xp: 0.0,
            passion: 1.0,
            last_used_gametime: 0.0,
        }
    }
}

#[derive(Component, Reflect, Debug, Clone, Default, Serialize, Deserialize, PartialEq)]
#[reflect(Component, Default)]
pub struct Skills {
    pub states: HashMap<String, SkillState>,
}

#[derive(Reflect, Debug, Clone, Deserialize, Serialize, PartialEq)]
pub struct SkillDefinition {
    pub name: String,
    pub description: String,
    pub max_level: u32,
    pub decay_rate: f32,
    pub soft_cap_base_level: u32,
}

#[derive(Resource, Reflect, Default, Clone, Debug)]
#[reflect(Resource, Default)]
pub struct SkillRegistry {
    pub skills: HashMap<String, SkillDefinition>,
}

#[derive(Reflect, Debug, Clone, Deserialize, Serialize, PartialEq)]
pub struct TraitSkillModifier {
    pub passion_multiplier: f32,
    pub soft_cap_offset: i32,
}

#[derive(Reflect, Debug, Clone, Deserialize, Serialize, PartialEq)]
pub struct TraitSocialModifiers {
    pub compatibility: Option<HashMap<String, f32>>,
}

#[derive(Reflect, Debug, Clone, Deserialize, Serialize, PartialEq)]
pub struct TraitDefinition {
    pub name: String,
    pub description: String,
    pub conflicts: Option<Vec<String>>,
    pub axis_shift: Option<HashMap<String, i32>>,
    pub stat_modifiers: Option<HashMap<String, f32>>,
    pub social_modifiers: Option<TraitSocialModifiers>,
    pub skill_modifiers: Option<HashMap<String, TraitSkillModifier>>,
}

#[derive(Resource, Reflect, Default, Clone, Debug)]
#[reflect(Resource, Default)]
pub struct TraitRegistry {
    pub traits: HashMap<String, TraitDefinition>,
}

/// Message emitted when an entity levels up a skill.
#[derive(bevy::prelude::Message, Debug, Clone)]
pub struct LevelUpMessage {
    pub entity: Entity,
    pub skill_id: String,
    pub new_level: u32,
}

pub fn load_skills_and_traits_system(
    mut skill_registry: ResMut<SkillRegistry>,
    mut trait_registry: ResMut<TraitRegistry>,
) {
    // Load skills
    let skills_path = "data/skills/skills.toml";
    match std::fs::read_to_string(skills_path) {
        Ok(content) => {
            #[derive(Deserialize)]
            struct TomlSkills {
                skills: HashMap<String, SkillDefinition>,
            }
            match toml::from_str::<TomlSkills>(&content) {
                Ok(data) => {
                    skill_registry.skills = data.skills;
                    info!("Loaded {} skill definitions", skill_registry.skills.len());
                }
                Err(err) => {
                    error!("Failed to parse skills.toml: {:?}", err);
                }
            }
        }
        Err(err) => {
            error!("Failed to read skills.toml: {:?}", err);
        }
    }

    // Load traits
    let traits_path = "data/traits/traits.toml";
    match std::fs::read_to_string(traits_path) {
        Ok(content) => {
            #[derive(Deserialize)]
            struct TomlTraits {
                traits: HashMap<String, TraitDefinition>,
            }
            match toml::from_str::<TomlTraits>(&content) {
                Ok(data) => {
                    trait_registry.traits = data.traits;
                    info!("Loaded {} trait definitions", trait_registry.traits.len());
                }
                Err(err) => {
                    error!("Failed to parse traits.toml: {:?}", err);
                }
            }
        }
        Err(err) => {
            error!("Failed to read traits.toml: {:?}", err);
        }
    }
}

pub fn initialize_personality_and_skills_system(
    mut commands: Commands,
    trait_registry: Res<TraitRegistry>,
    skill_registry: Res<SkillRegistry>,
    time_elapsed: Res<TimeElapsed>,
    mut query: Query<(Entity, &mut Personality, Option<&Skills>), Added<Personality>>,
) {
    let mut rng = rand::thread_rng();
    use rand::seq::SliceRandom;
    use rand::Rng;

    for (entity, mut personality, maybe_skills) in query.iter_mut() {
        if maybe_skills.is_some() {
            continue;
        }

        // 1. Roll random traits on spawn if traits set is empty (10% mutation chance)
        if personality.traits.is_empty() && rng.gen::<f32>() < 0.1 {
            let all_traits: Vec<&String> = trait_registry.traits.keys().collect();
            if !all_traits.is_empty() {
                if let Some(chosen_trait) = all_traits.choose(&mut rng) {
                    personality.traits.insert((*chosen_trait).clone());
                }
            }
        }

        let traits_list: Vec<String> = personality.traits.iter().cloned().collect();

        // 2. Apply Trait Axis Shifts to personality axes and clamp to [-100, 100]
        for trait_id in &traits_list {
            if let Some(t_data) = trait_registry.traits.get(trait_id) {
                if let Some(ref shifts) = t_data.axis_shift {
                    personality.kindness += shifts.get("kindness").copied().unwrap_or(0);
                    personality.energy += shifts.get("energy").copied().unwrap_or(0);
                    personality.bravery += shifts.get("bravery").copied().unwrap_or(0);
                    personality.greed += shifts.get("greed").copied().unwrap_or(0);
                }
            }
        }
        personality.kindness = personality.kindness.clamp(-100, 100);
        personality.energy = personality.energy.clamp(-100, 100);
        personality.bravery = personality.bravery.clamp(-100, 100);
        personality.greed = personality.greed.clamp(-100, 100);

        // 3. Initialize Skills component
        let mut skills = Skills::default();
        for skill_id in skill_registry.skills.keys() {
            let mut state = SkillState {
                level: 1,
                current_xp: 0.0,
                passion: 1.0, // default passion: Normal (1.0)
                last_used_gametime: time_elapsed.elapsed,
            };

            // Recalculate passion multiplier based on traits
            for trait_id in &traits_list {
                if let Some(t_data) = trait_registry.traits.get(trait_id) {
                    if let Some(ref skill_mods) = t_data.skill_modifiers {
                        if let Some(mod_data) = skill_mods.get(skill_id) {
                            state.passion *= mod_data.passion_multiplier;
                        }
                    }
                }
            }
            skills.states.insert(skill_id.clone(), state);
        }

        commands.entity(entity).insert(skills);
    }
}

#[derive(bevy::prelude::Message, Debug, Clone)]
pub struct AddXpEvent {
    pub entity: Entity,
    pub skill_id: String,
    pub amount: f32,
}

pub fn process_xp_gain_system(
    mut events: MessageReader<AddXpEvent>,
    skill_registry: Res<SkillRegistry>,
    trait_registry: Res<TraitRegistry>,
    settings: Res<SimulationSettings>,
    time_elapsed: Res<TimeElapsed>,
    mut query: Query<(
        &mut Skills,
        Option<&YukkuriStats>,
        Option<&Personality>,
        Option<&mut EmotionalState>,
    )>,
    mut message_writer: MessageWriter<LevelUpMessage>,
) {
    for event in events.read() {
        let Ok((mut skills, maybe_stats, maybe_personality, maybe_emotional)) = query.get_mut(event.entity) else {
            continue;
        };

        let Some(state) = skills.states.get_mut(&event.skill_id) else {
            continue;
        };

        let Some(definition) = skill_registry.skills.get(&event.skill_id) else {
            continue;
        };

        if state.level >= definition.max_level {
            continue;
        }

        // 1. Soft cap calculation
        let mut soft_cap_offset = 0;
        if let Some(personality) = maybe_personality {
            for trait_id in &personality.traits {
                if let Some(t_data) = trait_registry.traits.get(trait_id) {
                    if let Some(ref skill_mods) = t_data.skill_modifiers {
                        if let Some(mod_data) = skill_mods.get(&event.skill_id) {
                            soft_cap_offset += mod_data.soft_cap_offset;
                        }
                    }
                }
            }
        }

        let soft_cap_level = (definition.soft_cap_base_level as i32 + (state.passion * 2.0) as i32 + soft_cap_offset).max(1) as u32;
        let gain_multiplier = if state.level >= soft_cap_level { 0.1 } else { 1.0 };

        // 2. Intelligence factor
        let int_factor = maybe_stats.map(|s| s.intelligence).unwrap_or(1.0);

        // 3. Final XP gain
        let final_xp = event.amount * state.passion * int_factor * gain_multiplier;
        state.current_xp += final_xp;
        state.last_used_gametime = time_elapsed.elapsed;

        // 4. Burning Passion Effect
        if state.passion >= 2.5 {
            if let Some(mut emotional) = maybe_emotional {
                emotional.happiness = (emotional.happiness + 1.0).min(100.0);
            }
        }

        // 5. Level up checks
        let mut required_xp = settings.xp_base * (settings.xp_exponent.powf(state.level as f32));
        while state.current_xp >= required_xp && state.level < definition.max_level {
            state.current_xp -= required_xp;
            state.level += 1;
            info!("Entity {:?} leveled up {} to {}!", event.entity, event.skill_id, state.level);

            message_writer.write(LevelUpMessage {
                entity: event.entity,
                skill_id: event.skill_id.clone(),
                new_level: state.level,
            });

            required_xp = settings.xp_base * (settings.xp_exponent.powf(state.level as f32));
        }
    }
}

pub fn skill_decay_system(
    time_elapsed: Res<TimeElapsed>,
    skill_registry: Res<SkillRegistry>,
    mut query: Query<&mut Skills>,
    mut last_day_index: Local<Option<i32>>,
) {
    let seconds_per_day = 86400.0;
    let current_day_index = (time_elapsed.elapsed / seconds_per_day) as i32;

    if last_day_index.is_none() {
        *last_day_index = Some(current_day_index);
        return;
    }

    let last_day = last_day_index.unwrap();
    if current_day_index > last_day {
        let days_passed = current_day_index - last_day;
        for mut skills in query.iter_mut() {
            for _ in 0..days_passed {
                for (skill_id, state) in skills.states.iter_mut() {
                    let Some(definition) = skill_registry.skills.get(skill_id) else {
                        continue;
                    };
                    let decay_rate = definition.decay_rate;
                    if decay_rate <= 0.0 {
                        continue;
                    }
                    let days_since_use = (time_elapsed.elapsed - state.last_used_gametime) / seconds_per_day;
                    if days_since_use > 1.0 {
                        let excess_days = days_since_use - 1.0;
                        let loss = decay_rate * excess_days;
                        state.current_xp = (state.current_xp - loss).max(0.0);
                    }
                }
            }
        }
        *last_day_index = Some(current_day_index);
    }
}

pub struct SkillsSimulationPlugin;

impl Plugin for SkillsSimulationPlugin {
    fn build(&self, app: &mut App) {
        app.insert_resource(SkillRegistry::default())
            .insert_resource(TraitRegistry::default())
            .add_message::<AddXpEvent>()
            .add_systems(Startup, load_skills_and_traits_system)
            .add_systems(Update, (
                initialize_personality_and_skills_system,
                process_xp_gain_system,
                skill_decay_system,
            ))
            .register_type::<SkillState>()
            .register_type::<Skills>()
            .register_type::<SkillRegistry>()
            .register_type::<TraitRegistry>()
            .add_message::<LevelUpMessage>();
    }
}
