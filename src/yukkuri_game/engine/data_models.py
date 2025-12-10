"""
Module defining data models for game configuration (TOML schema).
"""

from typing import Dict, List, Optional, Any
import msgspec


class AnimationDefinition(msgspec.Struct):  # type: ignore[misc]
    """
    Data model representing an animation sequence.

    Attributes:
        name (str): The name of the animation.
        frames (List[int]): List of frame indices.
        frame_duration (float): Duration of each frame in seconds.
        loop (bool): Whether the animation should loop. Defaults to True.
        ping_pong (bool): Whether the animation should play back and forth. Defaults to False.
        events (Dict[int, str]): Dictionary mapping frame indices to event names.
        image (Optional[str]): Path to the sprite sheet image, if different from the base.
        width (Optional[int]): Width of a frame, if different from the base.
        height (Optional[int]): Height of a frame, if different from the base.
    """

    name: str
    frames: List[int]
    frame_duration: float
    loop: bool = True
    ping_pong: bool = False
    events: Dict[int, str] = msgspec.field(default_factory=dict)
    image: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None


class YukkuriType(msgspec.Struct):  # type: ignore[misc]
    """
    Data model representing a type of Yukkuri.

    Attributes:
        name (str): The display name of the Yukkuri type.
        image (str): The path to the sprite sheet image.
        width (int): The width of the sprite in pixels.
        height (int): The height of the sprite in pixels.
        max_health (int): The maximum health points.
        base_happiness (int): The starting happiness level.
        cost (int): The purchase cost of the Yukkuri. Defaults to 100.
        animations (Dict[str, AnimationDefinition]): A dictionary of animation definitions.
    """

    name: str
    image: str
    width: int
    height: int
    max_health: int
    base_happiness: int
    cost: int = 100
    animations: Dict[str, AnimationDefinition] = {}


class ItemType(msgspec.Struct):  # type: ignore[misc]
    """
    Data model representing a type of Item.

    Attributes:
        name (str): The display name of the item.
        image (str): The path to the item image.
        width (int): The width of the item in pixels.
        height (int): The height of the item in pixels.
        cost (int): The purchase cost of the item.
        is_portable (bool): Whether the item can be carried.
        nutrition (Optional[int]): Nutrition value if the item is food.
        comfort (Optional[int]): Comfort value if the item provides comfort (e.g. bed).
        fun (Optional[int]): Fun value if the item is a toy.
    """

    name: str
    image: str
    width: int
    height: int
    cost: int
    is_portable: bool
    nutrition: Optional[int] = None
    comfort: Optional[int] = None
    fun: Optional[int] = None


class ActionEffect(msgspec.Struct):  # type: ignore[misc]
    """
    Data model representing the effects of an AI action.

    Attributes:
        type (str): The type of effect (e.g., 'move_to', 'interact', 'modify_stat').
        target_stat (Optional[str]): The stat to modify, if applicable.
        consume (bool): Whether the target object is consumed (removed) after the action. Defaults to False.
        stat_changes (Dict[str, float]): A dictionary of stat changes to apply.
    """

    type: str
    target_stat: Optional[str] = None
    consume: bool = False
    stat_changes: Dict[str, float] = {}


class ActionConsideration(msgspec.Struct):  # type: ignore[misc]
    """
    Data model representing a consideration (input factor) for an AI action.

    Attributes:
        name (str): The name of the consideration.
        input (str): The input value key (e.g., 'hunger', 'distance').
        curve (str): The response curve type (e.g., 'linear', 'logistic').
        params (Dict[str, float]): Parameters for the response curve.
    """

    name: str
    input: str
    curve: str
    params: Dict[str, float] = {}


class AIAction(msgspec.Struct):  # type: ignore[misc]
    """
    Data model representing an AI action definition.

    Attributes:
        weight (float): The base weight or priority of the action.
        effects (ActionEffect): The effects resulting from the action.
        considerations (List[ActionConsideration]): A list of considerations that influence the action's score.
    """

    weight: float
    effects: Optional[ActionEffect] = None
    considerations: List[ActionConsideration] = []


