# Project: Yukkuri Raising Game - Biological, Social, and Environmental Simulation Systems Port

## Architecture
- **Host Engine (Rust/Bevy)**: Runs the core loop, need decay, environmental lighting, day/night cycles, lifecycle transitions, movement physics, inventory, and player shop commands.
- **AI Agent (Python/PyO3)**: Executes Behavior Trees. Receives blackboard state from Rust (synced FFI structures) and returns Commands.
- **Simulation Sync**:
  - Rust tick systems mutate needs, age, proximity, and relationships.
  - Needs, traits, time, and visible targets are serialized/shared with Python.
  - Python commands (like MoveTo, Flee, PlayAnimation, Attack, Interact, ModifyStat) are parsed and executed in Rust systems.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Need Decay, Metabolism, and Waste | Tick systems for need decay (hunger, energy, social, cleanliness, bladder), starvation damage, poop spawning, spatial cleanliness drop, and clean commands. | None | COMPLETED |
| 2 | Lifecycle and Breeding | Age ticking (Baby -> Child -> Adult), scale and collider sizing adjustments, and adult breeding checks. | Milestone 1 | COMPLETED |
| 3 | Relationships, Gossip, Traits & Skills | Proximity benefits, gossip/opinion systems, trait need modifiers, and skill XP tracking. | Milestone 2 | COMPLETED |
| 4 | Physics, Inventory, Bobbing & Navigation | Mount/dismount search, inventory pickup/drop, flight state collision, navigation grid updates, and movement bobbing. | Milestone 1 | COMPLETED |
| 5 | Time, Environment & Feedback Systems | Clock sync, day/night cycle, cursor lights, darkness stress, cry/text/sound feedback. | Milestone 1 | COMPLETED |
| 6 | Player Shop, Commands & LOD | Sell, train, punish commands, shop item spawning, predation events, and LOD simulation throttling. | Milestone 4, 5 | COMPLETED |

## Interface Contracts
### Rust ↔ Python FFI (via PyO3)
- `Blackboard` will include:
  - Time details (day, hour_of_day, game_time).
  - Extended stats (traits, skill levels).
  - Relationships (family status, affinity, trust, fear, familiarity).
- `Command` types mapping:
  - `ModifyStat` / `Speak` / `Interact` / `Attack` commands translated from Python to mutate Rust components.
  - Shop items spawned via Bevy entities using preset TOML definitions.

## Code Layout
- `src/simulation/mod.rs` - Simulation parent module, registering systems.
- `src/simulation/needs.rs` - Need decay, poop spawning, and cleaning systems.
- `src/simulation/lifecycle.rs` - Aging, scale adjustment, and breeding systems.
- `src/simulation/social.rs` - Relationships, opinion/gossip propagation, and proximity checks.
- `src/simulation/skills.rs` - Skills and trait mechanics.
- `src/simulation/physics.rs` - Mount/dismount, inventory, flight collision, and navigation grid updates.
- `src/simulation/environment.rs` - Time, day/night cycle, lights, and audio-visual feedback.
- `src/simulation/player.rs` - Player command dispatcher (sell, train, punish), shop placement, and LOD throttling.
- `tests/simulation_tests.rs` - Integration test suite for all simulation systems.
