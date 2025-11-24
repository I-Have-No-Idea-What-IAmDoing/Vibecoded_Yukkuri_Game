# Implementation Tasks: Narrative Ecology System

This document outlines the roadmap for implementing the design in `DESIGN.md`.

## Phase 1: Foundation (Data & Components)
*Goal: Establish the new data structures without breaking the game loop.*

- [ ] **Create `Instincts` Component**
    - [ ] Define dataclass with `survival`, `social`, `assertion`, `cognition` (floats).
    - [ ] Implement randomization logic based on Yukkuri Type (e.g., Reimu vs Marisa).
- [ ] **Create `Hydraulics` Component**
    - [ ] Define dataclass with `stress`, `satisfaction`, `ego` (floats 0-100).
    - [ ] Add simple `update(dt)` method for natural decay.
- [ ] **Refactor `RelationshipData`**
    - [ ] Create `Impression` class.
    - [ ] Implement `key_memories` list (Fixed size 3).
    - [ ] Add `add_memory_event(event)` logic to handle the "High Score" replacement.

## Phase 2: The Emotional Loop
*Goal: Connect the new components to behavior.*

- [ ] **Implement `HydraulicSystem`**
    - [ ] Handle "Overflow" and "Empty" states (e.g., trigger "Panic" status if Stress > 90).
    - [ ] Connect `Interaction` events to Bucket fills (e.g., `Eat` -> `+Satisfaction`).
- [ ] **Visual Feedback**
    - [ ] Hook `Hydraulics` state to sprite overlays (Tears, Puffing up).

## Phase 3: Social & Memory
*Goal: Implement the "Ecology" aspect.*

- [ ] **Implement `SectorSystem`**
    - [ ] Divide map into grid.
    - [ ] Implement `get_witnesses(location)` using grid lookup.
- [ ] **Implement `GossipSystem`**
    - [ ] Create `GossipPacket` struct.
    - [ ] Add `gossip_queue` to Entity.
    - [ ] Create interaction: "Chat" -> Exchange Gossip.

## Phase 4: AI Integration
*Goal: Make them act on the new data.*

- [ ] **Update `DecisionSystem`**
    - [ ] Use `Instincts` to weight Utility AI scores.
    - [ ] Use `Impression` data to determine target viability (e.g., Don't ask for food from someone with High Fear).
- [ ] **Refactor Traits**
    - [ ] Convert `traits.toml` to use the new "Lens" system (e.g., `predator_lens` logic).

## Phase 5: Testing & Optimization
- [ ] **Performance Test:** Spawn 100 entities. Profile the `HydraulicSystem` and `SectorSystem`.
- [ ] **Unit Test:** Verify `add_memory_event` correctly keeps the top 3 impactful memories.
- [ ] **Unit Test:** Verify Gossip propagation speed.