class SkillDefinition(msgspec.Struct):  # type: ignore[misc]
    """
    Data model representing a Skill definition.

    Attributes:
        name (str): Display name of the skill.
        description (str): Description of the skill.
        max_level (int): Maximum level achievable.
        decay_rate (float): XP loss per day.
        soft_cap_base_level (int): Level where soft cap starts.
    """

    name: str
    description: str
    max_level: int = 20
    decay_rate: float = 0.0
    soft_cap_base_level: int = 10


class TraitDefinition(msgspec.Struct):  # type: ignore[misc]
    """
    Data model for a Personality Trait.
    """

    name: str
    description: str
    conflicts: List[str] = []
    axis_shift: Dict[str, int] = {}
    stat_modifiers: Dict[str, float] = {}
    ai_modifiers: Dict[str, Any] = {}  # Complex structure, can be boolean flags or dicts
    skill_modifiers: Dict[str, Dict[str, float]] = {}
    social_modifiers: Dict[str, Dict[str, float]] = {}


# Interaction definitions are complex because they have conditions and modifiers.
# For now we use Dict[str, Any] for flexibility or define a loose struct.
class InteractionDefinition(msgspec.Struct):  # type: ignore[misc]
    """
    Data model for a Social Interaction.
    """

    base_impact: float = 0.0
    social_impact: Dict[str, float] = {}
    range_type: str = "touch"
    conditions: List[Dict[str, Any]] = []  # e.g. [{type="skill_check", ...}]
    modifiers: Dict[str, Dict[str, float]] = {}


# --- Game Tuning Data Models (from yukkuri_tuning.json) ---


class MovementVisuals(msgspec.Struct):  # type: ignore[misc]
    """
    Tuning for movement visual effects.

    Attributes:
        bob_height (float): The height of the bobbing animation.
        bob_speed (float): The speed of the bobbing animation.
    """

    bob_height: float = 10.0
    bob_speed: float = 5.0


class VisualTuning(msgspec.Struct):  # type: ignore[misc]
    """
    Container for all visual-related tuning.

    Attributes:
        movement (MovementVisuals): Tuning for movement visuals.
    """

    movement: MovementVisuals


class GameTuning(msgspec.Struct):  # type: ignore[misc]
    """
    Root container for the main JSON tuning file.

    Attributes:
        visuals (VisualTuning): Visual tuning parameters.
    """

    visuals: VisualTuning


# --- Root containers for the TOML structure ---
class YukkuriData(msgspec.Struct):  # type: ignore[misc]
    """
    Root container for Yukkuri type definitions loaded from TOML.

    Attributes:
        yukkuris (Dict[str, YukkuriType]): A dictionary mapping Yukkuri type names to their definitions.
    """

    yukkuris: Dict[str, YukkuriType]


class ItemData(msgspec.Struct):  # type: ignore[misc]
    """
    Root container for Item type definitions loaded from TOML.

    Attributes:
        items (Dict[str, ItemType]): A dictionary mapping item type names to their definitions.
    """

    items: Dict[str, ItemType]


class AIData(msgspec.Struct):  # type: ignore[misc]
    """
    Root container for AI action definitions loaded from TOML.

    Attributes:
        actions (Dict[str, AIAction]): A dictionary mapping action names to their definitions.
    """

    actions: Dict[str, AIAction]


class SkillData(msgspec.Struct):  # type: ignore[misc]
    """
    Root container for Skill definitions.
    """

    skills: Dict[str, SkillDefinition]


class TraitData(msgspec.Struct):  # type: ignore[misc]
    """
    Root container for Trait definitions.
    """

    traits: Dict[str, TraitDefinition]


class InteractionData(msgspec.Struct):  # type: ignore[misc]
    """
    Root container for Interaction definitions.
    """

    interaction: Dict[str, InteractionDefinition]


class AudioSettings(msgspec.Struct):
    """
    Audio settings data model.
    """

    master_volume: float = 0.5
    bgm_volume: float = 0.5
    sfx_volume: float = 0.5


class WindowSettings(msgspec.Struct):
    """
    Window settings data model.
    """

    width: int = 1280
    height: int = 720
    fullscreen: bool = False


class UserSettings(msgspec.Struct):
    """
    Root container for user settings.
    """

    audio: AudioSettings = msgspec.field(default_factory=AudioSettings)
    window: WindowSettings = msgspec.field(default_factory=WindowSettings)
