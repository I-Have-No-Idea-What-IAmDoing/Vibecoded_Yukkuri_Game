# Scope: E2E Simulation Test Suite

This scope document outlines the opaque-box end-to-end testing milestones for the biological, social, and environmental simulation systems, following the 4-tier testing methodology.

## Architecture & Test Harness
- **Test Runner**: Pytest (`scripts/test.py` / `pytest`)
- **Execution Mode**: Headless integration tests using `GameDriver` from `yukkuri_game.testing.driver`.
- **Target Interface**: Opaque-box interaction via ECS World operations, event dispatching, player commands, and state assertions on standard components (`Needs`, `YukkuriStats`, `Blackboard`, `EmotionalState`, `Skills`, etc.).

## Milestones

| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Biology & Metabolism Tests | Tier 1-4 tests for Need Decay, Metabolism, Waste, Lifecycle, and Breeding features. | None | PLANNED |
| 2 | Social & Personality Tests | Tier 1-4 tests for Proximity, opinion, Gossip, Traits, and Skills features. | Milestone 1 | PLANNED |
| 3 | Environment & Feedback Tests | Tier 1-4 tests for Time, Day/Night cycle, Darkness stress, Cursor lights, and Audio/Visual Feedback features. | Milestone 1 | PLANNED |
| 4 | Real-World Workload Scenarios | Tier 4 E2E compound scenarios tying biology, social, environment together. | Milestone 1, 2, 3 | PLANNED |

## E2E Feature Specifications & Test Plans

### 1. Need Decay & Metabolism
- **Tier 1 (Feature Coverage)**: Hunger, energy, cleanliness, social decay over time; bladder accumulation.
- **Tier 2 (Boundary & Corner)**: Clamping of needs at limits [0, 100], starvation damage when hunger reaches 100%, sleep recovery, eating recovery, health limits.
- **Tier 3 (Cross-Feature)**: Interaction between extreme hunger and low energy compounding happiness decay.
- **Tier 4 (Real-world)**: A Yukkuri experiences starvation, finds food, eats, heals, and falls asleep.

### 2. Waste & Cleanliness
- **Tier 1 (Feature Coverage)**: Bladder at 100% spawns poop, poop decays area cleanliness, poop presence decays nearby entities' cleanliness, clean command removes poop, clean command restores cleanliness.
- **Tier 2 (Boundary & Corner)**: No poop below bladder threshold, cleanliness decay drop-off with distance, compound poop decays, clean command bounds, low cleanliness triggering depression state.
- **Tier 3 (Cross-Feature)**: High bladder + sleep triggers dirty bed (bed cleanliness drops to 0, comfort ruined).
- **Tier 4 (Real-world)**: Bladder fills, poop spawns, area cleanliness drops, Yukkuri gets dirty/unhappy, player triggers clean command, Yukkuri recovers happiness.

### 3. Lifecycle & Growth
- **Tier 1 (Feature Coverage)**: Age ticking, Baby -> Child transition, Child -> Adult transition, scale factor increase, physics body collider and mass size updates.
- **Tier 2 (Boundary & Corner)**: No age ticking on pause, transition checks exactly at thresholds, safe spawning, collider scaling without overlap panics, age contribution to sell value.
- **Tier 3 (Cross-Feature)**: Need decay rates scaling with growth stage (Babies decay faster).
- **Tier 4 (Real-world)**: Spawning a Baby Yukkuri, feeding it, checking aging progression to Child and Adult, verifying transform scaling and collider expansion.

### 4. Breeding & Reproduction
- **Tier 1 (Feature Coverage)**: Happy/energetic adults breeding check, baby spawn, breeding stat depletion (happiness/energy consumption), baby inherits parent traits/type, baby placed collision-free.
- **Tier 2 (Boundary & Corner)**: Age constraints, happiness/energy thresholds, spiral search collision safety, breeding chance traits scaling.
- **Tier 3 (Cross-Feature)**: Multi-species breeding creating hybrid trait combinations.
- **Tier 4 (Real-world)**: High-state parent couple breeds, baby spawned safely nearby via spiral search, parent stats drop.

### 5. Proximity & Relationships
- **Tier 1 (Feature Coverage)**: Proximity detection of nearby entities, proximity benefits (happiness gain / stress drop) near family, relationship registration on birth, parent/child/mate tracking.
- **Tier 2 (Boundary & Corner)**: Radius boundaries, relationship registry limit protection, proximity penalties (stress gain) near enemies/threats, stress overriding family proximity benefits.
- **Tier 3 (Cross-Feature)**: Loneliness triggers active seek/wander towards friends/family.
- **Tier 4 (Real-world)**: Separated family members wander towards each other, meeting triggers proximity benefits.

### 6. Opinion & Gossip
- **Tier 1 (Feature Coverage)**: Witnessing events in radius generates gossip packets, interpersonal stats (affinity, trust, fear, familiarity) update on event, gossip transmission during conversation, opinion updates.
- **Tier 2 (Boundary & Corner)**: Gossip queue limits (cap at max length), memory locking for important events, core memory protection, witness radius boundaries, packet value decay.
- **Tier 3 (Cross-Feature)**: Gossip about threat/predator spreads, causing untargeted entities to flee.
- **Tier 4 (Real-world)**: Yukkuri A witnesses Yukkuri B being punished, gossips with Yukkuri C, who updates its fear relationship towards the player.

### 7. Traits & Skills
- **Tier 1 (Feature Coverage)**: Traits modifying need decay rates, traits affecting BT action choices, skill XP tracking, scavenging/athletics level-up, passion/intelligence XP speed modifiers.
- **Tier 2 (Boundary & Corner)**: Skill level cap, skill XP scaling, skill level increases speed (Athletics) or item yield (Scavenging).
- **Tier 3 (Cross-Feature)**: Trait + Skill level combo (e.g. Hyper-active + high Athletics leads to massive wander distances and fast hunger decay).
- **Tier 4 (Real-world)**: Athletics-trait Yukkuri wanders, levels up skill, gains speed bonus.

### 8. Time, Environment & Feedback
- **Tier 1 (Feature Coverage)**: Virtual clock sync, day/night transitions, cursor lights, darkness stress, feedback crying/text, feedback audio sound events.
- **Tier 2 (Boundary & Corner)**: Day/night speed scaling, darkness boundaries, cursor light positioning, feedback triggers only at stress threshold.
- **Tier 3 (Cross-Feature)**: Day/Night cycle + Sleep behavior interaction (sleep triggers at night, high darkness stress without light).
- **Tier 4 (Real-world)**: Night falls, Yukkuri accumulates darkness stress, cries, player moves cursor light close, stress decreases, Yukkuri sleeps.
