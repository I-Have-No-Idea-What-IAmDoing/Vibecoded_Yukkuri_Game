pub mod blackboard;
pub mod commands;
pub mod persistence;

use pyo3::prelude::*;
use bevy::prelude::*;
use std::collections::{HashMap, HashSet};
use std::path::Path;
use blackboard::Blackboard;
use commands::{Command, CommandType};
use crate::simulation::needs::FloatingText;
use crate::simulation::movement::{
    FLIGHT_STATE_GROUNDED, FLIGHT_STATE_FLYING, FLIGHT_STATE_HOVERING,
    FLIGHT_STATE_SWOOPING,
};

/// Workspace root resolved at compile time from the Cargo manifest directory.
///
/// Using `env!("CARGO_MANIFEST_DIR")` bakes the absolute path of the
/// workspace root into the binary, so paths to `./src` and `./.venv` are
/// correct regardless of which directory the executable is invoked from.
const WORKSPACE_ROOT: &str = env!("CARGO_MANIFEST_DIR");

#[pymodule]
pub fn yukkuri_rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<blackboard::TargetInfo>()?;
    m.add_class::<blackboard::Blackboard>()?;
    m.add_class::<commands::CommandType>()?;
    m.add_class::<commands::Command>()?;
    let _ = crate::ui::console::register_console_bindings(m);
    Ok(())
}

/// The single-threaded sandboxed Python behavior runner.
pub struct PythonAISandbox {
    pub behavior_module: Py<PyModule>,
}

impl PythonAISandbox {
    /// Creates a new PythonAISandbox and imports the behavior_ffi module.
    ///
    /// All paths are resolved relative to [`WORKSPACE_ROOT`] (the Cargo
    /// manifest directory baked in at compile time), so the binary works
    /// correctly regardless of which directory it is invoked from.
    pub fn new(py: Python) -> PyResult<Self> {
        let sys = py.import("sys")?;
        let path_attr = sys.getattr("path")?;
        let path: &Bound<'_, pyo3::types::PyList> = path_attr.downcast()?;

        // Add workspace /src to the Python module search path.
        let src_path = Path::new(WORKSPACE_ROOT).join("src");
        path.insert(0, src_path.to_str().unwrap_or("./src"))?;

        // Add the virtual-environment site-packages to sys.path so that
        // third-party packages (py_trees, pymunk, …) installed in the project
        // venv are importable without relying on the shell's active venv.
        let venv_root = Path::new(WORKSPACE_ROOT).join(".venv");
        if venv_root.exists() {
            // Windows layout:  .venv/Lib/site-packages
            let win_path = venv_root.join("Lib").join("site-packages");
            if win_path.exists() {
                path.insert(0, win_path.to_str().unwrap())?;
            } else {
                // Unix layout:  .venv/lib/pythonX.Y/site-packages
                if let Ok(entries) = std::fs::read_dir(venv_root.join("lib")) {
                    for entry in entries.flatten() {
                        let p = entry.path().join("site-packages");
                        if p.exists() {
                            path.insert(0, p.to_str().unwrap())?;
                            break;
                        }
                    }
                }
            }
        }

        let behavior_module = py
            .import("yukkuri_game.game.systems.behavior_ffi")?
            .unbind();

        Ok(Self { behavior_module })
    }

    /// Ticks a single entity with the provided Blackboard snapshot.
    pub fn tick_entity(
        &self,
        py: Python,
        blackboard: Blackboard,
    ) -> PyResult<Vec<Command>> {
        let behavior_module = self.behavior_module.bind(py);
        let result = behavior_module
            .call_method1("tick_entity_with_blackboard", (blackboard,))?;

        let commands: Vec<Command> = result.extract()?;
        Ok(commands)
    }

    /// Serializes Python-side state for the given entity to MessagePack bytes.
    pub fn serialize_entity(&self, py: Python, entity_id: u32) -> PyResult<Vec<u8>> {
        let behavior_module = self.behavior_module.bind(py);
        let result = behavior_module.call_method1("serialize_ai_state", (entity_id,))?;
        let bytes: Vec<u8> = result.extract()?;
        Ok(bytes)
    }

    /// Deserializes and remaps Python-side state for the given entity.
    pub fn deserialize_entity(
        &self,
        py: Python,
        entity_id: u32,
        blob: &[u8],
        id_map: &HashMap<u32, u32>,
    ) -> PyResult<()> {
        let behavior_module = self.behavior_module.bind(py);
        let _ = behavior_module.call_method1("deserialize_ai_state", (entity_id, blob, id_map))?;
        Ok(())
    }

    /// Cleans up any cached behavior tree or state for the given entity ID.
    pub fn cleanup_entity(&self, py: Python, entity_id: u32) -> PyResult<()> {
        let behavior_module = self.behavior_module.bind(py);
        let _ = behavior_module.call_method1("cleanup_entity_cache", (entity_id,))?;
        Ok(())
    }
}

// Components
#[derive(Component, Reflect, Debug, Clone)]
#[reflect(Component, Default)]
pub struct Needs {
    pub health: f32,
    pub hunger: f32,
    pub social: f32,
    pub energy: f32,
    pub cleanliness: f32,
    pub bladder: f32,
    pub easiness: f32,
    pub max_health: f32,
}

impl Default for Needs {
    fn default() -> Self {
        Self {
            health: 100.0,
            hunger: 0.0,
            social: 50.0,
            energy: 100.0,
            cleanliness: 100.0,
            bladder: 0.0,
            easiness: 50.0,
            max_health: 100.0,
        }
    }
}

#[allow(dead_code)]
#[derive(Component, Reflect, Debug, Clone, PartialEq)]
#[reflect(Component, Default)]
pub struct YukkuriStats {
    pub name: String,
    pub type_id: String,
    pub growth_stage: String,
    pub age: f32,
    pub intelligence: f32,
    pub badges: i32,
    pub quality_score: f32,
    pub discipline: f32,
    pub agility: f32,
    pub tastebud_spoiled: f32,
}

impl Default for YukkuriStats {
    fn default() -> Self {
        Self {
            name: "reimu".to_string(),
            type_id: "reimu".to_string(),
            growth_stage: "Adult".to_string(),
            age: 0.0,
            intelligence: 1.0,
            badges: 0,
            quality_score: 0.0,
            discipline: 0.0,
            agility: 1.0,
            tastebud_spoiled: 0.0,
        }
    }
}

impl YukkuriStats {
    pub fn calculate_value(&self, needs: &Needs, emotional_state: &EmotionalState) -> i32 {
        let badge_val = 500;
        let health_penalty = 2.0;
        let age_bonus = 10.0;
        let mut score = 100.0;
        
        score += emotional_state.happiness + 100.0;
        score += self.badges as f32 * badge_val as f32;
        if needs.health < needs.max_health {
            score -= (needs.max_health - needs.health) * health_penalty;
        }
        score += ((self.age / 60.0) as i32) as f32 * age_bonus;
        
        score.max(0.0) as i32
    }
}

/// Component for predator behavior logic.
#[derive(Component, Reflect, Debug, Clone, PartialEq)]
#[reflect(Component, Default)]
pub struct Predator {
    pub prey_tags: HashSet<String>,
    pub prey_sense_radius: f32,
    pub hunger_threshold: f32,
    pub aggression: f32,
    pub dps: f32,
}

impl Default for Predator {
    fn default() -> Self {
        Self {
            prey_tags: ["Yukkuri".to_string(), "reimu".to_string(), "marisa".to_string()].into_iter().collect(),
            prey_sense_radius: 300.0,
            hunger_threshold: 60.0,
            aggression: 1.0,
            dps: 20.0,
        }
    }
}

/// Marker component for dead yukkuri.
#[derive(Component, Reflect, Debug, Default, Clone, PartialEq)]
#[reflect(Component, Default)]
pub struct Dead;

/// Tracks the base collider radius of a yukkuri, used to compute scale-dependent collider sizes.
#[derive(Component, Reflect, Debug, Default, Clone, PartialEq)]
#[reflect(Component, Default)]
pub struct BaseColliderRadius(pub f32);

#[derive(Component, Reflect, Debug, Clone)]
#[reflect(Component, Default)]
pub struct EmotionalState {
    pub happiness: f32,
    pub stress: f32,
}

impl Default for EmotionalState {
    fn default() -> Self {
        Self {
            happiness: 0.0,
            stress: 0.0,
        }
    }
}

#[derive(Component, Reflect, Debug, Clone, Default)]
#[reflect(Component, Default)]
pub struct AIState {
    pub current_action: String,
    pub current_target_id: i32,
    pub short_term_memory: HashMap<u32, (f32, f32, f32)>,
}

/// A stable, session-persistent entity identifier stored as a component.
///
/// The value is the raw `u64` bit-representation of the Bevy [`Entity`] at
/// spawn time (`Entity::to_bits()`).  It is **never** re-derived from a live
/// entity reference, so it cannot silently alias a recycled entity slot.
///
/// The Python side receives only the low-32 raw index (`entity_id: u32`) as a
/// short per-session key.  The full `u64` is kept on the Rust side so that
/// [`EntityRegistry`] can provide a safe roundtrip for command dispatch.
#[derive(Component, Reflect, Debug, Clone, Copy, PartialEq, Eq, Hash, Default)]
#[reflect(Component, Default)]
pub struct StableId(pub u64);

impl StableId {
    /// Creates a [`StableId`] from a live [`Entity`].
    #[inline]
    pub fn from_entity(entity: Entity) -> Self {
        Self(entity.to_bits())
    }
}

use serde::{Serialize, Deserialize};

#[derive(Component, Reflect, Debug, Clone, PartialEq)]
#[reflect(Component, Default)]
pub struct Personality {
    pub kindness: i32,
    pub energy: i32,
    pub bravery: i32,
    pub greed: i32,
    pub base_kindness: i32,
    pub base_energy: i32,
    pub base_bravery: i32,
    pub base_greed: i32,
    pub traits: HashSet<String>,
}

