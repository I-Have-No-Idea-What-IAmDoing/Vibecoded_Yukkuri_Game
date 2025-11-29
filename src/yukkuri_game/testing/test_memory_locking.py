
import pytest
from ..game.yukkuri_components import RelationshipData, MemoryHeadline as Headline

# Since MemoryBuffer logic was moved into RelationshipData, we should test RelationshipData's add_headline
# But wait, MemoryBuffer is just a wrapper around list/deque in new impl?
# Or did I remove logic from MemoryBuffer?
# Looking at yukkuri_components.py, MemoryBuffer is just a wrapper.
# The logic is in RelationshipData.add_headline and _add_core_memory.
# So I should update this test to test RelationshipData.

def test_memory_locking():
    # Setup
    rel = RelationshipData()
    # Mock buffers to small size for testing
    from collections import deque
    rel.core_buffer = deque(maxlen=3)

    # Fill with core memories (importance > 50 or locked)
    h1 = Headline(id=1, timestamp=0, importance=60, event_type="1", is_locked=False)
    h2 = Headline(id=2, timestamp=0, importance=60, event_type="2", is_locked=False)
    h3 = Headline(id=3, timestamp=0, importance=60, event_type="3", is_locked=False)

    rel.add_headline(h1)
    rel.add_headline(h2)
    rel.add_headline(h3)

    assert len(rel.core_buffer) == 3
    assert list(rel.core_buffer) == [h1, h2, h3]

    # Add 4th, should push out oldest (h1)
    h4 = Headline(id=4, timestamp=0, importance=60, event_type="4", is_locked=False)
    rel.add_headline(h4)
    assert len(rel.core_buffer) == 3
    assert list(rel.core_buffer) == [h2, h3, h4]

    # Lock one (h3)
    # Modifying existing item in buffer
    # Deque stores references, so this works if we modify the object
    h3.is_locked = True

    # Add 5th. Should push out h2 (oldest non-locked)
    # Current buffer: [h2, h3(L), h4]
    h5 = Headline(id=5, timestamp=0, importance=60, event_type="5", is_locked=False)
    rel.add_headline(h5)

    assert len(rel.core_buffer) == 3
    # h3 is locked, so it stays. h2 was oldest unlocked (at index 0).
    assert h3 in rel.core_buffer
    assert h5 in rel.core_buffer
    assert h2 not in rel.core_buffer
    # Expected order depends on implementation.
    # Logic: del core_buffer[i], append new.
    # [h2, h3, h4]. h2 is not locked. del index 0. -> [h3, h4]. append h5 -> [h3, h4, h5]
    assert list(rel.core_buffer) == [h3, h4, h5]

    # Lock all
    h4.is_locked = True
    h5.is_locked = True
    # Now [h3(L), h4(L), h5(L)]

    # Try add new one
    h6 = Headline(id=6, timestamp=0, importance=60, event_type="6", is_locked=False)
    rel.add_headline(h6)

    # If all locked, currently implementation just passes (does nothing) because magnitude is same
    assert len(rel.core_buffer) == 3
    assert h6 not in rel.core_buffer

    # Try add one with significantly higher importance (> +20)
    # Locked memories are importance 60
    h7 = Headline(id=7, timestamp=0, importance=90, event_type="7", is_locked=False)
    rel.add_headline(h7)

    # Should overwrite the one with lowest importance. All are 60.
    # It overwrites one.
    assert len(rel.core_buffer) == 3
    assert h7 in rel.core_buffer
    # Should contain h7 and two of the previous locked ones
    assert (h3 in rel.core_buffer) or (h4 in rel.core_buffer) or (h5 in rel.core_buffer)
