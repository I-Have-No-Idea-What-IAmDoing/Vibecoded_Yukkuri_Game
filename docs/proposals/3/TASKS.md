# Implementation Tasks: Proposal 3

## Phase 1: Data Structures (The Skeleton)
- [ ] **Create `PersonalityAxis` Component**
    - [ ] Fields: `kindness` (int), `energy` (int), `bravery` (int), `greed` (int). Range -100 to 100.
    - [ ] Method: `get_archetype()` returning string (e.g., "Scum", "Hero") for debug.
- [ ] **Create `EmotionalState` Component**
    - [ ] Fields: `happiness` (float), `stress` (float).
    - [ ] Method: `get_mood_quadrant()` returning Enum (CONTENT, MANIC, DEPRESSED, RAGE).
- [ ] **Create `MemoryBank` Component**
    - [ ] Define `Headline` struct/dataclass (with `is_locked` flag).
    - [ ] Define `RelationshipEntry` holding `trivial_buffer` (Size 25) and `core_buffer` (Size 35).
    - [ ] Implement `lock_memory(headline_id)` logic.
- [ ] **Create `GossipQueue` Component**
    - [ ] Define `GossipPacket` struct.
    - [ ] Implement priority queue for top 3 packets.

## Phase 2: The Systems (The Muscle)
- [ ] **Implement `EmotionSystem`**
    - [ ] **Decay Logic:** Stress decays fast (returns to calm). Happiness decays slow (returns to neutral).
    - [ ] **Tuning:** Expose decay rates in a config file.
- [ ] **Implement `SocialSystem` (Refactor)**
    - [ ] **Compatibility Check:** Update to include `greed` axis.
    - [ ] **Headline Trigger:** Update interactions to emit "SocialEvents".
    - [ ] **Sector Broadcasting:** Implement spatial lookups (Quadtree or Grid) for visual/auditory events.
    - [ ] **Line-of-Sight:** Implement raycast check for Visual events.
- [ ] **Implement `GossipSystem`**
    - [ ] **Witness Logic:** Witness adds `GossipPacket` to own queue instead of direct reputation update.
    - [ ] **Exchange Logic:** Swap top 3 packets during `Chat` interaction.

## Phase 3: Integration (The Brain)
- [ ] **Update AI Decision Making**
    - [ ] Replace old `if mood == "HAPPY"` checks with `if emotion.happiness > 0`.
    - [ ] Implement "Stress Breaks": If `stress > 90`, force specialized behavior.
- [ ] **Trait Data Migration**
    - [ ] Update `traits.toml` to use **Center Shifts** instead of clamps.
    - [ ] Implement **Behavioral Overrides** system (Tags/Flags).
    - [ ] Add `Predator` and `Scum` examples.

## Phase 4: Verification & UI
- [ ] **Debug Tools**
    - [ ] Add "Psychoanalysis" window: Shows the 4 Axes and current Stress/Happiness graph.
    - [ ] Add "Memory Viewer": Shows Trivial and Core buffers, highlighting Locked memories.
    - [ ] Add "Gossip Tracker": Visualize the spread of a specific rumor on the map.
- [ ] **Performance Test**
    - [ ] Spawn 100 entities.
    - [ ] Force spam interactions.
    - [ ] Verify memory usage remains stable.
    - [ ] Verify Sector System culls updates correctly.

## Pre-Commit Checklist
- [ ] **Unit Tests:**
    - [ ] Test `MemoryBank` buffers and Locking logic.
    - [ ] Test `GossipQueue` priority logic.
    - [ ] Test `PersonalityAxis` center shifting.
- [ ] **Review:**
    - [ ] Verify no hardcoded float comparisons (use configured constants).
