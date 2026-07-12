use bevy::prelude::*;
use bevy::world_serialization::DynamicWorldBuilder;
use pyo3::prelude::*;
use rusqlite::{params, Connection};
use std::collections::HashMap;
use serde_json::json;

use crate::ai::{
    AIState, PythonState, PythonAISandbox, Persistable, Needs, YukkuriStats,
    EmotionalState, StableId, Flight, SteeringConfig, MoveTarget, Dead, BaseColliderRadius,
    Personality, RelationshipRegistry, GossipQueue, SocialIdCounter, Predator,
};

#[derive(Resource, Reflect, Default, Clone, Debug)]
#[reflect(Resource, Default)]
pub struct Economy {
    pub money: i32,
}

#[derive(Resource, Reflect, Clone, Debug)]
#[reflect(Resource, Default)]
pub struct TimeElapsed {
    pub elapsed: f32,
    pub scale: f32,
    pub game_speed: f32,
}

impl Default for TimeElapsed {
    fn default() -> Self {
        Self {
            elapsed: 43200.0, // Start at midday (12:00) so the lighting overlay begins fully transparent.
            scale: 60.0,
            game_speed: 1.0,
        }
    }
}

impl TimeElapsed {
    pub fn hour_of_day(&self) -> f32 {
        (self.elapsed % 86400.0) / 3600.0
    }

    pub fn day(&self) -> u32 {
        (self.elapsed / 86400.0) as u32 + 1
    }

    pub fn is_night(&self) -> bool {
        let h = self.hour_of_day();
        h > 20.0 || h < 6.0
    }
}

/// Saves the game state to an SQLite database file.
pub fn save_game(world: &mut World, filepath: &str) -> Result<(), Box<dyn std::error::Error>> {
    // 1. Python-side FFI serialization
    // Find all entities with AIState and retrieve their serialized states from Python
    let mut entities_to_serialize = Vec::new();
    {
        let mut query = world.query_filtered::<Entity, With<AIState>>();
        for entity in query.iter(world) {
            entities_to_serialize.push(entity);
        }
    }

    // Call FFI functions to get MsgPack binary blobs for each entity
    let python_states = Python::with_gil(|py| {
        let sandbox = world.get_non_send::<PythonAISandbox>()
            .expect("PythonAISandbox not found");
        
        let mut results = Vec::new();
        for entity in entities_to_serialize {
            let entity_id = entity.index().index();
            if let Ok(bytes) = sandbox.serialize_entity(py, entity_id) {
                results.push((entity, bytes));
            }
        }
        results
    });

    // Write PythonState components back to entities
    for (entity, bytes) in python_states {
        world.entity_mut(entity).insert(PythonState {
            serialized_blob: bytes,
        });
    }

    // 2. Bevy dynamic world serialization using DynamicWorldBuilder
    let persistable_entities: Vec<Entity> = {
        let mut query = world.query_filtered::<Entity, With<Persistable>>();
        query.iter(world).collect()
    };

    let type_registry = world.resource::<AppTypeRegistry>().clone();
    let registry_read = type_registry.read();
    let dynamic_world = DynamicWorldBuilder::from_world(world, &registry_read)
        .deny_all_components()
        .allow_component::<Transform>()
        .allow_component::<Needs>()
        .allow_component::<YukkuriStats>()
        .allow_component::<Dead>()
        .allow_component::<BaseColliderRadius>()
        .allow_component::<EmotionalState>()
        .allow_component::<AIState>()
        .allow_component::<StableId>()
        .allow_component::<Flight>()
        .allow_component::<SteeringConfig>()
        .allow_component::<MoveTarget>()
        .allow_component::<Persistable>()
        .allow_component::<PythonState>()
        .allow_component::<Personality>()
        .allow_component::<RelationshipRegistry>()
        .allow_component::<GossipQueue>()
        .allow_component::<crate::simulation::skills::Skills>()
        .allow_component::<crate::simulation::mount::Mount>()
        .allow_component::<crate::simulation::mount::PendingDismount>()
        .allow_component::<crate::simulation::inventory::InventoryComponent>()
        .allow_component::<crate::simulation::inventory::ItemStats>()
        .allow_component::<crate::simulation::movement::MovementController>()
        .allow_component::<crate::simulation::navigation::MovementPath>()
        .allow_component::<crate::render::lighting::LightSource>()
        .allow_component::<Predator>()
        .allow_component::<crate::simulation::lod::LODComponent>()
        .extract_entities(persistable_entities.into_iter())
        .build();
    let ron_string = dynamic_world.serialize(&registry_read)?;

    // 3. Save to SQLite
    let conn = Connection::open(filepath)?;
    conn.execute(
        "CREATE TABLE IF NOT EXISTS global_state (key TEXT PRIMARY KEY, value TEXT)",
        [],
    )?;
    conn.execute(
        "CREATE TABLE IF NOT EXISTS chunks (chunk_id TEXT PRIMARY KEY, data BLOB)",
        [],
    )?;

    // Serialize global data JSON
    let money = world.get_resource::<Economy>().map(|e| e.money).unwrap_or(1000);
    let (time, time_scale, game_speed) = world.get_resource::<TimeElapsed>()
        .map(|t| (t.elapsed, t.scale, t.game_speed))
        .unwrap_or((0.0, 60.0, 1.0));
    let social_counter = world.get_resource::<SocialIdCounter>().map(|s| s.0).unwrap_or(0);
    let global_data = json!({
        "money": money,
        "time": time,
        "time_scale": time_scale,
        "game_speed": game_speed,
        "social_counter": social_counter,
    });
    let global_data_str = serde_json::to_string(&global_data)?;

    conn.execute(
        "INSERT OR REPLACE INTO global_state (key, value) VALUES (?, ?)",
        params!["global_data", global_data_str],
    )?;

    conn.execute(
        "INSERT OR REPLACE INTO chunks (chunk_id, data) VALUES (?, ?)",
        params!["global", ron_string.as_bytes()],
    )?;

    Ok(())
}