impl Default for Personality {
    fn default() -> Self {
        // Generate random personality values using thread_rng
        let mut rng = rand::thread_rng();
        use rand::Rng;
        let kindness = rng.gen_range(-50..=50);
        let energy = rng.gen_range(-50..=50);
        let bravery = rng.gen_range(-50..=50);
        let greed = rng.gen_range(-50..=50);
        Self {
            kindness,
            energy,
            bravery,
            greed,
            base_kindness: kindness,
            base_energy: energy,
            base_bravery: bravery,
            base_greed: greed,
            traits: HashSet::new(),
        }
    }
}

#[derive(Reflect, Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct MemoryHeadline {
    pub id: u64,
    pub timestamp: f32,
    pub importance: f32,
    pub sentiment: f32,
    pub event_type: String,
    pub is_locked: bool,
}

#[derive(Reflect, Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct RelationshipData {
    pub affinity: f32,
    pub trust: f32,
    pub fear: f32,
    pub familiarity: f32,
    pub last_update: f32,
    pub base_compatibility: f32,
    pub trivial_sentiment_sum: f32,
    pub core_sentiment_sum: f32,
    pub trivial_buffer: Vec<MemoryHeadline>, // Max size 25 (FIFO)
    pub core_buffer: Vec<MemoryHeadline>,    // Max size 35 (Prioritized)
}

impl Default for RelationshipData {
    fn default() -> Self {
        Self {
            affinity: 0.0,
            trust: 0.0,
            fear: 0.0,
            familiarity: 0.0,
            last_update: 0.0,
            base_compatibility: 0.0,
            trivial_sentiment_sum: 0.0,
            core_sentiment_sum: 0.0,
            trivial_buffer: Vec::new(),
            core_buffer: Vec::new(),
        }
    }
}

impl RelationshipData {
    pub fn new(now: f32) -> Self {
        Self {
            last_update: now,
            ..Default::default()
        }
    }

    pub fn adjust_trust(&mut self, delta: f32) {
        self.trust = (self.trust + delta).clamp(-100.0, 100.0);
    }

    pub fn adjust_fear(&mut self, delta: f32) {
        self.fear = (self.fear + delta).clamp(0.0, 100.0);
    }

    pub fn add_headline(&mut self, headline: MemoryHeadline, threshold: f32) {
        if headline.importance > threshold || headline.is_locked {
            self.add_core_memory(headline);
        } else {
            self.add_trivial_memory(headline);
        }
        self.affinity = (self.base_compatibility + self.trivial_sentiment_sum + self.core_sentiment_sum).clamp(-100.0, 100.0);
    }

    fn add_trivial_memory(&mut self, headline: MemoryHeadline) {
        if self.trivial_buffer.len() >= 25 {
            let removed = self.trivial_buffer.remove(0);
            self.trivial_sentiment_sum -= removed.sentiment;
        }
        self.trivial_sentiment_sum += headline.sentiment;
        self.trivial_buffer.push(headline);
    }

    fn add_core_memory(&mut self, headline: MemoryHeadline) {
        if self.core_buffer.len() < 35 {
            self.core_sentiment_sum += headline.sentiment;
            self.core_buffer.push(headline);
            return;
        }
        let mut victim_index = None;
        for (i, mem) in self.core_buffer.iter().enumerate() {
            if !mem.is_locked {
                victim_index = Some(i);
                break;
            }
        }
        if let Some(idx) = victim_index {
            let removed = self.core_buffer.remove(idx);
            self.core_sentiment_sum -= removed.sentiment;
            self.core_sentiment_sum += headline.sentiment;
            self.core_buffer.push(headline);
            return;
        }
        let mut min_locked_importance = f32::INFINITY;
        let mut min_locked_index = None;
        for (i, mem) in self.core_buffer.iter().enumerate() {
            if mem.importance < min_locked_importance {
                min_locked_importance = mem.importance;
                min_locked_index = Some(i);
            }
        }
        if let Some(idx) = min_locked_index {
            if headline.importance > (min_locked_importance + 20.0) {
                let removed = self.core_buffer.remove(idx);
                self.core_sentiment_sum -= removed.sentiment;
                self.core_sentiment_sum += headline.sentiment;
                self.core_buffer.push(headline);
            }
        }
    }
}

#[derive(Component, Reflect, Debug, Clone, Default)]
#[reflect(Component, Default)]
pub struct RelationshipRegistry {
    pub relationships: HashMap<u64, RelationshipData>,
    pub biological_parents: Vec<u64>,
    pub biological_children: Vec<u64>,
    pub family_group_id: Option<u64>,
    pub mate_id: Option<u64>,
}

impl RelationshipRegistry {
    pub fn get_affinity(&self, target_stable_id: u64, base_compatibility: f32) -> f32 {
        self.relationships
            .get(&target_stable_id)
            .map(|r| r.affinity)
            .unwrap_or(base_compatibility)
    }

    pub fn is_family(&self, target_stable_id: u64, target_family_group_id: Option<u64>) -> bool {
        if self.biological_parents.contains(&target_stable_id) {
            return true;
        }
        if self.biological_children.contains(&target_stable_id) {
            return true;
        }
        if Some(target_stable_id) == self.mate_id {
            return true;
        }
        if let (Some(a), Some(b)) = (self.family_group_id, target_family_group_id) {
            if a == b {
                return true;
            }
        }
        false
    }
}

#[derive(Reflect, Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct GossipPacket {
    pub target_id: u64,
    pub event_type: String,
    pub value: f32,
    pub timestamp: f32,
}

#[derive(Component, Reflect, Debug, Clone, Default)]
#[reflect(Component, Default)]
pub struct GossipQueue {
    pub priority_queue: Vec<GossipPacket>,
}

impl GossipQueue {
    pub fn add_packet(&mut self, packet: GossipPacket) {
        let max_length = 10;
        let mut duplicate_index = None;
        for (i, existing) in self.priority_queue.iter().enumerate() {
            if existing.target_id == packet.target_id && existing.event_type == packet.event_type {
                duplicate_index = Some(i);
                break;
            }
        }
        if let Some(idx) = duplicate_index {
            if packet.value > self.priority_queue[idx].value {
                self.priority_queue.remove(idx);
                self.priority_queue.push(packet);
                self.priority_queue.sort_by(|a, b| b.value.partial_cmp(&a.value).unwrap_or(std::cmp::Ordering::Equal));
            }
            return;
        }
        if self.priority_queue.len() < max_length {
            self.priority_queue.push(packet);
            self.priority_queue.sort_by(|a, b| b.value.partial_cmp(&a.value).unwrap_or(std::cmp::Ordering::Equal));
        } else {
            if let Some(last) = self.priority_queue.last() {
                if packet.value > last.value {
                    self.priority_queue.pop();
                    self.priority_queue.push(packet);
                    self.priority_queue.sort_by(|a, b| b.value.partial_cmp(&a.value).unwrap_or(std::cmp::Ordering::Equal));
                }
            }
        }
    }
}

/// A frame-local resource mapping the Python-facing raw entity index (`u32`)
/// to the live Bevy [`Entity`] (which carries the correct generation counter).
///
/// This is rebuilt every frame by [`tick_python_ai_system`] from the current
/// query results, so a despawned entity's index is **never** present when
/// [`apply_ai_commands`] reads it.  Commands whose index is absent are logged
/// and silently dropped rather than corrupting another entity at the same slot.
#[derive(Resource, Debug, Default)]
pub struct EntityRegistry(pub HashMap<u32, Entity>);

#[derive(Resource, Default)]
pub struct SocialIdCounter(pub u64);

#[derive(bevy::prelude::Message, Debug, Clone)]
pub struct GossipEvent {
    pub initiator_entity: Entity,
    pub target_entity: Entity,
    pub initiator_stable_id: u64,
    pub target_stable_id: u64,
    pub position: Vec2,
    pub range_type: String,
    pub event_type: String,
}

#[derive(Component, Reflect, Debug, Clone)]
#[reflect(Component, Default)]
pub struct Flight {
    pub flight_state: u32,
    pub altitude: f32,
    pub stamina: f32,
    pub max_stamina: f32,
    pub fly_cost: f32,
    pub hover_cost: f32,
    pub recovery_rate: f32,
    pub vertical_speed: f32,
    pub max_altitude: f32,
}

impl Default for Flight {
    fn default() -> Self {
        Self {
            flight_state: 0,
            altitude: 0.0,
            stamina: 100.0,
            max_stamina: 100.0,
            fly_cost: 5.0,
            hover_cost: 2.0,
            recovery_rate: 10.0,
            vertical_speed: 50.0,
            max_altitude: 100.0,
        }
    }
}

#[derive(Component, Debug, Clone, Default)]
pub struct VisibleTargets {
    pub targets: Vec<blackboard::TargetInfo>,
}

#[allow(dead_code)]
#[derive(Component, Reflect, Debug, Clone)]
#[reflect(Component, Default)]
pub struct MoveTarget {
    pub position: Vec2,
    pub acceptance_radius: f32,
}

#[derive(Component, Reflect, Debug, Clone)]
#[reflect(Component, Default)]
pub struct StuckDetector {
    pub last_pos: Vec2,
    pub stuck_timer: f32,
    pub repath_timer: f32,
}

impl Default for StuckDetector {
    fn default() -> Self {
        Self {
            last_pos: Vec2::ZERO,
            stuck_timer: 0.0,
            repath_timer: 0.0,
        }
    }
}


impl Default for MoveTarget {
    fn default() -> Self {
        Self {
            position: Vec2::ZERO,
            acceptance_radius: 25.0,
        }
    }
}

