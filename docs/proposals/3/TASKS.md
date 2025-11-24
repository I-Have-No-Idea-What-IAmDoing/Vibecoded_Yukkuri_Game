# Implementation Tasks: Proposal 3 (Revised)

## Phase 1: Core Data Structures (Refactor & Extend)
- [ ] **Refactor `YukkuriStats` & Create `EmotionalState`**
    - [ ] Create `EmotionalState` component in `yukkuri_components.py`.
        - [ ] Fields: `happiness` (float), `stress` (float), `anger` (float), `fear` (float). Range 0-100.
        - [ ] Method: `get_dominant_emotion()` returning Enum.
    - [ ] **Migration**: Remove `happiness` and `stress` from `YukkuriStats`.
    - [ ] **Update**: Fix references in `stat_decay.py` and `ui/` to point to the new component.
- [ ] **Enhance `Personality` Component**
    - [ ] Define `PersonalityAxis` dataclass (Kindness, Energy, Bravery, Greed).
    - [ ] **Update**: Replace or augment `Personality.values` dict with `PersonalityAxis` instance.
    - [ ] Implement `get_archetype()` helper based on axis values.
- [ ] **Expand `RelationshipData` (Memory System)**
    - [ ] Define `Headline` dataclass (id, timestamp, importance, is_locked).
    - [ ] **Update**: Add `trivial_buffer` (Deque[Headline], max=25) and `core_buffer` (Deque[Headline], max=35) to `RelationshipData`.
    - [ ] Implement `lock_memory()` logic to move items from trivial to core.
- [ ] **Create `GossipQueue` Component**
    - [ ] Define `GossipPacket` dataclass (target_id, event_type, value).
    - [ ] Add `priority_queue` field to store top 3 gossip items.

## Phase 2: Systems Logic & Simulation
- [ ] **Implement `EmotionSystem` (Refactor `stat_decay.py`)**
    - [ ] Rename/Refactor `stat_decay.py` to `emotion_system.py`.
    - [ ] **Decay Logic**: Implement differential decay (Stress decays fast to 0, Happiness decays slow to 50).
    - [ ] **Input**: Handle `Impact` events (e.g., taking damage adds Stress).
- [ ] **Refactor `SocialSystem`**
    - [ ] **Spatial Queries**: Use `pymunk.Space.point_query` or `shape_query` for "Sector Broadcasting" (Auditory/Visual ranges) instead of custom Grid.
    - [ ] **Compatibility**: Update compatibility checks to use new `PersonalityAxis` (specifically `Greed` and `Kindness`).
    - [ ] **Events**: Emit "SocialEvents" when interactions occur.
- [ ] **Implement `GossipSystem`**
    - [ ] **Witnessing**: When an entity is within visual range (Raycast check) of an event, create `GossipPacket`.
    - [ ] **Exchange**: In `Chat` interaction, implement logic to exchange `GossipPacket`s between `GossipQueue`s.

## Phase 3: AI Integration (The Brain)
- [ ] **Update Behavior Trees (`py_trees`)**
    - [ ] Create/Update Condition Nodes: `CheckEmotion` (replacing old stats checks), `CheckStressLevel`.
    - [ ] Create "Stress Break" Subtree: Triggered when `stress > 90`.
- [ ] **Trait Data Migration**
    - [ ] Update `data/traits/traits.toml` schema to use **Axis Shifts** (e.g., `kindness_shift = +20`) instead of hard values.
    - [ ] Write migration script/logic in `trait_service.py` to apply these shifts to `PersonalityAxis`.

## Phase 4: Verification & Tools
- [ ] **Debug Tools**
    - [ ] **Psychoanalysis UI**: Window showing Axis charts and Emotion bars.
    - [ ] **Memory Inspector**: View contents of `trivial_buffer` and `core_buffer` for selected entity.
- [ ] **Verification**
    - [ ] **Memory Leak Check**: Ensure `Headline` objects are garbage collected when `RelationshipData` is cleared.
    - [ ] **Decay Verification**: Plot `EmotionalState` values over time to verify decay curves match config.

## Pre-Commit Checklist
- [ ] **Static Analysis**: Run `mypy` to verify component changes.
- [ ] **Unit Tests**:
    - [ ] `test_emotion_decay`: Verify stress returns to baseline.
    - [ ] `test_memory_locking`: Verify locked memories persist in core buffer.
    - [ ] `test_personality_archetypes`: Verify correct classification of mixed axes.
- [ ] **Integration Check**: Ensure `entity_factory.py` initializes new components correctly.
