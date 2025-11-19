"""
Data schemas for the Yukkuri Raising Game.

This module defines the expected structure of the JSON data files using
Python's `typing.TypedDict`. This allows for static analysis and provides
clear documentation of the expected data format.
"""
from typing import TypedDict, List, Dict, NotRequired

# schemas.py
class YukkuriSchema(TypedDict):
    id: str
    display_name_key: str
    base_needs: Dict[str, float]
    personality: Dict[str, float]
    ai_profile: str


class ItemSchema(TypedDict):
    id: str
    display_name_key: str
    size: Dict[str, int]
    tags: List[str]
    effects: Dict[str, Dict[str, float]]


class ConsiderationSchema(TypedDict):
    type: str
    weight: float
    # Fields that are not required for all consideration types
    curve: NotRequired[str]
    need: NotRequired[str]
    tag: NotRequired[str]
    value: NotRequired[float]


class ActionSchema(TypedDict):
    id: str
    cooldown: float
    considerations: List[ConsiderationSchema]


class BehaviorSchema(TypedDict):
    actions: List[ActionSchema]
