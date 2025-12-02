"""
Type definitions for the engine.
"""
from typing import NewType

# Msgspec handles NewType(int) automatically as int during serialization/deserialization.
# Using a class inheriting from int causes issues with msgspec unless we register a custom handler,
# but NewType works out of the box.
EntityID = NewType('EntityID', int)
