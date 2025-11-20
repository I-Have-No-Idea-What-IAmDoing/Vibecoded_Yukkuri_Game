# Development Guidelines

*   **Architecture**: Follow a clean separation of concerns. Entities, Systems, and UI should be decoupled.
*   **Data-Driven**: All gameplay parameters must be loaded from `data/` YAML files. Do not hardcode values in classes.
*   **AI**: The Utility AI should be generic. Actions should not be hardcoded into the `Yukkuri` class but rather injected or looked up.
*   **Testing**: Verify all changes. Run the game frequently to ensure no regressions.