/// Loads the game state from an SQLite database file.
pub fn load_game(world: &mut World, filepath: &str) -> Result<(), Box<dyn std::error::Error>> {
    let conn = Connection::open(filepath)?;

    // Read global state
    let mut global_stmt = conn.prepare("SELECT value FROM global_state WHERE key='global_data'")?;
    let global_rows = global_stmt.query_map([], |row| row.get::<_, String>(0))?;

    for val_res in global_rows {
        if let Ok(val) = val_res {
            if let Ok(parsed) = serde_json::from_str::<serde_json::Value>(&val) {
                if let Some(money) = parsed.get("money").and_then(|m| m.as_i64()) {
                    world.insert_resource(Economy { money: money as i32 });
                }
                if let Some(time) = parsed.get("time").and_then(|t| t.as_f64()) {
                    let mut time_res = TimeElapsed::default();
                    time_res.elapsed = time as f32;
                    if let Some(scale) = parsed.get("time_scale").and_then(|s| s.as_f64()) {
                        time_res.scale = scale as f32;
                    }
                    if let Some(speed) = parsed.get("game_speed").and_then(|s| s.as_f64()) {
                        time_res.game_speed = speed as f32;
                    }
                    world.insert_resource(time_res);
                }
                let social_counter_val = parsed.get("social_counter").and_then(|s| s.as_u64()).unwrap_or(0);
                world.insert_resource(SocialIdCounter(social_counter_val));
            }
        }
    }

    // Read world data
    let mut chunk_stmt = conn.prepare("SELECT data FROM chunks WHERE chunk_id='global'")?;
    let mut chunk_rows = chunk_stmt.query([])?;
    let ron_bytes = if let Some(row) = chunk_rows.next()? {
        row.get::<_, Vec<u8>>(0)?
    } else {
        return Err("No global chunk found in save file".into());
    };
    let ron_str = std::str::from_utf8(&ron_bytes)?;

    // 2. Deserialize RON using bevy_world_serialization
    let type_registry = world.resource::<AppTypeRegistry>().clone();
    let registry_read = type_registry.read();
    
    use bevy::world_serialization::serde::WorldDeserializer;
    use serde::de::DeserializeSeed;
    use bevy::ecs::entity::EntityHashMap;
    
    let mut deserializer = ron::de::Deserializer::from_str(ron_str)?;
    let mut asset_server = world.resource_mut::<AssetServer>();
    let world_deserializer = WorldDeserializer {
        type_registry: &registry_read,
        load_from_path: &mut *asset_server,
    };
    let dynamic_world = world_deserializer.deserialize(&mut deserializer)?;

    // 3. Clear existing Persistable entities
    {
        let mut query = world.query_filtered::<Entity, With<Persistable>>();
        let entities: Vec<Entity> = query.iter(world).collect();
        for entity in entities {
            if let Ok(e) = world.get_entity_mut(entity) {
                e.despawn();
            }
        }
    }

    // 4. Load the dynamic world
    let mut entity_map = EntityHashMap::default();
    dynamic_world.write_to_world(world, &mut entity_map)?;

    // Ensure all loaded persistable entities have default social components if missing
    {
        let mut query = world.query_filtered::<Entity, With<Persistable>>();
        let entities: Vec<Entity> = query.iter(world).collect();
        for entity in entities {
            if world.entity(entity).get::<Personality>().is_none() {
                world.entity_mut(entity).insert(Personality::default());
            }
            if world.entity(entity).get::<RelationshipRegistry>().is_none() {
                world.entity_mut(entity).insert(RelationshipRegistry::default());
            }
            if world.entity(entity).get::<GossipQueue>().is_none() {
                world.entity_mut(entity).insert(GossipQueue::default());
            }
            if world.entity(entity).get::<crate::simulation::skills::Skills>().is_none() {
                let mut skills = crate::simulation::skills::Skills::default();
                if let Some(skill_registry) = world.get_resource::<crate::simulation::skills::SkillRegistry>() {
                    let trait_registry = world.get_resource::<crate::simulation::skills::TraitRegistry>();
                    let time_elapsed = world.get_resource::<TimeElapsed>();
                    let elapsed = time_elapsed.map(|t| t.elapsed).unwrap_or(0.0);
                    let personality = world.entity(entity).get::<Personality>();

                    for (skill_id, _definition) in &skill_registry.skills {
                        let mut state = crate::simulation::skills::SkillState {
                            level: 1,
                            current_xp: 0.0,
                            passion: 1.0,
                            last_used_gametime: elapsed,
                        };
                        if let Some(p) = personality {
                            if let Some(tr) = trait_registry {
                                for trait_id in &p.traits {
                                    if let Some(t_data) = tr.traits.get(trait_id) {
                                        if let Some(ref skill_mods) = t_data.skill_modifiers {
                                            if let Some(mod_data) = skill_mods.get(skill_id) {
                                                state.passion *= mod_data.passion_multiplier;
                                            }
                                        }
                                    }
                                }
                            }
                        }
                        skills.states.insert(skill_id.clone(), state);
                    }
                }
                world.entity_mut(entity).insert(skills);
            }
            if world.entity(entity).get::<crate::simulation::mount::Mount>().is_none() {
                world.entity_mut(entity).insert(crate::simulation::mount::Mount::default());
            }
            if world.entity(entity).get::<crate::simulation::inventory::InventoryComponent>().is_none() {
                world.entity_mut(entity).insert(crate::simulation::inventory::InventoryComponent::default());
            }
            if world.entity(entity).get::<crate::simulation::movement::MovementController>().is_none() {
                world.entity_mut(entity).insert(crate::simulation::movement::MovementController::default());
            }
        }
    }

    // 5. Python-side FFI state deserialization & remapping
    let mut id_map = HashMap::new();
    for (old_entity, new_entity) in entity_map.iter() {
        id_map.insert(old_entity.index().index(), new_entity.index().index());
    }

    let mut entities_with_python_state = Vec::new();
    let mut query = world.query::<(Entity, &PythonState)>();
    for (entity, py_state) in query.iter(world) {
        let new_index = entity.index().index();
        entities_with_python_state.push((new_index, py_state.serialized_blob.clone()));
    }

    // Acquire GIL and call FFI deserialization for each entity
    Python::with_gil(|py| {
        let sandbox = world.get_non_send::<PythonAISandbox>()
            .expect("PythonAISandbox not found");
        
        for (new_index, blob) in entities_with_python_state {
            let _ = sandbox.deserialize_entity(py, new_index, &blob, &id_map);
        }
    });

    Ok(())
}
