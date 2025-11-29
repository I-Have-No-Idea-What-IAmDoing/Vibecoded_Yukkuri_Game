
import pytest
from ..game.yukkuri_components import MemoryBuffer, Headline

def test_memory_locking():
    # Capacity 3
    buffer = MemoryBuffer(maxlen=3)

    # Fill with trivial
    h1 = Headline(id=1, timestamp=0, importance=10, is_locked=False, text="1")
    h2 = Headline(id=2, timestamp=0, importance=10, is_locked=False, text="2")
    h3 = Headline(id=3, timestamp=0, importance=10, is_locked=False, text="3")

    buffer.add(h1)
    buffer.add(h2)
    buffer.add(h3)

    assert len(buffer.items) == 3

    # Add 4th, should push out oldest (h1)
    h4 = Headline(id=4, timestamp=0, importance=10, is_locked=False, text="4")
    buffer.add(h4)
    assert len(buffer.items) == 3
    assert buffer.items == [h2, h3, h4]

    # Lock one
    h3.is_locked = True

    # Add 5th. Should push out h2 (oldest non-locked)
    h5 = Headline(id=5, timestamp=0, importance=10, is_locked=False, text="5")
    buffer.add(h5)
    assert len(buffer.items) == 3
    # h3 is locked, so it stays. h2 was oldest unlocked.
    # Logic: iterate 0..len-2. items[0] is h2. not locked. remove h2.
    assert h3 in buffer.items
    assert h5 in buffer.items
    assert h2 not in buffer.items # Removed

    # Fill with all locked
    h4.is_locked = True
    h5.is_locked = True
    # Now [h3(L,10), h4(L,10), h5(L,10)]

    # Try add low importance
    h6 = Headline(id=6, timestamp=0, importance=15, is_locked=False, text="6")
    buffer.add(h6)
    # New importance 15. Lowest existing is 10. 15 > 10 * 2.0 is FALSE.
    # Should NOT replace anything.
    assert len(buffer.items) == 3
    assert h6 not in buffer.items

    # Try add high importance
    h7 = Headline(id=7, timestamp=0, importance=25, is_locked=False, text="7")
    buffer.add(h7)
    # 25 > 10 * 2.0 (20) is TRUE.
    # Should replace one of the 10s.
    assert len(buffer.items) == 3
    assert h7 in buffer.items
