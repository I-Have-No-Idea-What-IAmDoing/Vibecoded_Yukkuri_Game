# Critique of Proposal 1: AI System Rewrite

## Strengths

1.  **Primitive Action Composition**: The breakdown of complex behaviors into reusable primitives (`SeekPosition`, `CheckLineOfSight`) is excellent. This directly addresses the "God Object" anti-pattern found in `MoveToTarget`.
2.  **Configuration System**: Moving magic numbers to `ai_config.toml` is a high-value, low-risk improvement that significantly enhances tunability.
3.  **Typed ActionContext**: Replacing the untyped `state_data` dictionary with a dataclass is crucial for type safety and IDE support.
4.  **Phased Migration**: The plan allows for gradual adoption, which reduces the risk of breaking the entire game during the rewrite.

## Weaknesses

1.  **Limited System-Level Architectural Change**: While it cleans up the *code* within actions, it doesn't fundamentally change *how* the AI interacts with the game world as much as Proposal 2. It largely keeps the logic within the Behavior Tree nodes rather than moving execution to ECS Systems.
2.  **Potential for "Composite Bloat"**: Without strict rules, "Composite Actions" like `MoveToTargetV2` could eventually grow back into God Objects if they accumulate too much glue logic.
3.  **Performance**: It doesn't explicitly address the performance bottlenecks of the global utility evaluation or sensing as aggressively as Proposal 3 (Perception System).

## Verdict

Proposal 1 provides a solid **refactoring strategy** and code-level improvements. Its concept of **primitives** and **configuration** should be adopted. However, it lacks the architectural robustness of an ECS-driven approach for movement and sensing.
