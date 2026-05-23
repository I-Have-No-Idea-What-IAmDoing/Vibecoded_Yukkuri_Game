# Specification: Automated Testing Visual Diff Utility

## Goal Description
Enhance the headless integration testing suite (`GameDriver` inside `src/yukkuri_game/testing/driver.py`) to automatically generate and save a neon-magenta difference mask when a screenshot comparison fails. This tool will immediately isolate and highlight visual regression bugs (such as layout shifts, scaling problems, clipping, or incorrect sprite renderings) and provide clickable absolute URLs in the test console.

---

## Technical Architecture

### 1. File Modification
*   **Target File**: `src/yukkuri_game/testing/driver.py`
*   **Target Method**: `GameDriver.compare_screenshot`

### 2. Upgraded Method Signature
```python
def compare_screenshot(
    self,
    filename: str,
    reference_filename: str,
    tolerance: float = 0.01,
    drift_threshold: int = 5,
) -> bool:
    """
    Compares the current screen against a reference image. Exposes custom tolerances
    and thresholds. Raises descriptive AssertionErrors with clickable URLs on failure.
    """
```

### 3. Comparison Flow
1.  **Save Current Screen**: Save a screenshot of the active headless buffer to the absolute path of `filename`.
2.  **Reference Verification**: If `reference_filename` does not exist:
    *   Log a warning: `"Reference screenshot not found. Assumed new golden asset."`
    *   Return `True`.
3.  **Dimension Matching**: Load both images as Pygame surfaces. If their sizes are different:
    *   Format absolute paths to clickable file URLs:
        *   Actual: `file:///{os.path.abspath(filename)}`
        *   Expected: `file:///{os.path.abspath(reference_filename)}`
    *   Raise `AssertionError` detailing the dimension mismatch.
4.  **Fallback Mode (Numpy Missing)**:
    *   Log a warning: `"Numpy not available. Falling back to strict byte-wise check without diff mask."`
    *   Compare surfaces using strict byte-wise comparison of views (`surf.get_view("2").raw`).
    *   If buffers differ, raise `AssertionError` listing the clickable file URLs.
5.  **Visual Diff & Mask Generation (Numpy Active)**:
    *   Convert surfaces to 3D arrays: `pygame.surfarray.array3d(current_surf)` and `pygame.surfarray.array3d(ref_surf)`.
    *   Calculate absolute channel difference: `diff = np.abs(arr1 - arr2)`.
    *   Detect mismatched pixels exceeding color drift threshold:
        `mismatched_pixels = np.any(diff > drift_threshold, axis=2)`
    *   Calculate ratio:
        *   `num_diff = np.count_nonzero(mismatched_pixels)`
        *   `total_pixels = width * height`
        *   `diff_ratio = num_diff / total_pixels`
    *   If `diff_ratio > tolerance`:
        *   Initialize a black 3D array of matching dimensions:
            `diff_mask = np.zeros((width, height, 3), dtype=np.uint8)`
        *   Color mismatched pixels with **Neon Magenta**:
            `diff_mask[mismatched_pixels] = [255, 0, 255]`
        *   Convert the array back to a Pygame Surface:
            `diff_surf = pygame.surfarray.make_surface(diff_mask)`
        *   Save the diff mask to disk:
            `diff_filename = filename.rsplit(".", 1)[0] + "_diff.png"`
            `pygame.image.save(diff_surf, diff_filename)`
        *   Construct an explicit `AssertionError` with clear labels and clickable absolute URLs:
            ```text
            Visual Regression Mismatch Detected!
            Difference Ratio: {diff_ratio:.4%} (Allowed Tolerance: {tolerance:.4%})
            --------------------------------------------------------
            Expected (Reference): file:///{os.path.abspath(reference_filename)}
            Actual (Failed):      file:///{os.path.abspath(filename)}
            Difference Mask:      file:///{os.path.abspath(diff_filename)}
            --------------------------------------------------------
            ```
        *   Raise this `AssertionError`.
6.  **Success**: Return `True` if the comparison is within tolerance.

---

## ECS Architecture Impact
*   **Components**: None. This is a testing/diagnostic utility.
*   **Systems**: None.
*   **Services**: None.
*   **Events**: None.

---

## Test Plan

To ensure visual regression and diff mask creation work correctly under all circumstances, we will implement a new automated test:

### Test Case: `tests/integration/test_visual_diff.py`
A dedicated test that verifies the comparison behavior:
1.  **Golden Generation**: Draw a surface containing a simple blue rectangle and save it as a "reference".
2.  **Size Mismatch Assertion**: Draw a smaller surface, try to compare it against the reference, and verify that `AssertionError` is raised with dimension details.
3.  **Strict Tolerance Test**: Draw the same rectangle but shift it by 20 pixels (simulating a layout regression).
    *   Call `compare_screenshot` with tolerance `0.0` (zero tolerance).
    *   Assert that `AssertionError` is raised.
    *   Assert that the raised exception's error message contains absolute file URLs for both images and the diff mask.
    *   Assert that `_diff.png` is created on disk.
    *   Load the `_diff.png` image and verify that its pixels at the shifted region are colored **Neon Magenta** `(255, 0, 255)`.
4.  **Permissive Tolerance Test**:
    *   Call `compare_screenshot` with tolerance `0.5` (large tolerance) for the same shifted image.
    *   Assert that the method returns `True` successfully without raising an error.
5.  **Drift Threshold Test**:
    *   Draw the rectangle again, but alter its color slightly (e.g., RGB value from `(0, 0, 255)` to `(0, 0, 252)`).
    *   Compare with `drift_threshold = 5` and tolerance `0.0`. It should return `True` because the drift is within `5`.
    *   Compare with `drift_threshold = 2` and tolerance `0.0`. It should raise `AssertionError` because the drift is greater than `2`.
