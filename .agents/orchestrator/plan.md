# Project Plan: Biological, Social, and Environmental Simulation Systems Port

This plan details the implementation of biological, social, and environmental systems in Bevy/Rust, integrated with Bevy 0.19 and PyO3.

## Milestones

| # | Milestone Name | Description | Status |
|---|----------------|-------------|--------|
| 1 | Need Decay, Metabolism, and Waste | Tick systems for need decay (hunger, energy, social, cleanliness, bladder), starvation damage, poop spawning, spatial cleanliness drop, and clean commands. | PLANNED |
| 2 | Lifecycle and Breeding | Age ticking (Baby -> Child -> Adult), scale and collider sizing adjustments, and adult breeding checks. | PLANNED |
| 3 | Relationships, Gossip, Traits & Skills | Proximity benefits, gossip/opinion systems, trait need modifiers, and skill XP tracking. | PLANNED |
| 4 | Physics, Inventory, Bobbing & Navigation | Mount/dismount search, inventory pickup/drop, flight state collision, navigation grid updates, and movement bobbing. | PLANNED |
| 5 | Time, Environment & Feedback Systems | Clock sync, day/night cycle, cursor lights, darkness stress, cry/text/sound feedback. | PLANNED |
| 6 | Player Shop, Commands & LOD | Sell, train, punish commands, shop item spawning, predation events, and LOD simulation throttling. | PLANNED |

## Code & Data Layout
- `src/simulation/mod.rs` - Simulation parent module, registering systems.
- `src/simulation/needs.rs` - Need decay, poop spawning, and cleaning systems.
- `src/simulation/lifecycle.rs` - Aging, scale adjustment, and breeding systems.
- `src/simulation/social.rs` - Relationships, opinion/gossip propagation, and proximity checks.
- `src/simulation/skills.rs` - Skills and trait mechanics.
- `src/simulation/physics.rs` - Mount/dismount, inventory, flight collision, and navigation grid updates.
- `src/simulation/environment.rs` - Time, day/night cycle, lights, and audio-visual feedback.
- `src/simulation/player.rs` - Player command dispatcher (sell, train, punish), shop placement, and LOD throttling.
- `tests/simulation_tests.rs` - Integration test suite for all simulation systems.
