## 2026-06-29T21:57:22Z
You are the Explorer subagent for Milestone 1: Need Decay, Metabolism, and Waste Simulation.
Your task is to explore and analyze the codebase to plan the implementation:
1. Search the git history or `MVP_python` branch to find how the original Python codebase implemented:
   - Need decay rates/ticks for hunger, energy, social, cleanliness, and bladder.
   - Starvation damage: how much and how often health is reduced when hunger is at 100%.
   - Poop spawning: the probability check based on bladder level and time, and poop entity attributes.
   - Cleanliness reduction: the spatial or O(N^2) range/rates at which poop entities reduce nearby yukkuris' cleanliness.
   - Cleaning command: how the player cleans up poops (does it delete poop entities, restore cleanliness, etc.).
2. Examine the current Rust files (`src/ai/mod.rs`, `src/prefabs/mod.rs`, etc.) to see how `Needs` are currently defined and updated.
3. Formulate a precise design for:
   - The Rust components: `Needs`, any `Poop` entity marker component.
   - The Bevy systems: need decay tick, starvation damage, poop spawning, proximity cleanliness drop, and clean command handling.
   - Where these files should be added (e.g., `src/simulation/needs.rs` and `src/simulation/mod.rs`).
   - How the systems should be integrated into the Bevy app.
4. Output your analysis and implementation plan to your handoff file `.agents/explorer_1/handoff.md` and reply with a summary message.
Your working directory is: c:\Users\gamin\OneDrive\Documents\Git\Vibecoded_Yukkuri_Game\.agents\explorer_1
