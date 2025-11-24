# Implementation Tasks: Proposal 3

## Phase 1: Data Structures (The Skeleton)
- [ ] **Create `PersonalityAxis` Component**
    - [ ] Fields: `kindness`, `energy`, `bravery`, `greed`. Range -100 to 100.
    - [ ] Method: `get_archetype()` returning string (e.g., "Scum", "Hero") for debug.
- [ ] **Create `EmotionalState` Component**
    - [ ] Fields: `happiness` (float), `stress` (float).
    - [ ] Method: `get_mood_quadrant()` returning Enum.
- [ ] **Create `MemoryBank` Component**
    - [ ] Define `Headline` struct/dataclass (Timestamp, Severity, Type, Impact).
    - [ ] Define `RelationshipEntry`:
        - [ ] `trivial_events`: Circular Buffer (Size 25).
        - [ ] `core_memories`: List/Buffer (Size 35) with Locking support.
    - [ ] Method: `lock_memory(headline)` logic.
- [ ] **Create `GossipQueue` Component**
    - [ ] Queue of `GossipPacket` objects.

## Phase 2: The Systems (The Muscle)
- [ ] **Implement `TraitSystem` (Lenses)**
    - [ ] Implement `apply_center_shift(axis, trait_value)`.
    - [ ] Implement `check_lens_override(trait, instinct_trigger)` -> returns Modified Trigger.
- [ ] **Implement `SectorSystem`**
    - [ ] **Grid Management:** Divide world into 4x4 Sectors.
    - [ ] **Entity Tracking:** Update entity sector membership on move.
    - [ ] **Broadcasting:** Implement `get_observers(visual=True/False, volume_level)`.
- [ ] **Implement `SocialSystem` (Refactor)**
    - [ ] **Gossip Exchange:** On interaction, sync top 3 Gossip Packets.
    - [ ] **Viral Logic:** Check if packet is "New" to the receiver before adding.
    - [ ] **Opinion Calc:** Sum Core Memories + Weighted Trivial Memories.

## Phase 3: Integration (The Brain)
- [ ] **Update AI Decision Making**
    - [ ] Replace old `if mood == "HAPPY"` checks with `if emotion.happiness > 0`.
    - [ ] Implement "Stress Breaks": If `stress > 90`, force a specialized behavior state.
- [ ] **Trait Data Migration**
    - [ ] Update `traits.toml` to use `center_shift` instead of `clamp`.
    - [ ] Define "Lens" tags for specific traits (Scum, Predator).

## Phase 4: Verification & UI
- [ ] **Debug Tools**
    - [ ] Add "Psychoanalysis" window: Shows 4 Axes + Lenses.
    - [ ] Add "Sector Viewer": Visualizes the 4x4 Grid and entity membership.
    - [ ] Add "Gossip Tracker": Logs flow of a specific Gossip Packet across the map.
- [ ] **Performance Test**
    - [ ] Spawn 100 entities.
    - [ ] Force gossip spread (one event spreads to all).
    - [ ] Verify propagation delay (should not be instant).

## Pre-Commit Checklist
- [ ] **Unit Tests:**
    - [ ] Test `MemoryBank` locking (ensure locked memories stick).
    - [ ] Test `SectorSystem` adjacency logic.
    - [ ] Test `GossipQueue` deduplication (don't accept same gossip twice).
- [ ] **Review:**
    - [ ] Verify Trait "Center Shift" allows values to exceed "nature" with input.
