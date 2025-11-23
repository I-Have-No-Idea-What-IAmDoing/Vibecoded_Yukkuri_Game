# Implementation Tasks: Personality & Relationship System 2.0

This document outlines the step-by-step plan to implement the design proposed in `DESIGN.md`.

## Phase 1: Data Structure Refactoring
*Goal: Establish the new component schemas without breaking existing logic immediately.*

- [ ] **Create `PersonalityDimensions` Component**
    - [ ] Define dataclass with fields: `intellect`, `cooperativeness`, `conscientiousness`, `extroversion`, `neuroticism` (floats 0.0-1.0).
- [ ] **Create `EmotionState` Component**
    - [ ] Define dataclass with fields: `pleasure`, `arousal`, `dominance` (floats -1.0 to 1.0).
    - [ ] Define `base_line` (target state to drift towards).
- [ ] **Refactor `RelationshipData`**
    - [ ] Add `long_term_memories` list.
    - [ ] Add `cached_opinion` (float).
    - [ ] Mark `affinity` as deprecated (or map it to `cached_opinion`).
- [ ] **Update `EntityFactory`**
    - [ ] Initialize new components when spawning Yukkuris.
    - [ ] Randomize `PersonalityDimensions` based on Yukkuri Type (e.g., Reimus might have lower Intellect on average).

## Phase 2: The Emotion Engine
*Goal: Replace the static string moods with the dynamic PAD system.*

- [ ] **Create `EmotionSystem`**
    - [ ] Implement `update()` loop.
    - [ ] **Logic:** Decay current P/A/D values towards `base_line` using `PersonalityDimensions.neuroticism` to determine decay speed.
    - [ ] **Logic:** Map current P/A/D vector to a string (e.g., "Happy", "Rage") for UI display (backward compatibility with `Personality.mood`).
- [ ] **Integrate with `SocialSystem`**
    - [ ] Modify `_apply_impact`: Instead of setting `mood = "HAPPY"`, apply a vector impulse (e.g., Pleasure +0.5, Arousal +0.2).

## Phase 3: Memory & Opinion Logic
*Goal: Make relationships history-based.*

- [ ] **Enhance `MemoryRecord`**
    - [ ] Add `opinion_modifier` (float) field.
    - [ ] Add `expiration` (timestamp) for temporary memories.
- [ ] **Implement Opinion Calculation**
    - [ ] Create helper function `calculate_opinion(relationship_data) -> float`.
    - [ ] Sum valid short-term memory modifiers + long-term core memory modifiers.
- [ ] **Update `SocialSystem` Interaction Logic**
    - [ ] When interaction occurs, generate a `MemoryRecord`.
    - [ ] Calculate `opinion_modifier` based on Interaction Type + Actor's Compatibility.
    - [ ] Append to `RelationshipData` and trigger `calculate_opinion`.

## Phase 4: Trait & Interaction Data Update
*Goal: Update the data files to support the new system.*

- [ ] **Update `data/traits/traits.toml`**
    - [ ] Add `dimension_modifiers` block to traits (e.g., `intellect = 0.2`).
- [ ] **Update `data/ai/interactions.toml`**
    - [ ] Add `pad_impact` block (e.g., `pleasure = -0.5`, `arousal = 0.8`).
- [ ] **Update `TraitService`**
    - [ ] Parse and serve these new data fields.

## Phase 5: Cleanup & UI
*Goal: Polish and verify.*

- [ ] **Debug Inspector**
    - [ ] Create a text-based or UI inspector to view the PAD vector and current Opinion breakdown.
- [ ] **Deprecate Old Systems**
    - [ ] Remove legacy `mood` string logic from `SocialSystem`.
    - [ ] Remove linear decay logic.

## Pre-Commit Checklist
- [ ] Run existing tests to ensure no immediate crashes.
- [ ] Add unit tests for `EmotionSystem` decay logic.
- [ ] Add unit tests for `calculate_opinion`.
