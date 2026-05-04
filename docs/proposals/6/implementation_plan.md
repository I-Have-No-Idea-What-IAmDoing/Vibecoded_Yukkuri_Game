# Proposal 6: Command-Based Input Buffering

## Overview
The current input handling is direct: keyboard and mouse events are translated immediately into actions (like moving the camera or placing an item) within the `InputSystem`.

## Motivation
- **Decoupling**: Separates raw hardware events from game-level intent.
- **Determinism**: Buffered commands can be executed at a fixed rate, which is essential for deterministic simulation and netplay.
- **Features**: Enables easy implementation of Undo/Redo, Input Replay (for bug reporting), and AI-driven inputs (AI "pressing buttons").

## Proposed Changes

### 1. Define `GameCommand` objects
Create a hierarchy of command classes (e.g., `PlaceItemCommand`, `SelectEntityCommand`, `MoveCameraCommand`).

### 2. Implement `InputBufferService`
A service that collects commands from the `InputSystem` and stores them in a queue.

### 3. Implement `CommandProcessorSystem`
A system that runs at the start of the frame, consumes commands from the buffer, and executes their logic.

### 4. Refactor `InputSystem`
Update `InputSystem` to only produce commands, not execute them.

## Impact
- **Stability**: Prevents "input spam" from overwhelming the game logic.
- **Extensibility**: Makes it trivial to add a console or scripting system that "executes commands".

## Implementation Phases
1.  **Phase 1**: Define the base `GameCommand` class and several initial command types.
2.  **Phase 2**: Implement the `InputBufferService` and `CommandProcessorSystem`.
3.  **Phase 3**: Refactor camera controls and selection logic to use commands.
4.  **Phase 4**: Refactor entity placement and interaction logic.
