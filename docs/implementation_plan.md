# Implementation Plan

## Phase 1: Core Systems Implementation
- [ ] **Define Components**: Create `Personality` and `SocialMemory` components in `src/yukkuri_game/game/yukkuri_components.py`.
- [ ] **Implement Personality Logic**: Create `src/yukkuri_game/game/personality.py` to handle trait generation and mood updates.
- [ ] **Implement Relationship Logic**: Create `src/yukkuri_game/game/relationship.py` to handle relationship updates (decay, interaction effects).

## Phase 2: AI Integration
- [ ] **Update Utility AI Context**: Modify `src/yukkuri_game/game/ai/utility.py` (or the caller in `behavior.py`) to inject:
    *   Personality Traits
    *   Relationship scores with the current target
- [ ] **Create New Considerations**: Add `TraitConsideration` and `RelationshipConsideration` classes to `utility.py`.
- [ ] **Define New Actions**: Update `data/ai_actions.toml` (or wherever actions are defined) to include social actions like `Chat`, `Intimidate`, `Share`. *Note: Need to check where actions are actually stored/loaded.*

## Phase 3: Interaction & Events
- [ ] **Event System**: Ensure an event system exists to broadcast social interactions (`InteractionSystem` needs to trigger logic in `RelationshipSystem`).
- [ ] **Interaction Handlers**: Implement the logic where "Being Hit" -> updates Memory -> updates Relationship.

## Phase 4: Testing & Verification
- [ ] **Unit Tests**: Test Personality generation and Utility Context injection.
- [ ] **Simulation Test**: Run a simulation with 2 Yukkuris and log their interactions to verify relationship evolution.

## Detailed Tasks

1.  *Update `yukkuri_components.py`*
    - Add `Personality` dataclass.
    - Add `Relationship` and `SocialMemory` dataclasses.

2.  *Create `systems/social_system.py`*
    - This system will run periodically.
    - Updates Moods based on Stats.
    - Decays Relationships.
    - Processes queued social events (if any).

3.  *Modify `ai/utility.py`*
    - Add `TraitConsideration`.
    - Add `RelationshipConsideration`.
    - Update `score()` methods to handle these.

4.  *Modify `systems/interaction_system.py`*
    - When interactions occur, update the `SocialMemory` of the involved entities.
    - E.g., if `Eat` happens, and it was a gift, update Trust. (This might be complex, start simple: simple proximity updates first).

5.  *Pre-commit & Submit*
