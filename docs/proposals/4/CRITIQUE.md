# Critique of Proposal 4: Deterministic Kinematic Hierarchy

## 1. Complexity of "Sweep-and-Slide" Implementation
The proposal relies heavily on a custom "Sweep-and-Slide" implementation using `segment_query`. While this allows for deterministic control, it effectively reimplements physics collision resolution, which is notoriously difficult to get right.
*   **Edge Cases:** The simple "slide" logic (projecting velocity onto the tangent) works for single walls but often fails at "pinch points" (acute angles between walls) or "concave corners," leading to jitter or getting stuck.
*   **Internal Edges:** Moving across flat seams between two wall segments can cause the character to "catch" on the shared vertex if not explicitly handled (e.g., by filtering normals that oppose movement).
*   **Precision:** Relying on `alpha - epsilon` can cause entities to hover slightly off surfaces or drift through them over time due to floating-point accumulation.

## 2. Visibility Performance Optimism
The proposal claims that visibility checks are performant because Pymunk's spatial hash makes raycasts roughly $O(1)$. This is optimistic.
*   **Scale:** With $N$ observers and $M$ targets, $O(N \times M)$ raycasts per frame is prohibitively expensive in Python, even with spatial hashing. 50 units vs 50 units = 2500 raycasts/frame.
*   **Optimization Needed:** A strict "Broadphase First" approach is required. Checks like distance and sector (FOV) should precede any raycasting.

## 3. Dismount Logic "Crush" Fallback
The fallback mechanism where an entity "gets crushed" if the concentric search limit is reached is too harsh.
*   **Player Experience:** Losing a unit instantly because it tried to dismount near a complex wall geometry feels unfair and buggy.
*   **False Negatives:** The discrete search pattern might miss a valid spot that is just slightly off-grid or beyond the search radius.
*   **Recommendation:** A "Pending Dismount" state or "Ghost Mode" is preferred over immediate destruction.

## 4. Stack Rotation & Sweeping
The proposal focuses on linear movement but neglects rotation for "Totem Pole" stacks.
*   **Sweeping Width:** If a stack rotates, a wide child entity might clip into a wall because `segment_query` only checks the linear path of the root's central axis (or capsule).
*   **Compound Bounds:** The root's collider needs to dynamically expand to encompass the full bounding box of the stack, or rotation must be restricted.

## 5. Integration Details
*   **Body Type:** The proposal mentions manually setting position but doesn't explicitly mandate `pymunk.Body.KINEMATIC`. Using `DYNAMIC` bodies with manual position updates breaks the physics solver.
*   **Sensor Overlaps:** Mounted children being sensors means they don't block movement, leading to potential visual clipping of the "head" of the stack into ceilings. Mandatory ceiling checks are needed.
