# Actionable Tasks for Personality System 2.0

This document outlines the step-by-step implementation plan for the new system.

## Phase 1: Data Structure Updates

These tasks involve modifying the ECS components to support the new data models.

- [ ] **Task 1.1: Update `Personality` Component**
    - Modify `src/yukkuri_game/game/yukkuri_components.py`.
    - Add fields for Core Attributes: `aggression`, `sociability`, `intelligence`, `greed`, `stability`.
    - Add `values` dictionary for Nurture stats.
    - Ensure backwards compatibility (default values for existing saves/entities).
- [ ] **Task 1.2: Update `RelationshipData` Component**
    - Modify `src/yukkuri_game/game/yukkuri_components.py`.
    - Replace single scalar values with `affinity`, `dominance`, `trust` floats.
    - Add `label` field (calculated social status).
- [ ] **Task 1.3: Update `MemoryRecord`**
    - Ensure it supports the required fields for Episodic memory (`actor_id`, `action_type`, `impact`, `timestamp`).

## Phase 2: Logic Implementation

Implementing the core logic that drives personality and relationships.

- [ ] **Task 2.1: Personality Generator**
    - Create a helper service (e.g., in `EntityFactory` or `TraitService`) to generate random personalities based on parents (genetics) or random variation.
    - Implement "Nature" generation (Bell curve distribution for 0-100 stats).
- [ ] **Task 2.2: Relationship Update Logic**
    - Create `RelationshipSystem` (or update `TraitService`/`AISystem`).
    - Implement methods to update the 3 axes: `modify_affinity`, `modify_dominance`, `modify_trust`.
    - Implement decay logic for these values over time.
- [ ] **Task 2.3: Memory Consolidation Service**
    - Create a system that runs periodically (e.g., every in-game hour).
    - It should scan `memories`, apply their long-term effects to `values` or `relationship` stats, and then delete/archive them.

## Phase 3: Integration with AI

Connecting the new data to the existing Utility AI.

- [ ] **Task 3.1: Update Utility Considerations**
    - Modify `data/ai/actions.toml` (or the loading logic in `utility.py`).
    - Add new consideration inputs: `target_affinity`, `target_dominance`, `target_trust`, `self_aggression`, etc.
- [ ] **Task 3.2: Update Interaction Definitions**
    - Modify `data/ai/interactions.toml` to include effects on the new relationship axes.
    - Example: "Hit" -> `trust: -10`, `dominance: -5`.

## Phase 4: UI and Debugging

Making the system visible to the developer/player.

- [ ] **Task 4.1: Inspector UI Update**
    - Update the entity inspector to display the "Big Five" radar chart or bars.
    - Display the detailed Relationship list with the 3-axis values.
- [ ] **Task 4.2: Social Log**
    - Create a simple UI or log view to see the "Memory Stream" of an entity for debugging.

## Phase 5: Content Expansion (Optional/Later)

- [ ] **Task 5.1:** Add "Gossip" action.
- [ ] **Task 5.2:** Add "Training/Discipline" mechanics to modify Values.