/// Per-entity steering parameters, sourced from the prefab TOML `[steering]` section.
///
/// Carried as a component so that [`populate_visible_targets_system`] and
/// [`move_target_steering_system`] can read per-species values without
/// touching [`WorldSettings`].
#[derive(Component, Reflect, Debug, Clone)]
#[reflect(Component, Default)]
pub struct SteeringConfig {
    /// Maximum movement speed in world-units/second (maps to `SteeringComponent.max_speed`).
    pub max_speed: f32,
    /// Maximum steering force (maps to `SteeringComponent.max_force`).
    pub max_force: f32,
    /// Broadphase perception radius in world-units (maps to `Vision.range = 300.0`).
    pub perception_radius: f32,
    /// Distance at which a `MoveTarget` is considered reached.
    pub arrival_radius: f32,
}

impl Default for SteeringConfig {
    fn default() -> Self {
        Self {
            max_speed: 150.0,
            max_force: 50.0,
            perception_radius: 300.0,
            arrival_radius: 50.0,
        }
    }
}


/// Marker component indicating that the entity should be persisted.
#[derive(Component, Reflect, Debug, Clone, Default)]
#[reflect(Component, Default)]
pub struct Persistable;

/// Component storing MsgPack-serialized Python state.
#[derive(Component, Reflect, Debug, Clone, Default)]
#[reflect(Component, Default)]
pub struct PythonState {
    pub serialized_blob: Vec<u8>,
}

// Resources

/// Deserialisation target for `data/config.toml` – `[world]` section only.
#[derive(serde::Deserialize, Debug)]
struct WorldTomlSection {
    width: f32,
    height: f32,
}

#[derive(serde::Deserialize, Debug)]
struct GameConfigToml {
    world: WorldTomlSection,
}

/// Loads [`WorldSettings`] from `data/config.toml` (relative to the Cargo
/// manifest directory).  Falls back to 3 000 × 3 000 with a warning if the
/// file is absent or malformed so the game still boots in all environments.
pub fn load_world_settings() -> WorldSettings {
    let config_path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("data")
        .join("config.toml");

    match std::fs::read_to_string(&config_path) {
        Ok(contents) => match toml::from_str::<GameConfigToml>(&contents) {
            Ok(cfg) => WorldSettings {
                width: cfg.world.width,
                height: cfg.world.height,
            },
            Err(e) => {
                eprintln!(
                    "[WorldSettings] Failed to parse data/config.toml: {}; \
                     using defaults (3000×3000)",
                    e
                );
                WorldSettings::default()
            }
        },
        Err(e) => {
            eprintln!(
                "[WorldSettings] Could not read data/config.toml: {}; \
                 using defaults (3000×3000)",
                e
            );
            WorldSettings::default()
        }
    }
}

#[derive(Resource, Debug, Clone)]
pub struct WorldSettings {
    pub width: f32,
    pub height: f32,
}

impl Default for WorldSettings {
    /// Returns 3 000 × 3 000 as a compile-time fallback.  Prefer calling
    /// [`load_world_settings`] at startup so the value comes from
    /// `data/config.toml`.
    fn default() -> Self {
        Self {
            width: 3000.0,
            height: 3000.0,
        }
    }
}

#[derive(Resource, Debug, Default, Clone)]
pub struct PoppedCommands(pub Vec<Command>);

/// Bevy system to populate `VisibleTargets` each frame via a distance check.
///
/// Replaces the Python `VisibilitySystem` + `PerceptionSystem` pair from
/// MVP_python with a simplified broadphase-only pass:
/// - Perception radius comes from each entity's [`SteeringConfig`] (TOML).
/// - FOV is implicitly 360° (no angle check), matching `Vision(fov=360.0)`.
///
/// # Deferred work (see implementation_plan.md — Deferred Work table)
/// - TODO(deferred): Add raycast/LOS narrowphase via Avian2D `SpatialQuery::ray_hits`.
/// - TODO(deferred): Add temporal batching (20%/frame) once entity count warrants it.
/// - TODO(deferred): Add reaction-delay gating (`0.5 / agility`) once `agility` stat exists.
/// - TODO(deferred): Add relation classification (Prey/Threat/Family/Friend/Enemy)
///   once `RelationshipRegistry` component is ported.
/// - TODO(deferred): Populate `short_term_memory` when entities leave perception radius.
pub fn populate_visible_targets_system(
    world_settings: Res<WorldSettings>,
    spatial_query: avian2d::prelude::SpatialQuery,
    time: Res<Time>,
    time_elapsed: Option<Res<crate::ai::persistence::TimeElapsed>>,
    // ParamSet is required because both sub-queries match the same entities
    mut queries: ParamSet<(
        // p0: read-only snapshot of all potential targets
        Query<(
            Entity,
            &Transform,
            &StableId,
            &YukkuriStats,
            &RelationshipRegistry,
            &Personality,
            Option<&Predator>,
        )>,
        // p1: mutable observer pass — writes VisibleTargets
        Query<(
            Entity,
            &Transform,
            &mut VisibleTargets,
            &StableId,
            &SteeringConfig,
            &RelationshipRegistry,
            &Personality,
            Option<&Predator>,
            Option<&mut AIState>,
            &YukkuriStats,
        )>,
    )>,
) {
    let world_height = world_settings.height;
    let current_time = if let Some(ref te) = time_elapsed {
        te.elapsed
    } else {
        time.elapsed_secs() * 60.0
    };

    // Phase 1 — collect a cheap snapshot via p0, then release the borrow.
    let targets: Vec<(
        Entity,
        Vec2,
        u64,
        String,
        String,
        Option<u64>,
        Personality,
        Option<Predator>,
    )> = queries
        .p0()
        .iter()
        .map(|(e, t, sid, stats, reg, pers, pred)| {
            (
                e,
                t.translation.truncate(),
                sid.0,
                stats.type_id.clone(),
                stats.growth_stage.clone(),
                reg.family_group_id,
                pers.clone(),
                pred.cloned(),
            )
        })
        .collect();

    // Phase 2 — iterate p1 mutably with the snapshot already collected.
    for (
        observer_entity,
        observer_transform,
        mut visible_targets,
        _observer_sid,
        steering,
        observer_reg,
        observer_pers,
        observer_predator,
        maybe_ai_state,
        observer_stats,
    ) in queries.p1().iter_mut()
    {
        // Gather previous detection times and positions
        let mut old_positions = HashMap::new();
        let mut prev_detection = HashMap::new();
        for target in &visible_targets.targets {
            old_positions.insert(target.entity_id, (target.x, target.y));
            prev_detection.insert(target.entity_id, target.detected_at);
        }

        visible_targets.targets.clear();

        let obs_pos = observer_transform.translation.truncate();
        let radius_sq = steering.perception_radius * steering.perception_radius;

        let mut currently_visible = std::collections::HashSet::new();

        for (
            target_entity,
            target_pos,
            target_stable_id,
            target_type_id,
            target_growth_stage,
            target_family_group_id,
            target_pers,
            target_predator,
        ) in &targets
        {
            // Never report self.
            if *target_entity == observer_entity {
                continue;
            }

            let delta = *target_pos - obs_pos;
            let dist_sq = delta.length_squared();

            if dist_sq > radius_sq {
                continue;
            }

            let distance = dist_sq.sqrt();
            let target_entity_id = target_entity.index().index();

            // Line of Sight (LOS) raycast obstruction check
            if distance > 0.0 {
                if let Ok(dir) = Dir2::new(delta) {
                    let hits = spatial_query.ray_hits(
                        obs_pos,
                        dir,
                        distance,
                        1,
                        true,
                        &avian2d::prelude::SpatialQueryFilter::from_excluded_entities(vec![observer_entity, *target_entity]),
                    );
                    if !hits.is_empty() {
                        // Perception is blocked by obstacle/wall
                        continue;
                    }
                }
            }

            // Calculate affinity: if relationship exists, use it. Otherwise, compute base compatibility!
            let affinity = if let Some(rel) = observer_reg.relationships.get(target_stable_id) {
                rel.affinity
            } else {
                let diff_kind = (observer_pers.kindness - target_pers.kindness).abs();
                let diff_ener = (observer_pers.energy - target_pers.energy).abs();
                let diff_brav = (observer_pers.bravery - target_pers.bravery).abs();
                let diff_gree = (observer_pers.greed - target_pers.greed).abs();
                let total_diff = diff_kind + diff_ener + diff_brav + diff_gree;
                100.0 - (total_diff as f32 / 4.0)
            };

            let is_family = observer_reg.is_family(*target_stable_id, *target_family_group_id);

            // Determine is_threat and is_prey biological tags
            let is_prey = if let Some(ref my_predator) = observer_predator {
                my_predator.prey_tags.contains(target_type_id) || my_predator.prey_tags.contains("Yukkuri")
            } else {
                false
            };

            let is_threat = if let Some(ref target_predator) = target_predator {
                target_predator.prey_tags.contains(&observer_stats.type_id) || target_predator.prey_tags.contains("Yukkuri")
            } else {
                false
            };

            // Keep original detection time if known, otherwise set to current_time
            let detected_at = prev_detection.get(&target_entity_id).cloned().unwrap_or(current_time);
            currently_visible.insert(target_entity_id);

            visible_targets.targets.push(blackboard::TargetInfo::from_bevy(
                target_entity_id,
                *target_stable_id,
                target_type_id.clone(),
                target_growth_stage.clone(),
                target_pos.x,
                target_pos.y,
                world_height,
                distance,
                affinity,
                is_threat,
                is_prey,
                is_family,
                std::collections::HashSet::new(),
                detected_at,
            ));
        }

        // Manage Short-Term Memory (Object Permanence) when entities leave perception/view
        if let Some(mut ai_state) = maybe_ai_state {
            for (tid, (tx, ty)) in &old_positions {
                if !currently_visible.contains(tid) {
                    ai_state.short_term_memory.insert(*tid, (*tx, *ty, current_time));
                }
            }

            // Forget old memories (MEMORY_DURATION = 10.0 seconds)
            let memory_duration = 10.0;
            ai_state.short_term_memory.retain(|_, (_, _, timestamp)| {
                current_time - *timestamp <= memory_duration
            });
        }
    }
}


