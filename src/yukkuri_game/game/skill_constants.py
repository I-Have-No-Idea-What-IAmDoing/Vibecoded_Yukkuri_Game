"""
Skill Constants.
"""
from enum import Enum

class SkillId(str, Enum):
    """
    Enumeration of available skills.
    """
    ATHLETICS = "athletics"
    SOCIALIZATION = "socialization"
    SCAVENGING = "scavenging"
    COMBAT = "combat"

class PassionLevel(float, Enum):
    """
    Enumeration of passion levels affecting XP gain.
    """
    NONE = 0.5
    NORMAL = 1.0
    INTERESTED = 1.5
    BURNING = 2.5
