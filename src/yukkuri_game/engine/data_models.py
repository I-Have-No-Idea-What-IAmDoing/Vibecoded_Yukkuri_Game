from typing import Dict, List, Optional, TYPE_CHECKING
import msgspec

if TYPE_CHECKING:
    # Mypy doesn't play nice with msgspec extension types sometimes
    class YukkuriTypeBase:
        pass
    class ItemTypeBase:
        pass
    class ActionEffectBase:
        pass
    class ActionConsiderationBase:
        pass
    class AIActionBase:
        pass
    class YukkuriDataBase:
        pass
    class ItemDataBase:
        pass
    class AIDataBase:
        pass
    class AnimationDefinitionBase:
        pass
    class AnimationDataBase:
        pass
else:
    YukkuriTypeBase = msgspec.Struct
    ItemTypeBase = msgspec.Struct
    ActionEffectBase = msgspec.Struct
    ActionConsiderationBase = msgspec.Struct
    AIActionBase = msgspec.Struct
    YukkuriDataBase = msgspec.Struct
    ItemDataBase = msgspec.Struct
    AIDataBase = msgspec.Struct
    AnimationDefinitionBase = msgspec.Struct
    AnimationDataBase = msgspec.Struct


class YukkuriType(YukkuriTypeBase):
    """
    Data model representing a type of Yukkuri.

    Attributes:
        name (str): The display name of the Yukkuri type.
        image (str): The filename of the sprite image.
        width (int): The width of the sprite in pixels.
        height (int): The height of the sprite in pixels.
        max_health (int): The maximum health of this Yukkuri type.
        base_happiness (int): The starting happiness level.
    """
    name: str
    image: str
    width: int
    height: int
    max_health: int
    base_happiness: int
    cost: int = 100

class ItemType(ItemTypeBase):
    """
    Data model representing a type of Item.

    Attributes:
        name (str): The display name of the item.
        image (str): The filename of the sprite image.
        width (int): The width of the sprite in pixels.
        height (int): The height of the sprite in pixels.
        cost (int): The cost to purchase the item.
        is_portable (bool): Whether the item can be picked up by Yukkuris.
        nutrition (Optional[int]): Nutritional value if edible. Defaults to None.
        comfort (Optional[int]): Comfort value if it's a toy/bed. Defaults to None.
        fun (Optional[int]): Fun value if it's a toy. Defaults to None.
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

class ActionEffect(ActionEffectBase):
    """
    Data model representing the effects of an AI action.

    Attributes:
        type (str): The type of effect (e.g., "interact_item").
        target_stat (Optional[str]): The specific stat to modify. Defaults to None.
        consume (bool): Whether the action consumes the target (e.g., eating food). Defaults to False.
        stat_changes (Dict[str, float]): Dictionary of stat changes (key is stat name, value is change amount). Defaults to empty dict.
    """
    type: str
    target_stat: Optional[str] = None
    consume: bool = False
    stat_changes: Dict[str, float] = {}

class ActionConsideration(ActionConsiderationBase):
    """
    Data model representing a consideration (input factor) for an AI action.

    Attributes:
        name (str): The name of the consideration.
        input (str): The input variable to evaluate (e.g., "hunger").
        curve (str): The utility curve type to apply (e.g., "linear").
        params (Dict[str, float]): Parameters for the curve function. Defaults to empty dict.
    """
    name: str
    input: str
    curve: str
    params: Dict[str, float] = {}

class AIAction(AIActionBase):
    """
    Data model representing an AI action definition.

    Attributes:
        weight (float): The base weight/priority of the action.
        effects (ActionEffect): The effects resulting from the action.
        considerations (List[ActionConsideration]): A list of considerations that determine the action's utility score. Defaults to empty list.
    """
    weight: float
    effects: ActionEffect
    considerations: List[ActionConsideration] = []

class AnimationDefinition(AnimationDefinitionBase):
    """
    Data model representing an animation definition.

    Attributes:
        name (str): The name of the animation (e.g., "idle", "walk").
        image (str): The filename of the sprite sheet.
        frame_count (int): The number of frames in the animation.
        frame_duration (float): The duration of each frame in seconds.
        width (int): The width of a single frame in pixels.
        height (int): The height of a single frame in pixels.
        loop (bool): Whether the animation should loop. Defaults to True.
    """
    name: str
    image: str
    frame_count: int
    frame_duration: float
    width: int
    height: int
    loop: bool = True

# Root containers for the TOML structure
class YukkuriData(YukkuriDataBase):
    """
    Root container for Yukkuri type definitions loaded from TOML.

    Attributes:
        yukkuris (Dict[str, YukkuriType]): A dictionary mapping type IDs to YukkuriType objects.
    """
    yukkuris: Dict[str, YukkuriType]

class ItemData(ItemDataBase):
    """
    Root container for Item type definitions loaded from TOML.

    Attributes:
        items (Dict[str, ItemType]): A dictionary mapping item IDs to ItemType objects.
    """
    items: Dict[str, ItemType]

class AIData(AIDataBase):
    """
    Root container for AI action definitions loaded from TOML.

    Attributes:
        actions (Dict[str, AIAction]): A dictionary mapping action IDs to AIAction objects.
    """
    actions: Dict[str, AIAction]

class AnimationData(AnimationDataBase):
    """
    Root container for Animation definitions loaded from TOML.

    Attributes:
        animations (Dict[str, AnimationDefinition]): A dictionary mapping animation IDs to AnimationDefinition objects.
    """
    animations: Dict[str, AnimationDefinition]