/// Bevy system to tick all entities through Python Behavior Trees (GIL-safe).
///
/// Acquires the GIL once per frame, rebuilds [`EntityRegistry`] with the
/// current live entity set (clearing any stale entries from despawned
/// entities), then ticks every AI entity sequentially.
pub fn tick_python_ai_system(
    sandbox: NonSend<PythonAISandbox>,
    world_settings: Res<WorldSettings>,
    time: Res<Time>,
    nav_service: Option<Res<crate::simulation::hpa::NavigationService>>,
    time_elapsed: Option<Res<crate::ai::persistence::TimeElapsed>>,
    mut query: Query<(
        Entity,
        &Transform,
        Option<&Needs>,
        Option<&EmotionalState>,
        Option<&Flight>,
        Option<&YukkuriStats>,
        Option<&VisibleTargets>,
        Option<&mut AIState>,
        Option<&Personality>,
        Option<&crate::simulation::skills::Skills>,
        Option<&crate::simulation::mount::Mount>,
        Option<&crate::simulation::inventory::InventoryComponent>,
        Option<&crate::simulation::lod::LODComponent>,
    )>,
    mut command_queue: ResMut<PoppedCommands>,
    mut entity_registry: ResMut<EntityRegistry>,
    mut frame_counter: Local<u32>,
) {
    let world_height = world_settings.height;

    // Rebuild the registry from scratch each frame so despawned entities are
    // never present when apply_ai_commands looks up a command's entity_id.
    entity_registry.0.clear();

    *frame_counter = frame_counter.wrapping_add(1);

    // Read grid snapshot
    let (grid_width, grid_height, grid_cells) = if let Some(ref ns) = nav_service {
        let grid = (**ns).grid.read().unwrap();
        let cells_mask = grid.cells.iter().map(|c| c.access_mask).collect();
        (grid.width, grid.height, cells_mask)
    } else {
        (0, 0, Vec::new())
    };

    let (day, hour_of_day, is_night, elapsed) = if let Some(ref te) = time_elapsed {
        (te.day(), te.hour_of_day(), te.is_night(), te.elapsed)
    } else {
        (1, 12.0, false, 0.0)
    };

    Python::with_gil(|py| {
        for (
            entity,
            transform,
            maybe_needs,
            maybe_emotion,
            maybe_flight,
            maybe_stats,
            maybe_visible,
            mut maybe_ai_state,
            maybe_personality,
            maybe_skills,
            maybe_mount,
            maybe_inventory,
            maybe_lod,
        ) in query.iter_mut() {
            // Raw u32 index used as the Python-facing entity_id.
            // entity.index() returns EntityIndex; EntityIndex::index() returns u32.
            let entity_id = entity.index().index();
            entity_registry.0.insert(entity_id, entity);

            let lod_level = maybe_lod.map(|l| l.level).unwrap_or(0);
            if lod_level == 1 && *frame_counter % 2 != 0 {
                continue;
            }
            if lod_level == 2 && *frame_counter % 5 != 0 {
                continue;
            }

            // Build stats HashMap
            let mut stats = HashMap::new();
            let (traits, kindness, energy_p, bravery, greed) = if let Some(p) = maybe_personality {
                (p.traits.iter().cloned().collect(), p.kindness, p.energy, p.bravery, p.greed)
            } else {
                (Vec::new(), 0, 0, 0, 0)
            };
            stats.insert("kindness".to_string(), kindness as f32);
            stats.insert("energy_personality".to_string(), energy_p as f32);
            stats.insert("bravery".to_string(), bravery as f32);
            stats.insert("greed".to_string(), greed as f32);
            // Forward real frame delta-time so Python behavior trees use accurate timing
            // instead of the hardcoded 0.1s fallback in behavior_ffi.py.
            let dt_factor = match lod_level {
                1 => 2.0,
                2 => 5.0,
                _ => 1.0,
            };
            stats.insert("dt".to_string(), time.delta_secs() * dt_factor);
            if let Some(needs) = maybe_needs {
                stats.insert("health".to_string(), needs.health);
                stats.insert("hunger".to_string(), needs.hunger);
                stats.insert("social".to_string(), needs.social);
                stats.insert("energy".to_string(), needs.energy);
                stats.insert("cleanliness".to_string(), needs.cleanliness);
                stats.insert("bladder".to_string(), needs.bladder);
                stats.insert("easiness".to_string(), needs.easiness);
                stats.insert("max_health".to_string(), needs.max_health);
            }
            if let Some(emotion) = maybe_emotion {
                stats.insert("happiness".to_string(), emotion.happiness);
                stats.insert("stress".to_string(), emotion.stress);
            }

            let altitude = maybe_flight.map(|f| f.altitude).unwrap_or(0.0);
            let flight_state = maybe_flight.map(|f| f.flight_state).unwrap_or(0);

            let type_id = maybe_stats
                .map(|s| s.type_id.clone())
                .unwrap_or_else(|| "reimu".to_string());
            let growth_stage = maybe_stats
                .map(|s| s.growth_stage.clone())
                .unwrap_or_else(|| "Adult".to_string());

            let visible_targets = if let Some(visible) = maybe_visible {
                let reaction_delay = if let Some(stats) = maybe_stats {
                    if stats.agility > 0.0 {
                        0.5 / stats.agility
                    } else {
                        0.5
                    }
                } else {
                    0.5
                };
                visible.targets.iter()
                    .filter(|t| (elapsed - t.detected_at) >= reaction_delay)
                    .cloned()
                    .collect()
            } else {
                Vec::new()
            };

            let current_action = maybe_ai_state
                .as_ref()
                .map(|s| s.current_action.clone())
                .unwrap_or_else(|| "Idle".to_string());

            let short_term_memory = maybe_ai_state
                .as_ref()
                .map(|s| s.short_term_memory.clone())
                .unwrap_or_default();

            let skills_map = if let Some(skills) = maybe_skills {
                skills.states.iter().map(|(k, v)| (k.clone(), v.level)).collect()
            } else {
                HashMap::new()
            };

            let parent_id = maybe_mount.and_then(|m| m.parent_id.map(|p| p.index().index()));
            let children_ids = maybe_mount.map(|m| m.children_ids.iter().map(|c| c.index().index()).collect()).unwrap_or_default();
            let inventory = maybe_inventory.map(|inv| inv.items.iter().map(|item| (item.item_type_id.clone(), item.quantity)).collect()).unwrap_or_default();

            let blackboard = Blackboard::from_bevy(
                entity_id,
                stats,
                transform.translation.x,
                transform.translation.y,
                altitude,
                flight_state,
                visible_targets,
                current_action,
                short_term_memory,
                world_height,
                type_id,
                growth_stage,
                traits,
                skills_map,
                parent_id,
                children_ids,
                inventory,
                grid_width,
                grid_height,
                grid_cells.clone(),
                day,
                hour_of_day,
                is_night,
                elapsed,
            );

            match sandbox.tick_entity(py, blackboard) {
                Ok(cmds) => {
                    if let Some(ref mut ai_state) = maybe_ai_state {
                        if let Ok(py_ai_dict) =
                            sandbox.behavior_module.bind(py).getattr("_ai_states")
                        {
                            if let Ok(py_ai) = py_ai_dict.get_item(entity_id) {
                                if let Ok(act) = py_ai.getattr("current_action") {
                                    if let Ok(act_str) = act.extract::<String>() {
                                        ai_state.current_action = act_str;
                                    }
                                }
                                if let Ok(tgt) = py_ai.getattr("current_target_id") {
                                    if let Ok(tgt_val) = tgt.extract::<i32>() {
                                        ai_state.current_target_id = tgt_val;
                                    }
                                }
                            }
                        }
                    }
                    command_queue.0.extend(cmds);
                }
                Err(err) => {
                    eprintln!(
                        "Python FFI error ticking entity {}: {:?}",
                        entity_id, err
                    );
                    err.print(py);
                }
            }
        }
    });
}

