## 2026-06-29T22:40:38Z

You are the E2E Test Suite Developer. Your task is to fix a failing test case in `tests/integration/test_e2e.py`.
Specifically, the test `test_traits_skills_coverage[trait_decay_modifier]` failed with:
`assert needs_g.hunger > needs_n.hunger`
`where 40.5 > 40.5`
This happens because when a Yukkuri is spawned, it rolls a random trait if it doesn't inherit any from parents. Under the seeded RNG, the normal yukkuri and the glutton yukkuri both end up with the `"GLUTTON"` trait or share some traits.
To fix this, edit `test_traits_skills_coverage` in `tests/integration/test_e2e.py` (specifically under `trait_decay_modifier`) to:
1. Clear traits on both normal and glutton yukkuri entities.
2. Add only `"GLUTTON"` to the glutton yukkuri:
```python
        pers_n = driver.get_component(normal_id, Personality)
        pers_g = driver.get_component(glutton_id, Personality)
        pers_n.traits.clear()
        pers_g.traits.clear()
        pers_g.traits.add("GLUTTON")
```
Please make this edit to `tests/integration/test_e2e.py` around line 483.
Run the test suite `uv run pytest tests/integration/test_e2e.py` to verify that all tests pass.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.


## 2026-06-29T22:44:39Z

From: main agent (2b10aa19-2240-4d38-ad3b-dc70929d691b)
Context: Fixing line of sight E2E test failure.
Content: The test case `test_opinion_gossip_boundary[line_of_sight]` is failing because Pymunk's segment query is not hitting the static wall shape. When you change a Pymunk body type to `STATIC` after it has already been added to the space, you must force the space to re-index the shapes for that body, otherwise queries will miss it.

Please update the `line_of_sight` test block in `tests/integration/test_e2e.py` (around line 1040) to reindex the shapes:
```python
            pb = driver.get_component(wall_id, PhysicsBody)
            pb.body.body_type = pymunk.Body.STATIC
            pb.body.space.reindex_shapes_for_body(pb.body)
```
Action: Implement this change, run the test suite to ensure all tests pass (or to see if there are other failures), and report back.
