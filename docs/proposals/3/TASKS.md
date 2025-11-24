# Implementation Tasks: Proposal 3

## Phase 1: Data Structures (The Skeleton)
- [ ] **Create `PersonalityAxis` Component**
    - [ ] Fields: `kindness` (int), `energy` (int), `bravery` (int). Range -100 to 100.
    - [ ] Method: `get_archetype()` returning string (e.g., "Scum", "Hero") for debug.
- [ ] **Create `EmotionalState` Component**
    - [ ] Fields: `happiness` (float), `stress` (float).
    - [ ] Method: `get_mood_quadrant()` returning Enum (CONTENT, MANIC, DEPRESSED, RAGE).
- [ ] **Create `MemoryBank` Component**
    - [ ] Define `Headline` struct/dataclass.
    - [ ] Define `RelationshipEntry` holding the ring buffer and cached opinion.

## Phase 2: The Systems (The Muscle)
- [ ] **Implement `EmotionSystem`**
    - [ ] **Decay Logic:** Stress decays fast (returns to calm). Happiness decays slow (returns to neutral).
    - [ ] **Tuning:** Expose decay rates in a config file.
- [ ] **Implement `SocialSystem` (Refactor)**
    - [ ] **Compatibility Check:** Create function `calculate_base_compatibility(actor_p, target_p)`.
    - [ ] **Headline Trigger:** Update interactions to emit "SocialEvents". If Event Impact > Threshold, create Headline.
    - [ ] **Opinion Cache:** Update cached opinion whenever a Headline is added.

## Phase 3: Integration (The Brain)
- [ ] **Update AI Decision Making**
    - [ ] Replace old `if mood == "HAPPY"` checks with `if emotion.happiness > 0`.
    - [ ] Implement "Stress Breaks": If `stress > 90`, force a specialized behavior state (Panic/Berserk) based on `Bravery`.
- [ ] **Trait Data Migration**
    - [ ] Update `traits.toml` to include `axis_modifiers` (e.g., `predator: bravery=+50`).

## Phase 4: Verification & UI
- [ ] **Debug Tools**
    - [ ] Add "Psychoanalysis" window: Shows the 3 Axes and current Stress/Happiness graph.
    - [ ] Add "Memory Viewer": Shows the 5 Headlines for a selected target.
- [ ] **Performance Test**
    - [ ] Spawn 100 entities.
    - [ ] Force spam interactions.
    - [ ] Verify memory usage remains stable (due to fixed buffer).

## Pre-Commit Checklist
- [ ] **Unit Tests:**
    - [ ] Test `MemoryBank` circular buffer (ensure it overwrites correctly).
    - [ ] Test `Opinion` calculation math.
    - [ ] Test `PersonalityAxis` clamping logic.
- [ ] **Review:**
    - [ ] Verify no hardcoded float comparisons (use configured constants).
