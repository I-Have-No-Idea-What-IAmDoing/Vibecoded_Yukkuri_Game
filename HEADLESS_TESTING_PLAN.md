# Headless Testing Infrastructure Improvement Plan

## 1. Goal
Improve the quality, robustness, and accuracy of the headless testing infrastructure for the Yukkuri Game.

## 2. Analysis of Current State
- **Robustness**: Current tests rely on checking if screenshots are "not black". This is brittle.
- **Accuracy**: Tests verify rendering but lack regression capabilities against known good states.
- **Determinism**: Simulation time needs strict control to ensure reproducible results.
- **Debuggability**: When headless tests fail, it is hard to know why without logs or state dumps.

## 3. Improvements Implemented

### 3.1. Strict Time Control
- **Refactoring `GameDriver`**: Modified `_tick()` to ensure `TimeService` is accurately updated during headless execution.
- **Mocking**: Ensured that the game loop does not rely on wall-clock time (`pygame.time.get_ticks()`) for simulation logic.

### 3.2. Image Comparison (Visual Regression)
- **Feature**: Added `compare_screenshot(filename, reference_filename, tolerance)` to `GameDriver`.
- **Logic**: Compares the rendered frame against a "Gold Master" reference image. Supports pixel-perfect matching and tolerant comparison (if numpy is available).

### 3.3. State Dumping
- **Feature**: Added `dump_state()` to `GameDriver`.
- **Usage**: Automatically called when a test scenario fails, dumping the current ECS state (entities and components) to a log file.

### 3.4. Log Assertions
- **Feature**: Added `capture_logs()` context manager to `GameDriver`.
- **Usage**: Allows tests to assert that specific logs were emitted (or not emitted), useful for verifying system behavior without visual output.

### 3.5. Enhanced Tests
- **`test_headless_robustness.py`**: Updated to use log assertions.
- **`test_headless_advanced.py`**: New test suite demonstrating image comparison and reset consistency.

## 4. Future Work
- Integrate numpy for faster and more flexible image comparison if not already present in the environment.
- Add more granular component dumping for `dump_state`.
