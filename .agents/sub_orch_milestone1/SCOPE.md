# Scope: Milestone 1: Need Decay, Metabolism, and Waste Simulation

## Architecture
- **Needs Decay System**: A Bevy update system that reduces Needs values over time (using `Res<Time>`). Needs are `hunger`, `energy`, `social`, `cleanliness`, and `bladder`.
- **Starvation Damage System**: A Bevy system checking if `Needs::hunger` is at 100.0 (or its maximum), and applying damage to `Needs::health` accordingly.
- **Poop Spawning System**: A Bevy system that ticks bladder levels, evaluates a chance-based check for spawning poop entities based on bladder and elapsed time, and instantiates Poop entities.
- **Cleanliness / Environment System**: Nearby entities' `cleanliness` is reduced due to proximity to Poop entities.
- **Player Cleaning Command**: A player command or system that cleans poop entities and restores cleanliness.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1.1 | Exploration & Analysis | Explore original Python behavior (e.g. branch `MVP_python`) for need decay rates, poop spawning chances, cleanliness dynamics, and cleaning. Identify how to integrate these into Bevy. | None | DONE |
| M1.2 | Need Decay & Starvation | Implement tick systems in Rust/Bevy for hunger, energy, social, cleanliness, bladder decay, and starvation damage at 100% hunger. | M1.1 | IN_PROGRESS |
| M1.3 | Poop Spawning & Proximity | Implement poop entity spawning (chance-based on bladder and time) and cleanliness reduction for nearby entities. | M1.2 | IN_PROGRESS |
| M1.4 | Player Cleaning | Support player cleaning commands / interactions to clean poops. | M1.3 | IN_PROGRESS |
| M1.5 | Integration & Verification | Write Rust integration tests to verify need decay, starvation damage, poop spawning, proximity cleanliness drop, and clean command. Verify with python test runner if applicable. | M1.4 | IN_PROGRESS |

## Interface Contracts
### Rust Needs Component
`Needs` struct includes fields: `health`, `hunger`, `social`, `energy`, `cleanliness`, `bladder`, `easiness`, `max_health`.
`Poop` entity should have location/transform.
`Clean` command modifies cleanliness or removes poop entities.