/// Bevy system to apply high-level action commands dispatched from Python.
///
/// Uses [`EntityRegistry`] to convert the Python-facing raw entity index back
/// to a live Bevy [`Entity`] (with its correct generation counter) instead of
/// the fragile `Entity::from_raw_u32` reconstruction, which would silently
/// alias a recycled slot after entities are despawned and re-spawned.
pub fn apply_ai_commands(
    mut commands: Commands,
    mut popped_commands: ResMut<PoppedCommands>,
    world_settings: Res<WorldSettings>,
    entity_registry: Res<EntityRegistry>,
    mut message_writer: MessageWriter<crate::audio::PlaySoundEvent>,
    mut gossip_writer: MessageWriter<GossipEvent>,
    time_elapsed: Res<persistence::TimeElapsed>,
    interaction_registry: Res<crate::simulation::social::InteractionRegistry>,
    mut social_counter: ResMut<SocialIdCounter>,
    mut queries: ParamSet<(
        Query<(
            Entity,
            &mut Needs,
            &mut EmotionalState,
            &mut avian2d::prelude::LinearVelocity,
            Option<&mut crate::render::Animator>,
            Option<&AIState>,
            &StableId,
            &mut Personality,
            &mut RelationshipRegistry,
            &mut GossipQueue,
            &Transform,
            Option<&mut YukkuriStats>,
            Option<&Predator>,
            Option<&crate::simulation::navigation::MovementPath>,
            Option<&MoveTarget>,
        )>,
        Query<(Entity, &mut crate::simulation::inventory::ItemStats, &Transform)>,
        Query<(
            Entity,
            &mut Needs,
            &mut EmotionalState,
            &YukkuriStats,
            &Transform,
            &StableId,
            &Personality,
            &mut RelationshipRegistry,
            &mut GossipQueue,
        )>,
    )>,
    item_registry: Res<crate::simulation::inventory::ItemRegistry>,
    trait_registry: Res<crate::simulation::skills::TraitRegistry>,
    mut nav_service: Option<ResMut<crate::simulation::hpa::NavigationService>>,
    mut xp_writer: Option<MessageWriter<crate::simulation::skills::AddXpEvent>>,
    time: Res<Time>,
) {
    let world_height = world_settings.height;
    let cmds: Vec<Command> = popped_commands.0.drain(..).collect();

    for cmd in cmds {
        let entity_id = cmd.entity_id;

        // Resolve the Python-facing raw index to the live generational Entity.
        // If the entity was despawned this frame the registry entry is absent
        // and the command is silently dropped rather than corrupting another
        // entity at the recycled slot.
        let bevy_entity = match entity_registry.0.get(&entity_id) {
            Some(&e) => e,
            None => {
                eprintln!(
                    "apply_ai_commands: entity index {} not in registry \
(despawned?); dropping {:?} command",
                    entity_id, cmd.cmd_type
                );
                continue;
            }
        };

        // 1. Get a read-only snapshot of actor components (cloning them)
        let actor_snapshot = {
            if let Ok((entity, needs, emotional, _, _, _, stable_id, personality, _, _, transform, maybe_ystats, maybe_predator, maybe_path, maybe_target)) = queries.p0().get(bevy_entity) {
                Some((
                    entity,
                    needs.clone(),
                    emotional.clone(),
                    stable_id.0,
                    personality.clone(),
                    transform.translation,
                    maybe_ystats.cloned(),
                    maybe_predator.cloned(),
                    maybe_path.cloned(),
                    maybe_target.cloned(),
                ))
            } else {
                None
            }
        };

        if let Some((actor_ent, a_needs, a_emotion, a_stable_id, a_pers, a_pos, a_ystats, a_pred, a_path, a_target)) = actor_snapshot {
            // 2. Perform target interaction / item consumption
            let mut actor_needs_modifier = a_needs.clone();
            let mut actor_emotion_modifier = a_emotion.clone();
            let mut actor_velocity_modifier = None;
            let mut actor_tastebud_spoiled_val = a_ystats.as_ref().map(|s| s.tastebud_spoiled);
            let mut actor_relationship_update = None;

            match cmd.cmd_type {
                CommandType::MoveTo => {
                    if let Some((tx, bevy_ty)) = cmd.get_bevy_coordinate("target_x", "target_y", world_height) {
                        let accept = cmd.payload.get("acceptance_radius").and_then(|v| v.parse::<f32>().ok()).unwrap_or(25.0);
                        let new_pos = Vec2::new(tx, bevy_ty);

                        // Check if we should skip inserting MoveTarget to avoid overwriting active path/waypoint following
                        let mut skip = false;
                        if let Some(ref path) = a_path {
                            if let Some(&final_wp) = path.waypoints.last() {
                                if final_wp.distance(new_pos) < 1.0 {
                                    skip = true;
                                }
                            }
                        }
                        if let Some(ref target) = a_target {
                            if target.position.distance(new_pos) < 1.0 {
                                skip = true;
                            }
                        }

                        if !skip {
                            commands.entity(actor_ent).insert(MoveTarget {
                                position: new_pos,
                                acceptance_radius: accept,
                            });
                        }
                    }
                }
                CommandType::Flee => {
                    let vx = cmd.payload.get("velocity_x").and_then(|v| v.parse::<f32>().ok()).unwrap_or(0.0);
                    let py_vy = cmd.payload.get("velocity_y").and_then(|v| v.parse::<f32>().ok()).unwrap_or(0.0);
                    let bevy_vy = -py_vy;
                    actor_velocity_modifier = Some(Vec2::new(vx, bevy_vy));
                }
                CommandType::ModifyStat => {
                    let stat_name = cmd.payload.get("stat_name").cloned().unwrap_or_default();
                    let amount = cmd.payload.get("amount").and_then(|v| v.parse::<f32>().ok()).unwrap_or(0.0);

                    match stat_name.as_str() {
                        "health" => actor_needs_modifier.health = (actor_needs_modifier.health + amount).clamp(0.0, actor_needs_modifier.max_health),
                        "hunger" => actor_needs_modifier.hunger = (actor_needs_modifier.hunger + amount).clamp(0.0, 100.0),
                        "social" => actor_needs_modifier.social = (actor_needs_modifier.social + amount).clamp(0.0, 100.0),
                        "energy" => actor_needs_modifier.energy = (actor_needs_modifier.energy + amount).clamp(0.0, 100.0),
                        "cleanliness" => actor_needs_modifier.cleanliness = (actor_needs_modifier.cleanliness + amount).clamp(0.0, 100.0),
                        "bladder" => actor_needs_modifier.bladder = (actor_needs_modifier.bladder + amount).clamp(0.0, 100.0),
                        "easiness" => actor_needs_modifier.easiness = (actor_needs_modifier.easiness + amount).clamp(0.0, 100.0),
                        "happiness" => actor_emotion_modifier.happiness = (actor_emotion_modifier.happiness + amount).clamp(-100.0, 100.0),
                        "stress" => actor_emotion_modifier.stress = (actor_emotion_modifier.stress + amount).clamp(0.0, 100.0),
                        _ => {}
                    }
                }
                CommandType::PlayAnimation => {
                    let anim_name = cmd.payload.get("animation_name").cloned().unwrap_or_else(|| "default".to_string());
                    let normalized = anim_name.to_lowercase();
                    let speed = cmd.payload.get("speed").and_then(|v| v.parse::<f32>().ok());
                    let loop_override = cmd.payload.get("loop").and_then(|v| v.parse::<bool>().ok());
                    let next_anim = cmd.payload.get("next_animation").cloned();

                    if let Ok((_, _, _, _, mut maybe_animator, maybe_ai_state, _, _, _, _, _, _, _, _, _)) = queries.p0().get_mut(bevy_entity) {
                        if let Some(ref mut animator) = maybe_animator {
                            if animator.animations.contains_key(&normalized) {
                                crate::render::switch_animation(animator, &normalized);
                                animator.manual_override = true;
                                if let Some(ai_state) = maybe_ai_state {
                                    animator.ai_action_at_override = ai_state.current_action.clone();
                                }
                                if let Some(s) = speed {
                                    animator.speed = s;
                                }
                                if let Some(l) = loop_override {
                                    if let Some(def) = animator.animations.get_mut(&normalized) {
                                        def.loop_anim = l;
                                    }
                                }
                                if let Some(next) = next_anim {
                                    animator.next_animation = Some(next);
                                }
                            } else {
                                warn!("PlayAnimation command received unknown animation name: {}", normalized);
                            }
                        }
                    }
                }
                CommandType::Speak => {
                    let sound_name = cmd.payload.get("sound").cloned().unwrap_or_else(|| "cry".to_string());
                    message_writer.write(crate::audio::PlaySoundEvent { name: sound_name });

                    let text = cmd.payload.get("text").cloned().unwrap_or_default();
                    if !text.is_empty() {
                        commands.spawn((
                            FloatingText {
                                velocity: Vec2::new(0.0, 30.0),
                                lifetime: 0.0,
                                max_lifetime: 2.0,
                            },
                            Text::new(text),
                            TextColor(Color::srgb(0.9, 0.9, 0.95)),
                            TextFont {
                                font_size: FontSize::Px(16.0),
                                ..default()
                            },
                            Transform::from_translation(a_pos + Vec3::new(0.0, 30.0, 1.5)),
                        ));
                    }
                }
                CommandType::Interact => {
                    let target_id_str = cmd.payload.get("target_id").cloned().unwrap_or_default();
                    let action = cmd.payload.get("action").cloned().unwrap_or_default();
                    let consume = cmd.payload.get("consume")
                        .and_then(|v| v.parse::<bool>().ok())
                        .unwrap_or(false);

                    if let Ok(target_u32) = target_id_str.parse::<u32>() {
                        if let Some(&target_entity) = entity_registry.0.get(&target_u32) {
                            let mut item_consumed = false;
                            
                            if let Ok((item_ent, item_stats, item_trans)) = queries.p1().get_mut(target_entity) {
                                let dist = a_pos.truncate().distance(item_trans.translation.truncate());
                                if dist <= 110.0 {
                                    item_consumed = true;
                                    if consume {
                                        let initial_hunger = a_needs.hunger;
                                        if item_stats.nutrition > 0.0 {
                                            actor_needs_modifier.hunger = (a_needs.hunger - item_stats.nutrition).clamp(0.0, 100.0);
                                            actor_needs_modifier.bladder = (a_needs.bladder + item_stats.nutrition * 0.5).clamp(0.0, 100.0);

                                            let mut fun_gain = item_stats.fun;
                                            if let Some(ref ystats) = a_ystats {
                                                let mut tastebud_spoiled_val = ystats.tastebud_spoiled;
                                                if tastebud_spoiled_val > 0.0 && item_stats.quality < tastebud_spoiled_val {
                                                    let base_mult = (item_stats.quality / tastebud_spoiled_val).clamp(0.0, 1.0);
                                                    let mut multiplier = base_mult;
                                                    if initial_hunger >= 50.0 {
                                                        let hunger_factor = ((initial_hunger - 50.0) / 30.0).clamp(0.0, 1.0);
                                                        multiplier = base_mult + (1.0 - base_mult) * hunger_factor;
                                                    }
                                                    fun_gain = item_stats.fun * multiplier;
                                                    if multiplier < 0.99 && item_stats.fun > 0.0 {
                                                        commands.spawn((
                                                            FloatingText {
                                                                velocity: Vec2::new(0.0, 50.0),
                                                                lifetime: 0.0,
                                                                max_lifetime: 1.5,
                                                            },
                                                            Text::new(format!("Tastes bland... (+{} Happy)", fun_gain as i32)),
                                                            TextColor(Color::srgb(0.78, 0.58, 0.58)),
                                                            TextFont {
                                                                font_size: FontSize::Px(20.0),
                                                                ..default()
                                                            },
                                                            Transform::from_translation(a_pos + Vec3::new(0.0, 20.0, 1.0)),
                                                        ));
                                                    }
                                                }
                                                tastebud_spoiled_val = tastebud_spoiled_val.max(item_stats.quality);
                                                actor_tastebud_spoiled_val = Some(tastebud_spoiled_val);
                                            }

                                            if fun_gain > 0.0 {
                                                actor_emotion_modifier.happiness = (a_emotion.happiness + fun_gain).clamp(-100.0, 100.0);
                                            }
                                        }

                                        if item_stats.comfort > 0.0 {
                                            actor_needs_modifier.energy = (a_needs.energy + item_stats.comfort).clamp(0.0, 100.0);
                                        }

                                        if let Some(config) = item_registry.items.get(&item_stats.type_id) {
                                            if let Some(ref obs_type) = config.obstacle_type {
                                                if obs_type == "HIGH" {
                                                    if let Some(ref mut ns) = nav_service {
                                                        {
                                                            let mut grid = ns.grid.write().unwrap();
                                                            grid.update_obstacle_rect(
                                                                item_trans.translation.x,
                                                                item_trans.translation.y,
                                                                config.width as f32,
                                                                config.height as f32,
                                                                false,
                                                                5,
                                                            );
                                                        }
                                                        let _ = ns.request_tx.send(crate::simulation::hpa::NavCommand::RebuildAll);
                                                    }
                                                }
                                            }
                                        }

                                        if let Some(ref mut writer) = xp_writer {
                                            writer.write(crate::simulation::skills::AddXpEvent {
                                                entity: actor_ent,
                                                skill_id: "scavenging".to_string(),
                                                amount: 5.0,
                                            });
                                        }

                                        message_writer.write(crate::audio::PlaySoundEvent { name: "eat".to_string() });
                                        commands.entity(item_ent).despawn();
                                    } else {
                                        // Non-consuming interaction: apply fun (happiness)
                                        if item_stats.fun > 0.0 {
                                            actor_emotion_modifier.happiness = (a_emotion.happiness + item_stats.fun).clamp(-100.0, 100.0);
                                        }
                                    }
                                }
                            }

                            if !item_consumed {
                                if let Ok((target_ent, mut t_needs, mut t_emotion, t_stats, t_trans, t_sid, t_pers, mut t_reg, mut t_gossip)) = queries.p2().get_mut(target_entity) {
                                    let is_predator = a_pred.is_some();
                                    if is_predator && action == "DEFAULT" {
                                        let dist = a_pos.truncate().distance(t_trans.translation.truncate());
                                        if dist <= 110.0 {
                                            let actor_agility = a_ystats.as_ref().map(|s| s.agility).unwrap_or(1.0);
                                            let target_agility = t_stats.agility;

                                            if target_agility > actor_agility * 1.5 {
                                                commands.spawn((
                                                    FloatingText {
                                                        velocity: Vec2::new(0.0, 50.0),
                                                        lifetime: 0.0,
                                                        max_lifetime: 1.2,
                                                    },
                                                    Text::new("Miss!".to_string()),
                                                    TextColor(Color::srgb(0.8, 0.8, 0.8)),
                                                    TextFont {
                                                        font_size: FontSize::Px(20.0),
                                                        ..default()
                                                    },
                                                    Transform::from_translation(t_trans.translation + Vec3::new(0.0, 20.0, 1.0)),
                                                ));
                                            } else {
                                                let dps = a_pred.as_ref().map(|p| p.dps).unwrap_or(20.0);
                                                let damage = dps * time.delta_secs();
                                                t_needs.health = (t_needs.health - damage).clamp(0.0, t_needs.max_health);

                                                if t_needs.health <= 0.0 {
                                                    commands.entity(target_ent).despawn();
                                                    actor_needs_modifier.hunger = (a_needs.hunger - 50.0).clamp(0.0, 100.0);
                                                    message_writer.write(crate::audio::PlaySoundEvent { name: "eat".to_string() });
                                                }
                                            }
                                        }
                                    } else {
                                        if let Some(interaction) = interaction_registry.interactions.get(&action) {
                                            let now = time_elapsed.elapsed;
                                            let base_compat = {
                                                let diff_kind = (a_pers.kindness - t_pers.kindness).abs();
                                                let diff_ener = (a_pers.energy - t_pers.energy).abs();
                                                let diff_brav = (a_pers.bravery - t_pers.bravery).abs();
                                                let diff_gree = (a_pers.greed - t_pers.greed).abs();
                                                let total_diff = diff_kind + diff_ener + diff_brav + diff_gree;
                                                let mut compat = 100.0 - (total_diff as f32 / 4.0);
                                                
                                                for my_trait in &a_pers.traits {
                                                    if let Some(td) = trait_registry.traits.get(my_trait) {
                                                        if let Some(ref social_mods) = td.social_modifiers {
                                                            if let Some(ref comp_map) = social_mods.compatibility {
                                                                for other_trait in &t_pers.traits {
                                                                    if let Some(&val) = comp_map.get(other_trait) {
                                                                        compat += val;
                                                                    }
                                                                }
                                                            }
                                                        }
                                                    }
                                                }
                                                compat
                                            };
                                            let mut a_d_affinity = interaction.social_impact.get("affinity").copied().unwrap_or(0.0);
                                            let mut a_d_trust = interaction.social_impact.get("trust").copied().unwrap_or(0.0);
                                            let mut a_d_fear = interaction.social_impact.get("fear").copied().unwrap_or(0.0);
                                            let a_d_familiarity = interaction.social_impact.get("familiarity").copied().unwrap_or(0.0);

                                            for trait_name in &a_pers.traits {
                                                let mod_key = format!("trait:{}", trait_name);
                                                if let Some(mods) = interaction.modifiers.get(&mod_key) {
                                                    a_d_affinity += mods.get("affinity").copied().unwrap_or(0.0);
                                                    a_d_trust += mods.get("trust").copied().unwrap_or(0.0);
                                                    a_d_fear += mods.get("fear").copied().unwrap_or(0.0);
                                                }
                                            }
                                            let a_mult = if interaction.base_impact > 0.0 {
                                                (1.0 + (a_pers.kindness as f32 / 100.0)).max(0.1)
                                            } else if interaction.base_impact < 0.0 {
                                                (1.0 - (a_pers.kindness as f32 / 100.0)).max(0.1)
                                            } else {
                                                1.0
                                            };
                                            a_d_affinity *= a_mult;
                                            a_d_trust *= a_mult;
                                            if interaction.base_impact < 0.0 {
                                                a_d_fear *= a_mult;
                                            }
                                            actor_relationship_update = Some((t_sid.0, base_compat, a_d_trust, a_d_fear, a_d_familiarity, a_d_affinity, action.clone()));

                                            // Target's relationship updates (bidirectional impact)
                                            let mut t_d_affinity = interaction.social_impact.get("affinity").copied().unwrap_or(0.0);
                                            let mut t_d_trust = interaction.social_impact.get("trust").copied().unwrap_or(0.0);
                                            let mut t_d_fear = interaction.social_impact.get("fear").copied().unwrap_or(0.0);
                                            let t_d_familiarity = interaction.social_impact.get("familiarity").copied().unwrap_or(0.0);

                                            for trait_name in &t_pers.traits {
                                                let mod_key = format!("trait:{}", trait_name);
                                                if let Some(mods) = interaction.modifiers.get(&mod_key) {
                                                    t_d_affinity += mods.get("affinity").copied().unwrap_or(0.0);
                                                    t_d_trust += mods.get("trust").copied().unwrap_or(0.0);
                                                    t_d_fear += mods.get("fear").copied().unwrap_or(0.0);
                                                }
                                            }
                                            let t_mult = if interaction.base_impact > 0.0 {
                                                (1.0 + (t_pers.kindness as f32 / 100.0)).max(0.1)
                                            } else if interaction.base_impact < 0.0 {
                                                (1.0 - (t_pers.kindness as f32 / 100.0)).max(0.1)
                                            } else {
                                                1.0
                                            };
                                            t_d_affinity *= t_mult;
                                            t_d_trust *= t_mult;
                                            if interaction.base_impact < 0.0 {
                                                t_d_fear *= t_mult;
                                            }

                                            if !t_reg.relationships.contains_key(&a_stable_id) {
                                                let mut new_rel = RelationshipData::new(now);
                                                new_rel.base_compatibility = base_compat;
                                                new_rel.affinity = base_compat;
                                                t_reg.relationships.insert(a_stable_id, new_rel);
                                            }
                                            if let Some(rel) = t_reg.relationships.get_mut(&a_stable_id) {
                                                rel.last_update = now;
                                                rel.adjust_trust(t_d_trust);
                                                rel.adjust_fear(t_d_fear);
                                                rel.familiarity = (rel.familiarity + t_d_familiarity).clamp(0.0, 100.0);
                                                social_counter.0 += 1;
                                                let headline = MemoryHeadline {
                                                    id: social_counter.0,
                                                    timestamp: now,
                                                    importance: 10.0,
                                                    sentiment: t_d_affinity,
                                                    event_type: action.clone(),
                                                    is_locked: false,
                                                };
                                                rel.add_headline(headline, 50.0);
                                            }
                                            t_gossip.add_packet(GossipPacket {
                                                target_id: a_stable_id,
                                                event_type: action.clone(),
                                                value: 10.0,
                                                timestamp: now,
                                            });

                                            if interaction.base_impact < -15.0 {
                                                actor_emotion_modifier.happiness = (a_emotion.happiness - 20.0).clamp(-100.0, 100.0);
                                                actor_emotion_modifier.stress = (a_emotion.stress + 20.0).clamp(0.0, 100.0);
                                            } else if interaction.base_impact > 15.0 {
                                                actor_emotion_modifier.happiness = (a_emotion.happiness + 20.0).clamp(-100.0, 100.0);
                                            }
                                            if interaction.base_impact < -15.0 {
                                                t_emotion.happiness = (t_emotion.happiness - 20.0).clamp(-100.0, 100.0);
                                                t_emotion.stress = (t_emotion.stress + 20.0).clamp(0.0, 100.0);
                                            } else if interaction.base_impact > 15.0 {
                                                t_emotion.happiness = (t_emotion.happiness + 20.0).clamp(-100.0, 100.0);
                                            }
                                            let apply_phys = |needs: &mut Needs, emotional: &mut EmotionalState, impact: &HashMap<String, f32>| {
                                                if let Some(&val) = impact.get("health") { needs.health = (needs.health + val).clamp(0.0, needs.max_health); }
                                                if let Some(&val) = impact.get("hunger") { needs.hunger = (needs.hunger + val).clamp(0.0, 100.0); }
                                                if let Some(&val) = impact.get("social") { needs.social = (needs.social + val).clamp(0.0, 100.0); }
                                                if let Some(&val) = impact.get("energy") { needs.energy = (needs.energy + val).clamp(0.0, 100.0); }
                                                if let Some(&val) = impact.get("cleanliness") { needs.cleanliness = (needs.cleanliness + val).clamp(0.0, 100.0); }
                                                if let Some(&val) = impact.get("bladder") { needs.bladder = (needs.bladder + val).clamp(0.0, 100.0); }
                                                if let Some(&val) = impact.get("easiness") { needs.easiness = (needs.easiness + val).clamp(0.0, 100.0); }
                                                if let Some(&val) = impact.get("happiness") { emotional.happiness = (emotional.happiness + val).clamp(-100.0, 100.0); }
                                                if let Some(&val) = impact.get("stress") { emotional.stress = (emotional.stress + val).clamp(0.0, 100.0); }
                                            };
                                            apply_phys(&mut actor_needs_modifier, &mut actor_emotion_modifier, &interaction.actor_physical_impact);
                                            apply_phys(&mut actor_needs_modifier, &mut actor_emotion_modifier, &interaction.physical_impact);
                                            apply_phys(&mut t_needs, &mut t_emotion, &interaction.target_physical_impact);
                                            apply_phys(&mut t_needs, &mut t_emotion, &interaction.physical_impact);
                                            let sound_name = match action.as_str() {
                                                "Talk" | "Greet" | "Chat" => "talk",
                                                "Fight" | "Hit" => "hit",
                                                "Dance" => "jump",
                                                _ => "",
                                            };
                                            if !sound_name.is_empty() {
                                                message_writer.write(crate::audio::PlaySoundEvent { name: sound_name.to_string() });
                                            }
                                            gossip_writer.write(GossipEvent {
                                                initiator_entity: actor_ent,
                                                target_entity: target_ent,
                                                initiator_stable_id: a_stable_id,
                                                target_stable_id: t_sid.0,
                                                position: a_pos.truncate(),
                                                range_type: interaction.range_type.clone().unwrap_or_else(|| "visual".to_string()),
                                                event_type: action.clone(),
                                            });
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                CommandType::Attack => {
                    let target_id_str = cmd.payload.get("target_id").cloned().unwrap_or_default();
                    if let Ok(target_u32) = target_id_str.parse::<u32>() {
                        if let Some(&target_entity) = entity_registry.0.get(&target_u32) {
                            if let Ok((target_ent, mut t_needs, _t_emotion, t_stats, t_trans, _t_sid, _t_pers, _, _)) = queries.p2().get_mut(target_entity) {
                                let dist = a_pos.truncate().distance(t_trans.translation.truncate());
                                if dist <= 110.0 {
                                    let actor_agility = a_ystats.as_ref().map(|s| s.agility).unwrap_or(1.0);
                                    let target_agility = t_stats.agility;

                                    if target_agility > actor_agility * 1.5 {
                                        commands.spawn((
                                            FloatingText {
                                                velocity: Vec2::new(0.0, 50.0),
                                                lifetime: 0.0,
                                                max_lifetime: 1.2,
                                            },
                                            Text::new("Miss!".to_string()),
                                            TextColor(Color::srgb(0.8, 0.8, 0.8)),
                                            TextFont {
                                                font_size: FontSize::Px(20.0),
                                                ..default()
                                            },
                                            Transform::from_translation(t_trans.translation + Vec3::new(0.0, 20.0, 1.0)),
                                        ));
                                    } else {
                                        let dps = a_pred.as_ref().map(|p| p.dps).unwrap_or(20.0);
                                        let damage = dps * time.delta_secs();
                                        t_needs.health = (t_needs.health - damage).clamp(0.0, t_needs.max_health);

                                        if t_needs.health <= 0.0 {
                                            commands.entity(target_ent).despawn();
                                            actor_needs_modifier.hunger = (a_needs.hunger - 50.0).clamp(0.0, 100.0);
                                            message_writer.write(crate::audio::PlaySoundEvent { name: "eat".to_string() });
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // 3. Re-borrow actor mutably and apply all modifications!
            if let Ok((_, mut mut_needs, mut mut_emotion, mut mut_velocity, _, _, _, _, mut mut_reg, mut mut_gossip, _, mut mut_ystats, _, _, _)) = queries.p0().get_mut(bevy_entity) {
                *mut_needs = actor_needs_modifier;
                *mut_emotion = actor_emotion_modifier;

                if let Some(vel) = actor_velocity_modifier {
                    mut_velocity.0 = vel;
                }

                if let Some(t_spoiled) = actor_tastebud_spoiled_val {
                    if let Some(ref mut ystats) = mut_ystats.as_mut() {
                        ystats.tastebud_spoiled = t_spoiled;
                    }
                }

                if let Some((t_stable_id, base_compat, a_d_trust, a_d_fear, a_d_familiarity, a_d_affinity, event_action)) = actor_relationship_update {
                    let now = time_elapsed.elapsed;
                    if !mut_reg.relationships.contains_key(&t_stable_id) {
                        let mut new_rel = RelationshipData::new(now);
                        new_rel.base_compatibility = base_compat;
                        new_rel.affinity = base_compat;
                        mut_reg.relationships.insert(t_stable_id, new_rel);
                    }
                    if let Some(rel) = mut_reg.relationships.get_mut(&t_stable_id) {
                        rel.last_update = now;
                        rel.adjust_trust(a_d_trust);
                        rel.adjust_fear(a_d_fear);
                        rel.familiarity = (rel.familiarity + a_d_familiarity).clamp(0.0, 100.0);
                        social_counter.0 += 1;
                        let headline = MemoryHeadline {
                            id: social_counter.0,
                            timestamp: now,
                            importance: 10.0,
                            sentiment: a_d_affinity,
                            event_type: event_action.clone(),
                            is_locked: false,
                        };
                        rel.add_headline(headline, 50.0);
                    }
                    mut_gossip.add_packet(GossipPacket {
                        target_id: t_stable_id,
                        event_type: event_action,
                        value: 10.0,
                        timestamp: now,
                    });
                }
            }
        }
    }
}

fn rotate_vec2(v: Vec2, angle_rad: f32) -> Vec2 {
    let cos = angle_rad.cos();
    let sin = angle_rad.sin();
    Vec2::new(v.x * cos - v.y * sin, v.x * sin + v.y * cos)
}

/// Bevy system to drive entities toward their `MoveTarget` each frame.
///
/// Applies steering forces: Seek/Arrival, Separation (avoiding neighbors),
/// and Obstacle Avoidance (avoiding static walls). Detects stuck entities
/// and triggers jitter or repathing.
pub fn move_target_steering_system(
    mut commands: Commands,
    time: Res<Time>,
    spatial_query: avian2d::prelude::SpatialQuery,
    nav_service: Option<Res<crate::simulation::hpa::NavigationService>>,
    mut query: Query<(
        Entity,
        &Transform,
        &MoveTarget,
        &SteeringConfig,
        &BaseColliderRadius,
        &mut avian2d::prelude::LinearVelocity,
        Option<&Flight>,
        Option<&crate::simulation::navigation::MovementPath>,
        Option<&mut StuckDetector>,
    )>,
    query_all_obstacles: Query<&avian2d::prelude::RigidBody>,
    query_neighbors: Query<(Entity, &Transform, &BaseColliderRadius)>,
) {
    let dt = time.delta_secs();
    if dt <= 0.0 {
        return;
    }

    // 1. Collect all entity positions and radii for separation force
    let entities_positions: Vec<(Entity, Vec2, f32)> = query_neighbors
        .iter()
        .map(|(ent, trans, radius)| (ent, trans.translation.truncate(), radius.0))
        .collect();

    for (entity, transform, move_target, steering, radius, mut velocity, maybe_flight, maybe_path, maybe_stuck) in query.iter_mut() {
        let current_pos = transform.translation.truncate();
        let delta = move_target.position - current_pos;
        let dist = delta.length();

        if dist <= move_target.acceptance_radius {
            // Arrived: remove MoveTarget.
            commands.entity(entity).remove::<MoveTarget>();
            velocity.0 = Vec2::ZERO;

            if maybe_stuck.is_some() {
                commands.entity(entity).remove::<StuckDetector>();
            }
            continue;
        }

        // 2. Desired velocity (Seek / Arrival Deceleration)
        let seek_dir = delta.normalize_or_zero();
        let speed = if dist < steering.arrival_radius && steering.arrival_radius > 0.0 {
            steering.max_speed * (dist / steering.arrival_radius).clamp(0.1, 1.0)
        } else {
            steering.max_speed
        };
        let mut steering_force = seek_dir * speed - velocity.0;

        // 3. Separation Force (Avoid other units)
        let mut separation_force = Vec2::ZERO;
        let self_radius = radius.0;
        for &(other_ent, other_pos, other_radius) in &entities_positions {
            if other_ent == entity {
                continue;
            }
            let diff = current_pos - other_pos;
            let distance = diff.length();
            let min_dist = self_radius + other_radius + 20.0;
            if distance < min_dist && distance > 0.0 {
                let force_factor = (min_dist - distance) / min_dist;
                separation_force += diff.normalize() * force_factor * steering.max_force * 1.5;
            }
        }
        steering_force += separation_force;

        // 4. Obstacle Avoidance Force (Avoid static walls)
        let is_flying = maybe_flight.map(|f| f.flight_state == FLIGHT_STATE_FLYING || f.flight_state == FLIGHT_STATE_HOVERING).unwrap_or(false);
        let obstacle_mask = if is_flying {
            avian2d::prelude::LayerMask::from(crate::simulation::mount::GameLayer::HighObstacle)
        } else {
            avian2d::prelude::LayerMask::from(crate::simulation::mount::GameLayer::HighObstacle) | avian2d::prelude::LayerMask::from(crate::simulation::mount::GameLayer::LowObstacle)
        };

        let filter = avian2d::prelude::SpatialQueryFilter::default()
            .with_excluded_entities(vec![entity])
            .with_mask(obstacle_mask);

        let look_ahead = 75.0;
        let forward_dir = velocity.0.normalize_or_zero();
        let ray_dir = if forward_dir.length_squared() > 0.01 {
            forward_dir
        } else {
            seek_dir
        };

        if ray_dir.length_squared() > 0.01 {
            let left_dir = rotate_vec2(ray_dir, 30.0f32.to_radians());
            let right_dir = rotate_vec2(ray_dir, -30.0f32.to_radians());

            let mut avoidance_force = Vec2::ZERO;
            
            for &dir in &[ray_dir, left_dir, right_dir] {
                if let Ok(dir2d) = Dir2::new(dir) {
                    let hits = spatial_query.ray_hits(
                        current_pos,
                        dir2d,
                        look_ahead,
                        1,
                        true,
                        &filter,
                    );
                    if let Some(hit) = hits.first() {
                        if let Ok(body) = query_all_obstacles.get(hit.entity) {
                            if matches!(body, avian2d::prelude::RigidBody::Static) {
                                let force_factor = (look_ahead - hit.distance) / look_ahead;
                                avoidance_force += hit.normal * force_factor * steering.max_force * 2.0;
                            }
                        }
                    }
                }
            }
            steering_force += avoidance_force;
        }

        // Apply forces
        let new_velocity = velocity.0 + steering_force * dt;
        velocity.0 = new_velocity.clamp_length_max(steering.max_speed);

        // 5. Stuck Detection and Repathing
        if let Some(mut stuck) = maybe_stuck {
            let moved = current_pos.distance(stuck.last_pos);
            stuck.last_pos = current_pos;

            if moved < 2.0 * dt {
                stuck.stuck_timer += dt;
                stuck.repath_timer += dt;

                if stuck.stuck_timer >= 1.0 {
                    let jitter = Vec2::new(
                        rand::random::<f32>() - 0.5,
                        rand::random::<f32>() - 0.5,
                    ).normalize_or_zero() * steering.max_speed * 0.5;
                    velocity.0 += jitter;
                    stuck.stuck_timer = 0.0;
                }

                if stuck.repath_timer >= 3.0 {
                    stuck.repath_timer = 0.0;
                    if let Some(path) = maybe_path {
                        if let Some(&destination) = path.waypoints.last() {
                            if let Some(ref ns) = nav_service {
                                let grid_read = ns.grid.read().unwrap();
                                let start_grid = grid_read.to_grid(current_pos);
                                let end_grid = grid_read.to_grid(destination);
                                let capabilities = if is_flying {
                                    crate::simulation::hpa::TRAVERSAL_FLY
                                } else {
                                    crate::simulation::hpa::TRAVERSAL_WALK
                                };
                                let _ = ns.request_tx.send(crate::simulation::hpa::NavCommand::RequestPath(crate::simulation::hpa::PathRequest {
                                    entity_id: entity,
                                    start: start_grid,
                                    end: end_grid,
                                    capabilities,
                                    end_world: Some(destination),
                                }));
                            }
                        }
                    }
                }
            } else {
                stuck.stuck_timer = 0.0;
                stuck.repath_timer = 0.0;
            }
        } else {
            commands.entity(entity).insert(StuckDetector {
                last_pos: current_pos,
                stuck_timer: 0.0,
                repath_timer: 0.0,
            });
        }
    }
}


pub fn sync_yukkuri_animations(
    mut query: Query<(
        Entity,
        &AIState,
        Option<&Flight>,
        &mut crate::render::Animator,
        Option<&crate::simulation::lod::LODComponent>,
    )>,
    mut frame_counter: Local<u32>,
) {
    *frame_counter = frame_counter.wrapping_add(1);

    for (_entity, ai_state, maybe_flight, mut animator, maybe_lod) in query.iter_mut() {
        let lod_level = maybe_lod.map(|l| l.level).unwrap_or(0);
        if lod_level == 1 && *frame_counter % 2 != 0 {
            continue;
        }
        if lod_level == 2 && *frame_counter % 4 != 0 {
            continue;
        }
        if animator.manual_override {
            if ai_state.current_action != animator.ai_action_at_override {
                animator.manual_override = false;
            } else {
                continue;
            }
        }

        let mut target_anim = ai_state.current_action.to_lowercase();

        if let Some(flight) = maybe_flight {
            if flight.flight_state != FLIGHT_STATE_GROUNDED {
                if flight.flight_state == FLIGHT_STATE_SWOOPING {
                    target_anim = "swoop".to_string();
                } else {
                    target_anim = "fly".to_string();
                }
            }
        }

        if animator.animations.contains_key(&target_anim) {
            crate::render::switch_animation(&mut animator, &target_anim);
        }
    }
}

pub fn cleanup_ffi_cache_system(
    mut removed: RemovedComponents<PythonState>,
    sandbox: Option<NonSend<PythonAISandbox>>,
) {
    let Some(sandbox) = sandbox else { return; };
    Python::with_gil(|py| {
        for entity in removed.read() {
            let entity_id = entity.index_u32();
            if let Err(e) = sandbox.cleanup_entity(py, entity_id) {
                error!("Failed to cleanup Python BT cache for entity {}: {:?}", entity_id, e);
            }
        }
    });
}

/// Plugin to register AI components, systems, and Python FFI resource.
///
/// `WorldSettings` must be inserted **before** this plugin is added so that
/// the AI tick system reads the correct world dimensions.  Call
/// [`load_world_settings`] in `main` and use `app.insert_resource(settings)`
/// prior to `add_plugins(AIPlugin)`.
pub struct AIPlugin;

impl Plugin for AIPlugin {
    fn build(&self, app: &mut App) {
        app.add_systems(Update, cleanup_ffi_cache_system);
        let sandbox = Python::with_gil(|py| {
            PythonAISandbox::new(py).expect("Failed to initialize Python AI Sandbox")

        });

        // Only insert WorldSettings default if the caller did not already
        // provide one (insert_resource would overwrite; init_resource skips).
        app
            .insert_non_send(sandbox)
            .init_resource::<WorldSettings>()
            .init_resource::<PoppedCommands>()
            .init_resource::<EntityRegistry>()
            .init_resource::<SocialIdCounter>()
            .init_resource::<persistence::TimeElapsed>()
            .add_message::<crate::audio::PlaySoundEvent>()
            .add_message::<GossipEvent>()
            .register_type::<Needs>()
            .register_type::<YukkuriStats>()
            .register_type::<Dead>()
            .register_type::<BaseColliderRadius>()
            .register_type::<EmotionalState>()
            .register_type::<AIState>()
            .register_type::<StableId>()
            .register_type::<Flight>()
            .register_type::<SteeringConfig>()
            .register_type::<MoveTarget>()
            .register_type::<StuckDetector>()
            .register_type::<Persistable>()
            .register_type::<PythonState>()
            .register_type::<Personality>()
            .register_type::<RelationshipRegistry>()
            .register_type::<GossipQueue>()
            .register_type::<crate::simulation::skills::Skills>()
            .register_type::<crate::simulation::mount::Mount>()
            .register_type::<crate::simulation::mount::PendingDismount>()
            .register_type::<crate::simulation::inventory::InventoryComponent>()
            .register_type::<crate::simulation::inventory::ItemStack>()
            .register_type::<crate::simulation::inventory::InventoryPickupRequest>()
            .register_type::<crate::simulation::inventory::InventoryDropRequest>()
            .register_type::<crate::simulation::inventory::ItemStats>()
            .register_type::<crate::simulation::movement::MovementController>()
            .register_type::<crate::simulation::navigation::MovementPath>()
            .register_type::<persistence::TimeElapsed>()
            .register_type::<Predator>()
            .register_type::<crate::simulation::lod::LODComponent>()
            .add_systems(
                Update,
                (
                    // 1. Spatial perception: populate VisibleTargets from distance checks.
                    populate_visible_targets_system,
                    // 2. AI tick: build blackboards and dispatch Python behavior trees.
                    tick_python_ai_system,
                    // 3. Command apply: translate Python commands into ECS mutations.
                    apply_ai_commands,
                    // 4. Steering: consume MoveTarget and set LinearVelocity.
                    move_target_steering_system,
                    // 5. Animation sync: keep sprite state consistent with AI action.
                    sync_yukkuri_animations,
                ).chain(),
            );
    }
}
