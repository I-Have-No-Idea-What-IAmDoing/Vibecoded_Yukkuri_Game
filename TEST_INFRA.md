# E2E Test Infra: Vibecoded Yukkuri Game Simulation

## Test Philosophy
- Opaque-box, requirement-driven. The test suite verifies the biological, social, and environmental simulation systems without relying on or depending on Bevy/Rust host integration internals.
- Methodology: Category-Partition, Boundary Value Analysis, Pairwise Combinatorial Testing, and Real-World Workload Testing (Tiers 1-4).

## Feature Inventory
| # | Feature | Source (requirement) | Tier 1 | Tier 2 | Tier 3 |
|---|---------|---------------------|:------:|:------:|:------:|
| 1 | Need Decay & Metabolism | ORIGINAL_REQUEST §1 | 5 | 10 | ✓ |
| 2 | Waste & Cleanliness | ORIGINAL_REQUEST §2 | 5 | 5 | ✓ |
| 3 | Lifecycle & Growth | ORIGINAL_REQUEST §3 | 5 | 5 | ✓ |
| 4 | Breeding & Reproduction | ORIGINAL_REQUEST §4 | 5 | 5 | ✓ |
| 5 | Proximity & Relationships | ORIGINAL_REQUEST §5 | 5 | 5 | ✓ |
| 6 | Opinion & Gossip | ORIGINAL_REQUEST §6 | 5 | 5 | ✓ |
| 7 | Traits & Skills | ORIGINAL_REQUEST §7 | 5 | 5 | ✓ |
| 8 | Time, Environment & Feedback | ORIGINAL_REQUEST §8 | 5 | 5 | ✓ |

## Test Architecture
- **Test Runner**: Pytest (`scripts/test.py` / `pytest`) executed via UV environment wrapper (`uv run scripts/test.py -x --timeout=10 -q`).
- **Test Case Format**: Headless integration tests in Python utilizing the `GameDriver` harness. State queries are executed against Pygame-adapted components (`Needs`, `YukkuriStats`, `Blackboard`, etc.).
- **Directory Layout**:
  - `tests/integration/test_e2e.py`: Main opaque-box E2E test suite containing Tiers 1-4 tests (98 test cases).
  - `tests/systems/test_gossip_system.py`: Target unit/integration tests for the Gossip system including LoS obstacle/sensor handling.

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Complexity |
|---|----------|--------------------|------------|
| 1 | Starvation, Foraging, Healing, Sleeping | Metabolism, Hunger, AI Actions, Sleep | High |
| 2 | Waste and Cleanliness Cycle | Bladder, Poop Spawning, Area Decay, Player Commands | Medium |
| 3 | Reproduction, Growth, and Inherited Stats | Breeding, Lifecycle, Family Registration | High |
| 4 | Witness Abuse, Gossip, and Spread Fear | Opinion, Gossip Transmission, Relationships | High |
| 5 | Night Darkness Stress Cycle Negated by Light | Time, Day/Night, Cursor Light, Feedback | Medium |

## Coverage Thresholds
- Tier 1: 5 cases per feature (Total: 40 cases)
- Tier 2: ≥5 cases per feature (Total: 45 cases)
- Tier 3: Pairwise coverage of major feature interactions (Total: 8 cases)
- Tier 4: ≥5 realistic application scenarios (Total: 5 cases)
