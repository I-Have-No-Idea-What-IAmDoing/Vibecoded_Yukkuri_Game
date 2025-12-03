# Critique of Proposal 3: The "Ghost Child" Delusion

While this proposal correctly identifies that standard physics integration is bad for arcade control, its proposed implementation is a performance hog and visually broken.

## 1. Performance Suicide: Python Sweeps

The proposal advocates for `space.shape_query` (sweeps) for every moving entity, multiple times per frame (Axis-Separated).
*   **Slow in Python:** Calling into Pymunk's C-API from Python for every single entity, twice per frame, plus resolving the logic in Python, will kill the frame rate.
*   **O(N) * Complexity:** If you have 500 entities, that's 1000+ shape queries per frame. Pymunk is fast, but the Python overhead is not.

## 2. The "Sensor" Problem: Visual Garbage

The proposal suggests: *"Children have their physics shapes set to Sensor... Only the Root collides."*
*   **Clipping:** This means if you have a stack of 3 Yukkuri, and you walk sideways into a low overhang, the top two will simply **clip through the wall**. This looks incredibly cheap and amateurish.
*   **Inconsistent Interactions:** If a child is a "Sensor", it can't be hit by projectiles or push buttons physically. You have to write *another* system to handle "Sensor collisions that should be real."

## 3. "Rigid Parenting" Logic Flaws

*   **The "Wide Load" Issue:** If a child is wider than the parent, the parent might fit through a gap but the child won't. Since the parent drives the movement and the child is a ghost, the child will pass through the solid wall.
*   **Hitbox Expansion:** The "Advanced" suggestion to resize the root hitbox is a nightmare. Changing a physics shape's geometry every time someone mounts/dismounts requires re-indexing the spatial hash, which is expensive and prone to bugs (getting stuck in walls because your hitbox suddenly grew).

## 4. Conclusion

This proposal offers "tight controls" at the cost of **visual integrity** and **performance**. The "Ghost Child" clipping is unacceptable for a polished game. While the "Controller" pattern is the right direction, this specific implementation is naive. **Rejected in its current form.**
